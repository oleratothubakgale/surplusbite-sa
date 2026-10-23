"""
SurplusBite — core image processing and AWS Lambda handler.
"""

import logging
import os
import json
from io import BytesIO
from datetime import datetime, timezone
from typing import Optional
from urllib.parse import unquote_plus

import boto3
from PIL import Image, UnidentifiedImageError
from botocore.exceptions import ClientError

# ---------------------------------------------------------------------------
# CLOUD ENGINEER NOTES:
# 1. ENVIRONMENT VARIABLES:
#    - OUTPUT_BUCKET: The exact name of the S3 bucket where thumbnails AND catalogue.json go.
#    - ENABLE_REKOGNITION: Set to "true" to enable AI labels. Set to "false" to disable.
# 2. IAM EXECUTION ROLE (Additions for M5):
#    - rekognition:DetectLabels (Required if ENABLE_REKOGNITION is true)
# ---------------------------------------------------------------------------

logger = logging.getLogger()
logger.setLevel(logging.INFO)

s3_client = boto3.client("s3")
rekognition = boto3.client("rekognition")

CARD_MAX = (300, 300)
PIN_MAX = (96, 96)
VALID_EXTENSIONS = {".jpg", ".jpeg", ".png"}
VALID_FORMATS = {"JPEG", "PNG"}
CATALOGUE_KEY = "catalogue/index.json"

# ---------- AI Taxonomy ----------
FOOD_TAXONOMY = {
    "produce": ["Vegetable", "Fruit", "Produce", "Leaf vegetable", "Root vegetable", "Tomato", "Carrot", "Apple", "Banana"],
    "bakery": ["Bread", "Bakery", "Pastry", "Cake", "Dessert", "Sourdough", "Croissant"],
    "prepared": ["Meal", "Dish", "Cuisine", "Food", "Lunch", "Dinner", "Takeout", "Pizza", "Burger"],
    "dairy": ["Cheese", "Milk", "Dairy", "Egg", "Butter"]
}
ALL_VALID_LABELS = [label for labels in FOOD_TAXONOMY.values() for label in labels]

def _validate_extension(key: str) -> bool:
    return any(key.lower().endswith(ext) for ext in VALID_EXTENSIONS)

def _resize_to(image: Image.Image, max_dim: tuple[int, int]) -> Image.Image:
    copy = image.copy()
    copy.thumbnail(max_dim, Image.LANCZOS)
    return copy

def _encode(image: Image.Image, fmt: str) -> bytes:
    if image.mode in ("RGBA", "P") and fmt == "JPEG":
        image = image.convert("RGB")
    out = BytesIO()
    image.save(out, format=fmt, optimize=True)
    return out.getvalue()

def process_image(key: str, image_bytes: bytes) -> dict:
    if not _validate_extension(key):
        return {"key": key, "status": "rejected", "reason": "extension"}

    try:
        with Image.open(BytesIO(image_bytes)) as img:
            fmt: Optional[str] = img.format
            if fmt not in VALID_FORMATS:
                return {"key": key, "status": "rejected", "reason": f"format:{fmt}"}

            original_size = img.size
            base = img.convert("RGB") if img.mode in ("RGBA", "P") else img

            card = _resize_to(base, CARD_MAX)
            pin = _resize_to(base, PIN_MAX)

            save_fmt = "JPEG" if fmt == "JPEG" else "PNG"
            card_bytes = _encode(card, save_fmt)
            pin_bytes = _encode(pin, save_fmt)

            reduction = (
                round((1 - len(card_bytes) / len(image_bytes)) * 100, 2)
                if image_bytes else 0.0
            )

            return {
                "key": key,
                "status": "success",
                "original_bytes": len(image_bytes),
                "original_dims": original_size,
                "card_bytes": card_bytes,
                "card_dims": card.size,
                "card_size": len(card_bytes),
                "pin_bytes": pin_bytes,
                "pin_dims": pin.size,
                "pin_size": len(pin_bytes),
                "reduction_pct_card": reduction,
            }

    except UnidentifiedImageError:
        return {"key": key, "status": "error", "reason": "unidentified_image"}
    except Exception as exc:
        logger.exception("Unexpected failure processing %s", key)
        return {"key": key, "status": "error", "reason": f"{type(exc).__name__}: {exc}"}

# ---------- AI LOGIC ----------
def _detect_food_category(image_bytes: bytes) -> dict:
    """Calls Rekognition and maps results to our taxonomy."""
    if os.environ.get("ENABLE_REKOGNITION", "false").lower() != "true":
        return {"category": "unknown", "labels": [], "status": "disabled"}

    try:
        response = rekognition.detect_labels(
            Image={"Bytes": image_bytes},
            MaxLabels=10,
            MinConfidence=70.0
        )
        
        raw_labels = [label["Name"] for label in response.get("Labels", [])]
        logger.info(f"Rekognition labels: {raw_labels}")

        matched_category = None
        for category, keywords in FOOD_TAXONOMY.items():
            if any(keyword.lower() in [l.lower() for l in raw_labels] for keyword in keywords):
                matched_category = category
                break

        if matched_category:
            return {"category": matched_category, "labels": raw_labels, "status": "success"}
        else:
            return {"category": "unknown", "labels": raw_labels, "status": "no_food_detected"}

    except Exception as e:
        logger.error(f"Rekognition failed: {e}")
        return {"category": "unknown", "labels": [], "status": "error"}

def _update_catalogue(output_bucket: str, new_entry: dict):
    try:
        response = s3_client.get_object(Bucket=output_bucket, Key=CATALOGUE_KEY)
        catalogue_data = json.loads(response["Body"].read().decode("utf-8"))
        if not isinstance(catalogue_data, list):
            catalogue_data = []
    except ClientError as e:
        if e.response['Error']['Code'] == 'NoSuchKey':
            catalogue_data = []
        else:
            logger.error(f"Error reading catalogue: {e}")
            return

    catalogue_data.insert(0, new_entry)
    catalogue_data = catalogue_data[:50]

    s3_client.put_object(
        Bucket=output_bucket,
        Key=CATALOGUE_KEY,
        Body=json.dumps(catalogue_data, indent=2),
        ContentType="application/json"
    )
    logger.info(f"Updated catalogue. Total entries: {len(catalogue_data)}")

# ---------- AWS Lambda Handler ----------
def lambda_handler(event, context):
    output_bucket = os.environ.get("OUTPUT_BUCKET")
    if not output_bucket:
        logger.error("Missing OUTPUT_BUCKET environment variable.")
        raise ValueError("OUTPUT_BUCKET environment variable is required.")

    results = []

    for record in event.get("Records", []):
        src_bucket = record["s3"]["bucket"]["name"]
        key = unquote_plus(record["s3"]["object"]["key"])
        
        logger.info(f"Received event for s3://{src_bucket}/{key}")

        try:
            response = s3_client.get_object(Bucket=src_bucket, Key=key)
            image_bytes = response["Body"].read()

            result = process_image(key, image_bytes)

            if result["status"] == "success":
                ai_result = _detect_food_category(image_bytes)
                
                base_name = os.path.splitext(os.path.basename(key))[0]
                ext = "jpg" if key.lower().endswith((".jpg", ".jpeg")) else "png"
                
                card_key = f"thumbnails/{base_name}_card.{ext}"
                pin_key = f"thumbnails/{base_name}_pin.{ext}"

                content_type = "image/jpeg" if ext == "jpg" else "image/png"
                s3_client.put_object(Bucket=output_bucket, Key=card_key, Body=result["card_bytes"], ContentType=content_type)
                s3_client.put_object(Bucket=output_bucket, Key=pin_key, Body=result["pin_bytes"], ContentType=content_type)
                
                catalogue_entry = {
                    "id": base_name,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "card_url": f"/{card_key}",
                    "pin_url": f"/{pin_key}",
                    "reduction_pct": result["reduction_pct_card"],
                    "original_size": result["original_bytes"],
                    "ai_category": ai_result["category"],
                    "ai_status": ai_result["status"],
                    "ai_labels": ai_result["labels"]
                }
                
                _update_catalogue(output_bucket, catalogue_entry)

                result["card_key"] = card_key
                result["pin_key"] = pin_key
                result["ai_result"] = ai_result
                logger.info(f"Successfully processed {key} -> {card_key}, {pin_key}")
            else:
                logger.warning(f"Failed to process {key}: {result.get('reason')}")

            result.pop("card_bytes", None)
            result.pop("pin_bytes", None)
            results.append(result)

        except Exception as e:
            logger.error(f"Failed to handle S3 object {key}: {str(e)}")
            results.append({"key": key, "status": "error", "reason": str(e)})

    return {"statusCode": 200, "body": results}