"""
SurplusBite — core image processing logic.

Milestone 1 (this file): pure Python + Pillow. No AWS calls, no boto3.
Milestone 2 will add `lambda_handler(event, context)` at the bottom.

The `process_image()` function is the contract every later milestone reuses.
"""

import logging
from io import BytesIO
from typing import Optional

from PIL import Image, UnidentifiedImageError

logger = logging.getLogger(__name__)

# ---------- Constants ----------
CARD_MAX = (300, 300)          # listing card thumbnail
PIN_MAX = (96, 96)             # map-marker thumbnail
VALID_EXTENSIONS = {".jpg", ".jpeg", ".png"}
VALID_FORMATS = {"JPEG", "PNG"}


# ---------- Helpers ----------
def _validate_extension(key: str) -> bool:
    """Return True if the object key ends with a supported image extension."""
    return any(key.lower().endswith(ext) for ext in VALID_EXTENSIONS)


def _resize_to(image: Image.Image, max_dim: tuple[int, int]) -> Image.Image:
    """
    Return a resized copy that fits inside max_dim, preserving aspect ratio.
    Never upscales: small images are returned unchanged in size.
    """
    copy = image.copy()
    copy.thumbnail(max_dim, Image.LANCZOS)
    return copy


def _encode(image: Image.Image, fmt: str) -> bytes:
    """
    Encode an image to bytes. Converts RGBA / P to RGB for JPEG safety.
    Optimises output to reduce file size.
    """
    if image.mode in ("RGBA", "P") and fmt == "JPEG":
        image = image.convert("RGB")
    out = BytesIO()
    image.save(out, format=fmt, optimize=True)
    return out.getvalue()


# ---------- Public entry point used by tests and (later) Lambda ----------
def process_image(key: str, image_bytes: bytes) -> dict:
    """
    Validate, resize and encode a single image.

    Returns a structured result dict. Never raises for expected failures.

    Success:
        {
          "key": str,
          "status": "success",
          "original_bytes": int,
          "original_dims": (w, h),
          "card_bytes": bytes, "card_dims": (w, h), "card_size": int,
          "pin_bytes":  bytes, "pin_dims":  (w, h), "pin_size":  int,
          "reduction_pct_card": float,
        }

    Rejected (bad extension / unsupported format):
        {"key": ..., "status": "rejected", "reason": "..."}

    Error (corrupt or unreadable image):
        {"key": ..., "status": "error", "reason": "..."}
    """
    # ---- Extension check ----
    if not _validate_extension(key):
        return {"key": key, "status": "rejected", "reason": "extension"}

    # ---- Decode and process ----
    try:
        with Image.open(BytesIO(image_bytes)) as img:
            fmt: Optional[str] = img.format
            if fmt not in VALID_FORMATS:
                return {"key": key, "status": "rejected", "reason": f"format:{fmt}"}

            original_size = img.size  # (w, h)

            # Normalise mode once, then derive both variants from it
            base = img.convert("RGB") if img.mode in ("RGBA", "P") else img

            card = _resize_to(base, CARD_MAX)
            pin = _resize_to(base, PIN_MAX)

            save_fmt = "JPEG" if fmt == "JPEG" else "PNG"
            card_bytes = _encode(card, save_fmt)
            pin_bytes = _encode(pin, save_fmt)

            reduction = (
                round((1 - len(card_bytes) / len(image_bytes)) * 100, 2)
                if image_bytes
                else 0.0
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

    except Exception as exc:  # noqa: BLE001 — we want to catch everything and log
        logger.exception("Unexpected failure processing %s", key)
        return {
            "key": key,
            "status": "error",
            "reason": f"{type(exc).__name__}: {exc}",
        }


# Milestone 2 will append:
#
# def lambda_handler(event, context):
#     ...