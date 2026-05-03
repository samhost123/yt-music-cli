from io import BytesIO
from PIL import Image
import requests

ASCII_CHARS = " .:-=+*#%@"
CACHE: dict[str, str] = {}

def render_album_art(thumbnail_url: str, width: int = 40, height: int = 20) -> str:
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
                idx = pixels[y * width + x] * (len(ASCII_CHARS) - 1) // 255
                line += ASCII_CHARS[idx]
            lines.append(line)
        result = "\n".join(lines)
        CACHE[thumbnail_url] = result
        return result
    except Exception:
        return ""
