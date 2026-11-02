"""Converts illustrations to authentic 16-bit SNES pixel art (Secret of Evermore / Terranigma style)."""

from pathlib import Path
from PIL import Image

BACKGROUNDS_DIR = Path("assets/backgrounds")
TARGET_FILES = ["ossuary.png", "foundry.png", "observatory.png", "sanctum.png", "shop.png", "rest.png"]

# Native SNES internal 16:9 pixel resolution
SNES_W, SNES_H = 320, 180
TARGET_W, TARGET_H = 960, 540


def convert_image(file_name: str) -> None:
    path = BACKGROUNDS_DIR / file_name
    if not path.exists():
        print(f"File not found: {path}")
        return

    img = Image.open(path).convert("RGB")

    # 1. Downscale to SNES native resolution
    small = img.resize((SNES_W, SNES_H), resample=Image.Resampling.LANCZOS)

    # 2. Quantize to 128-color SNES palette with Floyd-Steinberg dithering
    quantized = small.quantize(colors=128, method=Image.Quantize.FASTOCTREE, dither=Image.Dither.FLOYDSTEINBERG)

    # 3. Nearest-neighbor upscale back to 960x540
    pixel_art = quantized.convert("RGB").resize((TARGET_W, TARGET_H), resample=Image.Resampling.NEAREST)

    # Save over file
    pixel_art.save(path, format="PNG")
    print(f"Successfully converted {file_name} to 16-bit SNES pixel art ({TARGET_W}x{TARGET_H})")


def main() -> None:
    for f in TARGET_FILES:
        convert_image(f)


if __name__ == "__main__":
    main()
