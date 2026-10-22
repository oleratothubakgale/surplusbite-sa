"""
SurplusBite — generate synthetic test images for Milestone 1.

Run with the ▶ button in VS Code (or: python tests/generate_test_images.py).
Creates four files in tests/test_images/ — no external files, no downloads.
"""

from pathlib import Path

from PIL import Image, ImageDraw

OUT = Path(__file__).resolve().parent / "test_images"


def make_large_jpg() -> None:
    """4032x3024 — same size as a modern phone photo. 'Busy' content."""
    img = Image.new("RGB", (4032, 3024), color=(220, 200, 180))
    draw = ImageDraw.Draw(img)
    for i in range(18):
        x, y = (i * 220) % 3800, (i * 160) % 2800
        draw.ellipse(
            [x, y, x + 500, y + 400],
            fill=((60 + i * 11) % 255, (140 + i * 9) % 255, (100 + i * 7) % 255),
        )
    path = OUT / "sample-large.jpg"
    img.save(path, "JPEG", quality=85)
    print(f"Created {path.name}  ({path.stat().st_size:>8} bytes)")


def make_square_png() -> None:
    """1024x1024 RGBA — tests the RGBA→RGB path on JPEG output."""
    img = Image.new("RGBA", (1024, 1024), color=(50, 130, 70, 255))
    draw = ImageDraw.Draw(img)
    draw.rectangle([120, 120, 900, 900], fill=(255, 200, 60, 255))
    draw.ellipse([300, 300, 700, 700], fill=(220, 80, 60, 255))
    path = OUT / "sample-square.png"
    img.save(path, "PNG")
    print(f"Created {path.name}  ({path.stat().st_size:>8} bytes)")


def make_tiny_jpg() -> None:
    """150x120 — smaller than card max. Must NOT be upscaled."""
    img = Image.new("RGB", (150, 120), color=(80, 140, 200))
    draw = ImageDraw.Draw(img)
    draw.line([0, 0, 150, 120], fill=(255, 255, 255), width=4)
    path = OUT / "sample-tiny.jpg"
    img.save(path, "JPEG", quality=85)
    print(f"Created {path.name}  ({path.stat().st_size:>8} bytes)")


def make_corrupt() -> None:
    """Plain text with a .jpg extension — must fail as unidentified_image."""
    path = OUT / "corrupt-file.jpg"
    path.write_text("this is not an image — it is plain text\n")
    print(f"Created {path.name}  ({path.stat().st_size:>8} bytes)")


if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    make_large_jpg()
    make_square_png()
    make_tiny_jpg()
    make_corrupt()
    print("\nDone. Next: run tests/test_local.py")
      