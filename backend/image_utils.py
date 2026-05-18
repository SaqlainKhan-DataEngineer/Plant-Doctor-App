"""Compress scan images before DB storage."""
import io
from PIL import Image

MAX_DIM = 1024
JPEG_QUALITY = 72
MAX_BYTES = 450_000


def compress_image_bytes(data: bytes) -> bytes:
    """Resize + JPEG compress so base64 fits comfortably in MySQL."""
    img = Image.open(io.BytesIO(data)).convert("RGB")
    w, h = img.size
    if max(w, h) > MAX_DIM:
        ratio = MAX_DIM / max(w, h)
        img = img.resize((int(w * ratio), int(h * ratio)), Image.Resampling.LANCZOS)

    quality = JPEG_QUALITY
    out = b""
    while quality >= 40:
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=quality, optimize=True)
        out = buf.getvalue()
        if len(out) <= MAX_BYTES:
            return out
        quality -= 8
    return out
