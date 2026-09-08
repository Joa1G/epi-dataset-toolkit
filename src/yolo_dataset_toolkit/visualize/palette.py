"""Color palettes, generated for any number of classes."""

import colorsys

# OpenCV stores pixels as Blue, Green, Red - not the usual RGB order.
Color = tuple[int, int, int]

# Walking the hue circle by the golden angle keeps consecutive classes far
# apart in color for any class count, without hand-picking values.
_GOLDEN_ANGLE = 0.618033988749895


def build_palette(count: int, saturation: float = 0.9, value: float = 1.0) -> list[Color]:
    """Build `count` visually distinct BGR colors. Class 0 gets red."""
    palette: list[Color] = []
    hue = 0.0

    for _ in range(count):
        red, green, blue = colorsys.hsv_to_rgb(hue, saturation, value)
        palette.append((round(blue * 255), round(green * 255), round(red * 255)))
        hue = (hue + _GOLDEN_ANGLE) % 1.0

    return palette


def parse_hex_color(text: str) -> Color:
    """'#00ff00' or '00ff00' -> BGR tuple, for overriding a class color."""
    cleaned = text.lstrip("#")
    if len(cleaned) != 6:
        raise ValueError(f"expected a 6-digit hex color, got {text!r}")

    try:
        red, green, blue = (int(cleaned[i : i + 2], 16) for i in (0, 2, 4))
    except ValueError as exc:
        raise ValueError(f"invalid hex color {text!r}") from exc

    return (blue, green, red)
