"""
SurplusBite — local test harness for Milestone 1.

Usage (VS Code): open this file and click the ▶ Run button.
Or in the integrated terminal: python tests/test_local.py
"""

import sys
from pathlib import Path

# Allow `from lambda_function import ...` without installing as a package
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from backend.lambda_function import process_image  # noqa: E402

TEST_DIR = Path(__file__).resolve().parent / "test_images"
VALID_EXTENSIONS = {".jpg", ".jpeg", ".png"}
EXPECTED_REJECT_TOKENS = ("corrupt", "invalid", "unsupported")
ASPECT_TOLERANCE = 0.02

def _expect(name: str) -> str:
    lower = name.lower()
    if any(tok in lower for tok in EXPECTED_REJECT_TOKENS):
        return "reject"
    return "success"

def _check_success(result: dict, failures: list[str]) -> None:
    cw, ch = result["card_dims"]
    pw, ph = result["pin_dims"]
    ow, oh = result["original_dims"]

    print(f"  original: {result['original_bytes']:>8} bytes, {ow}x{oh}")
    print(
        f"  card:     {result['card_size']:>8} bytes, {cw}x{ch}  "
        f"(reduction {result['reduction_pct_card']}%)"
    )
    print(f"  pin:      {result['pin_size']:>8} bytes, {pw}x{ph}")

    if cw > 300 or ch > 300:
        failures.append(f"{result['key']}: card exceeds 300x300 ({cw}x{ch})")
    if pw > 96 or ph > 96:
        failures.append(f"{result['key']}: pin exceeds 96x96 ({pw}x{ph})")

    if oh and ch:
        orig_ratio = ow / oh
        card_ratio = cw / ch
        if abs(card_ratio - orig_ratio) > ASPECT_TOLERANCE:
            failures.append(
                f"{result['key']}: aspect ratio drift "
                f"(orig {orig_ratio:.3f} vs card {card_ratio:.3f})"
            )

def main() -> int:
    if not TEST_DIR.exists():
        print(f"ERROR: {TEST_DIR} does not exist.")
        return 1

    # FIX: Only look at image files, ignoring README.md and anything else
    files = sorted(
        p for p in TEST_DIR.iterdir() if p.is_file() and p.suffix.lower() in VALID_EXTENSIONS
    )
    
    if not files:
        print(
            f"No test images in {TEST_DIR}.\n"
            f"Run tests/generate_test_images.py first."
        )
        return 1

    failures: list[str] = []
    for path in files:
        print(f"\n=== {path.name} ===")
        expect = _expect(path.name)

        try:
            data = path.read_bytes()
        except OSError as exc:
            failures.append(f"{path.name}: cannot read ({exc})")
            print(f"  FAIL: cannot read file ({exc})")
            continue

        result = process_image(path.name, data)
        print(f"  status: {result['status']}")

        if expect == "success":
            if result["status"] != "success":
                reason = result.get("reason", "unknown")
                print(f"  FAIL: expected success, got {result['status']} ({reason})")
                failures.append(
                    f"{path.name}: expected success, got {result['status']} ({reason})"
                )
                continue
            _check_success(result, failures)

        else:
            if result["status"] == "success":
                print("  FAIL: expected rejection, got success")
                failures.append(f"{path.name}: expected rejection, got success")
            else:
                reason = result.get("reason", "unknown")
                print(f"  rejected ({result['status']}): {reason}")

    print("\n" + "=" * 50)
    if failures:
        print(f"FAILED — {len(failures)} issue(s):")
        for f in failures:
            print(f"  - {f}")
        return 1

    print(f"PASSED — {len(files)} file(s) checked")
    return 0

if __name__ == "__main__":
    sys.exit(main())