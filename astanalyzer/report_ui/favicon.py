from pathlib import Path

from PIL import Image, ImageDraw


FAVICON_FILENAME = "astanalyzer.ico"


def ensure_report_favicon(output_dir: Path) -> Path:
    """
    Ensure that the AstAnalyzer report favicon exists.

    The icon is generated only when it is missing. Existing icons are left
    untouched to avoid overwriting user-visible report assets.
    """
    output_dir = Path(output_dir)
    favicon_path = output_dir / FAVICON_FILENAME

    if favicon_path.exists():
        return favicon_path

    output_dir.mkdir(parents=True, exist_ok=True)
    
    size = 64
    image = Image.new("RGBA", (size, size), (58, 58, 58, 255))
    draw = ImageDraw.Draw(image)

    def draw_line(x: int, y: int, width: int, height: int, color):
        draw.rectangle([x, y, x + width, y + height], fill=color)

    draw_line(14, 14, 34, 4, (74, 163, 255))   # neutral
    draw_line(20, 22, 30, 4, (46, 204, 113))   # green (indented)
    draw_line(20, 30, 34, 4, (74, 163, 255))   # neutral same indent
    draw_line(14, 38, 40, 5, (231, 76, 60))    # red (longer + thicker)
    draw_line(14, 48, 28, 4, (74, 163, 255))   # neutral
    
    image.save(favicon_path, format="ICO")
    return favicon_path