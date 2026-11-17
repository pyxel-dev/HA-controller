"""Generate the integration brand icons (icon.png and icon@2x.png)."""

from pathlib import Path

from PIL import Image, ImageDraw

DESIGN = 512
OUT = Path(__file__).parents[2] / "custom_components" / "ha_controller" / "brand"


def draw(size: int) -> Image.Image:
    """Draw the icon at `size` px, scaled from the 512 design."""
    scale = 4  # supersample for smooth edges
    px = size * scale
    k = px / DESIGN
    c = px / 2
    img = Image.new("RGBA", (px, px), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    def box(r: float) -> tuple[float, float, float, float]:
        return (c - r * k, c - r * k, c + r * k, c + r * k)

    d.ellipse(box(240), fill="#111827")
    # Ring and arc are centred on radius 170, so the outer edge is 170 + width / 2.
    outer = 170 + 36 / 2
    d.ellipse(box(outer), outline="#374151", width=round(36 * k))
    d.arc(box(outer), 135, 315, fill="#F59E0B", width=round(36 * k))
    d.ellipse(box(40), fill="#F9FAFB")
    return img.resize((size, size), Image.LANCZOS)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    draw(256).save(OUT / "icon.png")
    draw(512).save(OUT / "icon@2x.png")


if __name__ == "__main__":
    main()
