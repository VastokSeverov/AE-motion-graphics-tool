"""Local still-image background removal for VASTOCHNIY AE Copilot.

Inference is performed on-device with rembg/ONNX Runtime. The original image is
never overwritten; output PNGs are stored in the user's Application Support folder.
"""
from pathlib import Path
import os
import uuid

SUPPORTED = {".png", ".jpg", ".jpeg", ".webp", ".tif", ".tiff", ".bmp"}
MAX_BYTES = 150 * 1024 * 1024

class BackgroundRemovalError(ValueError):
    """A safe, user-facing background-removal error."""

def remove_background(source_path):
    source = Path(source_path).expanduser()
    try:
        source = source.resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        raise BackgroundRemovalError("The selected image file could not be found. Make sure it is saved locally.") from exc
    if not source.is_file():
        raise BackgroundRemovalError("The selected layer is not a local image file.")
    if source.suffix.lower() not in SUPPORTED:
        raise BackgroundRemovalError("Choose a still image (PNG, JPG, WEBP, TIFF, or BMP). Video and image sequences are not supported yet.")
    try:
        size = source.stat().st_size
    except OSError as exc:
        raise BackgroundRemovalError("Could not read the selected image file.") from exc
    if size <= 0 or size > MAX_BYTES:
        raise BackgroundRemovalError("Image file must be smaller than 150 MB.")
    try:
        from rembg import remove, new_session
        from PIL import Image
        import io
        # Keep one model session per process so subsequent images don't reload it.
        global _SESSION
        try:
            _SESSION
        except NameError:
            _SESSION = new_session("isnet-general-use")
        raw = source.read_bytes()
        result = remove(raw, session=_SESSION)
        with Image.open(io.BytesIO(result)) as image:
            rgba = image.convert("RGBA")
            out_dir = Path.home() / "Library" / "Application Support" / "VASTOCHNIY" / "BackgroundRemover"
            out_dir.mkdir(parents=True, exist_ok=True)
            output = out_dir / (source.stem + "_no_bg_" + uuid.uuid4().hex[:8] + ".png")
            rgba.save(str(output), format="PNG", optimize=True)
        return output
    except ImportError as exc:
        raise BackgroundRemovalError("Background remover is not installed. Follow the Background Remover setup in INSTALL_MAC.txt.") from exc
    except Exception as exc:
        # Keep technical detail in Terminal, but show a useful message in the panel.
        print("Background removal error:", repr(exc), flush=True)
        raise BackgroundRemovalError("Could not remove the background. Check the bridge Terminal for the model or image error.") from exc
