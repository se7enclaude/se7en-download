"""The format the user asked for when pasting the link: make sure the downloaded file has it.

yt-dlp converts most sources itself while downloading. Direct links, galleries and the
rare stream yt-dlp cannot remux arrive in their original format: they are converted here,
with the same converter as the « Convertir » tab, so every link gives the chosen format.
"""
from __future__ import annotations

import threading
from pathlib import Path
from typing import Any, Callable

from ..logging_setup import get_logger

log = get_logger("process")

# audio format (download options) -> converter target
AUDIO_TARGETS = {"mp3": "mp3", "m4a": "m4a", "aac": "m4a", "opus": "opus", "ogg": "ogg",
                 "flac": "flac", "wav": "wav", "alac": "alac"}
# video container -> converter target (H.264 / AAC where a conversion is needed)
VIDEO_TARGETS = {"mp4": "mp4", "mkv": "mkv", "webm": "webm", "mov": "mov"}
AUDIO_EXTS = {"mp3", "m4a", "aac", "opus", "ogg", "oga", "flac", "wav", "wma", "aiff", "aif", "alac", "webm", "mka"}
VIDEO_EXTS = {"mp4", "mkv", "webm", "mov", "avi", "flv", "ts", "m4v", "3gp", "wmv", "mpg", "mpeg", "ogv"}
LOSSLESS = {"flac", "wav", "alac"}


def wanted_target(options: dict[str, Any], defaults) -> str | None:
    """Converter target id the job must end with, or None (original format / images)."""
    mode = options.get("mode", defaults.default_mode)
    if mode == "audio":
        fmt = str(options.get("audio_format", defaults.default_audio_format) or "best").lower()
        return AUDIO_TARGETS.get(fmt)
    if mode in ("av", "video"):
        return VIDEO_TARGETS.get(str(options.get("container", defaults.default_container) or "").lower())
    return None


def needs_conversion(path: Path, target_id: str, probe: Callable[[Path], dict] | None = None) -> bool:
    from ..tools.convert import TARGETS
    target = TARGETS[target_id]
    ext = path.suffix.lower().lstrip(".")
    if ext != target.ext:
        return True
    if target.ext == "m4a" and probe:  # AAC and ALAC share the .m4a extension
        try:
            codecs = [str(a.get("codec") or "").lower() for a in probe(path).get("audio", [])]
        except Exception:
            return False
        want_alac = target_id == "alac"
        return bool(codecs) and any((c == "alac") != want_alac for c in codecs)
    return False


def ensure(path_str: str | None, options: dict[str, Any], settings, cancel: threading.Event,
           progress: Callable[[dict], None]) -> dict[str, Any] | None:
    """Convert the downloaded file when it is not in the requested format.

    Returns the converter result (new file_path, size, format…) or None when nothing was needed.
    """
    if not path_str:
        return None
    src = Path(path_str)
    target_id = wanted_target(options, settings.download)
    if not target_id or not src.is_file():
        return None
    ext = src.suffix.lower().lstrip(".")
    mode = options.get("mode", settings.download.default_mode)
    if mode == "audio" and ext not in AUDIO_EXTS | VIDEO_EXTS:
        return None
    if mode != "audio" and ext not in VIDEO_EXTS:
        return None  # an image or a document from a gallery: nothing to convert
    from ..media import ffmpeg
    from ..tools import convert as converter
    if not needs_conversion(src, target_id, ffmpeg.probe):
        return None
    label = converter.TARGETS[target_id].label

    def on_progress(frac: float, text: str, eta: float | None = None) -> None:
        progress({"stage": "processing", "label": f"Conversion → {label}", "percent": frac * 100, "eta": eta,
                  "speed": 0})

    opts: dict[str, Any] = {"output_dir": str(src.parent), "hw": settings.tools.use_gpu_encoder}
    if mode == "audio" and target_id not in LOSSLESS:
        opts["audio_bitrate"] = int(options.get("audio_bitrate") or settings.download.default_audio_bitrate)
    log.info("Converting the download to %s: %s", label, src.name)
    res = converter.convert(src, target_id, opts, cancel, on_progress)
    try:
        src.unlink()
        dst = Path(res["file_path"])
        if dst.suffix.lower() == src.suffix.lower():  # AAC -> ALAC: keep the original name
            dst.replace(src)
            res.update(file_path=str(src), title=src.name)
    except OSError:
        log.warning("Could not remove the original after conversion: %s", src)
    return res
