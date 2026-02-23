"""Generate placeholder application icons using Pillow."""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


def create_icon(size: int = 512) -> Image.Image:
    """Create a simple placeholder icon: blue circle with 'MA' text."""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    margin = int(size * 0.05)
    draw.ellipse(
        [margin, margin, size - margin, size - margin],
        fill=(47, 128, 237),
    )

    font_size = int(size * 0.35)
    try:
        font = ImageFont.truetype("arial.ttf", font_size)
    except OSError:
        font = ImageFont.load_default(font_size)
    draw.text(
        (size / 2, size / 2),
        "MA",
        fill=(255, 255, 255),
        font=font,
        anchor="mm",
    )
    return img


def main():
    root = Path(__file__).resolve().parent.parent
    icons_dir = root / "resources" / "icons"
    icons_dir.mkdir(parents=True, exist_ok=True)

    img = create_icon(512)

    png_path = icons_dir / "app_icon.png"
    img.save(str(png_path))
    print(f"Created: {png_path}")

    ico_path = icons_dir / "app.ico"
    ico_sizes = [256, 128, 64, 48, 32, 16]
    ico_images = [img.resize((s, s), Image.LANCZOS) for s in ico_sizes]
    ico_images[0].save(
        str(ico_path), format="ICO", append_images=ico_images[1:]
    )
    print(f"Created: {ico_path}")

    icns_path = icons_dir / "app.icns"
    img.save(str(icns_path), format="ICNS")
    print(f"Created: {icns_path}")


if __name__ == "__main__":
    main()
