from io import BytesIO
from PIL import Image
import requests

ASCII_CHARS = " .:-=+*#%@"
CACHE: dict[str, str] = {}

_COLOR_STOPS = [
    (0, (0x00, 0x00, 0x33)),
    (63, (0x00, 0x33, 0xaa)),
    (127, (0x33, 0x99, 0xff)),
    (192, (0xcc, 0xdd, 0xff)),
    (255, (0xff, 0xff, 0xff)),
]


def _pixel_tag(brightness: int) -> str:
    for i in range(len(_COLOR_STOPS) - 1):
        low_pos, low_color = _COLOR_STOPS[i]
        high_pos, high_color = _COLOR_STOPS[i + 1]
        if brightness <= high_pos:
            ratio = (brightness - low_pos) / (high_pos - low_pos)
            r = int(low_color[0] + (high_color[0] - low_color[0]) * ratio)
            g = int(low_color[1] + (high_color[1] - low_color[1]) * ratio)
            b = int(low_color[2] + (high_color[2] - low_color[2]) * ratio)
            return f"[#{r:02x}{g:02x}{b:02x}]"
    return "[#ffffff]"


def render_album_art(thumbnail_url: str, width: int = 60, height: int = 20) -> str:
    if not thumbnail_url:
        return ""
    if thumbnail_url in CACHE:
        return CACHE[thumbnail_url]
    try:
        resp = requests.get(thumbnail_url, timeout=5)
        img = Image.open(BytesIO(resp.content)).convert("L")
        img = img.resize((width, height))
        pixels = list(img.getdata())
        lines = []
        for y in range(height):
            line = ""
            for x in range(width):
                raw = pixels[y * width + x]
                idx = raw * (len(ASCII_CHARS) - 1) // 255
                line += f"{_pixel_tag(raw)}{ASCII_CHARS[idx]}[/]"
            lines.append(line)
        result = "\n".join(lines)
        CACHE[thumbnail_url] = result
        return result
    except Exception:
        return ""
