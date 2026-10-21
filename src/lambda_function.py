"""
SurplusBite — core image processing and AWS Lambda handler.
"""

import logging
import os
from io import BytesIO
from typing import Optional

import boto3
from PIL import Image, UnidentifiedImageError

# ---------------------------------------------------------------------------
# CLOUD ENGINEER NOTES:
# 1. ENVIRONMENT VARIABLES:
#    - OUTPUT_BUCKET: The exact name of the S3 bucket where thumbnails go.
#    - (Must be set in the Lambda configuration)
# 2. IAM EXECUTION ROLE:
#    - s3:GetObject on the source bucket
#    - s3:PutObject on the output bucket
#    - logs:CreateLogGroup, logs:CreateLogStream, logs:PutLogEvents
# 3. TRIGGER:
#    - S3 ObjectCreated on the source bucket.
# ---------------------------------------------------------------------------

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize S3 client outside the handler for connection reuse
s3_client = boto3.client("s3")

# ---------- Constants ----------
CARD_MAX = (300, 300)
PIN_MAX = (96, 96)
VALID_EXTENSIONS = {".jpg", ".jpeg", ".png"}
VALID_FORMATS = {"JPEG", "PNG"}


# ---------- Helpers ----------
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


# ---------- Core Logic ----------
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


# ---------- AWS Lambda Handler ----------
def lambda_handler(event, context):
    """
    Triggered by S3 ObjectCreated.
    Downloads image, calls process_image(), uploads card and pin.
    """
    output_bucket = os.environ.get("OUTPUT_BUCKET")
    if not output_bucket:
        logger.error("Missing OUTPUT_BUCKET environment variable.")
        raise ValueError("OUTPUT_BUCKET environment variable is required.")

    results = []

    for record in event.get("Records", []):
        src_bucket = record["s3"]["bucket"]["name"]
        key = record["s3"]["object"]["key"]
        
        logger.info(f"Received event for s3://{src_bucket}/{key}")

        try:
            # 1. Download original from S3
            response = s3_client.get_object(Bucket=src_bucket, Key=key)
            image_bytes = response["Body"].read()

            # 2. Process
            result = process_image(key, image_bytes)

            # 3. Upload outputs if successful
            if result["status"] == "success":
                base_name = os.path.splitext(os.path.basename(key))[0]
                ext = "jpg" if key.lower().endswith((".jpg", ".jpeg")) else "png"
                
                card_key = f"thumbnails/{base_name}_card.{ext}"
                pin_key = f"thumbnails/{base_name}_pin.{ext}"

                # Upload Card
                s3_client.put_object(
                    Bucket=output_bucket,
                    Key=card_key,
                    Body=result["card_bytes"],
                    ContentType=f"image/{ext}"
                )
                
                # Upload Pin
                s3_client.put_object(
                    Bucket=output_bucket,
                    Key=pin_key,
                    Body=result["pin_bytes"],
                    ContentType=f"image/{ext}"
                )
                
                result["card_key"] = card_key
                result["pin_key"] = pin_key
                logger.info(f"Successfully processed {key} -> {card_key}, {pin_key}")
            else:
                logger.warning(f"Failed to process {key}: {result.get('reason')}")

            # Remove raw bytes from the result before logging (keeps logs clean)
            result.pop("card_bytes", None)
            result.pop("pin_bytes", None)
            results.append(result)

        except Exception as e:
            logger.error(f"Failed to handle S3 object {key}: {str(e)}")
            results.append({"key": key, "status": "error", "reason": str(e)})

    return {
        "statusCode": 200,
        "body": results
    }