"""The format chosen when pasting a link is the format of the file you get."""
import subprocess
import threading
from types import SimpleNamespace

import pytest

from medialab.downloader import output_format as of
from medialab.settings import Settings


def _settings():
    return Settings()


def test_wanted_target_for_every_choice():
    d = _settings().download
    assert of.wanted_target({"mode": "audio", "audio_format": "mp3"}, d) == "mp3"
    assert of.wanted_target({"mode": "audio", "audio_format": "aac"}, d) == "m4a"
    assert of.wanted_target({"mode": "audio", "audio_format": "ogg"}, d) == "ogg"
    assert of.wanted_target({"mode": "audio", "audio_format": "alac"}, d) == "alac"
    assert of.wanted_target({"mode": "audio", "audio_format": "best"}, d) is None  # original kept
    assert of.wanted_target({"mode": "av", "container": "mov"}, d) == "mov"
    assert of.wanted_target({"mode": "av", "container": "mkv"}, d) == "mkv"
    assert of.wanted_target({"mode": "image"}, d) is None


def test_settings_accept_new_formats():
    s = Settings.model_validate({"download": {"default_audio_format": "ogg", "default_container": "mov"}})
    assert s.download.default_audio_format == "ogg" and s.download.default_container == "mov"
    Settings.model_validate({"download": {"default_audio_format": "alac"}})


def _tone(ffmpeg, path, extra=()):
    subprocess.run([ffmpeg, "-y", "-v", "error", "-f", "lavfi", "-i", "sine=frequency=440:duration=2", *extra, str(path)],
                   check=True)


@pytest.mark.parametrize("fmt,ext,codec", [("mp3", ".mp3", "mp3"), ("ogg", ".ogg", "vorbis"), ("flac", ".flac", "flac"),
                                           ("opus", ".opus", "opus"), ("aac", ".m4a", "aac"), ("alac", ".m4a", "alac")])
def test_direct_file_is_converted_to_the_chosen_audio_format(ffmpeg_bin, tmp_path, fmt, ext, codec):
    from medialab.media import ffmpeg
    src = tmp_path / "direct.wav"
    _tone(ffmpeg_bin, src)
    seen = []
    res = of.ensure(str(src), {"mode": "audio", "audio_format": fmt, "audio_bitrate": 192}, _settings(),
                    threading.Event(), seen.append)
    assert res is not None
    out = tmp_path / f"direct{ext}"
    assert res["file_path"] == str(out) and out.is_file() and not src.exists()
    assert ffmpeg.probe(out)["audio"][0]["codec"] == codec
    assert seen and seen[-1]["stage"] == "processing"


def test_already_in_the_right_format_is_left_alone(ffmpeg_bin, tmp_path):
    src = tmp_path / "song.mp3"
    _tone(ffmpeg_bin, src)
    assert of.ensure(str(src), {"mode": "audio", "audio_format": "mp3"}, _settings(), threading.Event(), print) is None
    assert of.ensure(str(src), {"mode": "audio", "audio_format": "best"}, _settings(), threading.Event(), print) is None
    img = tmp_path / "cover.jpg"
    img.write_bytes(b"\xff\xd8\xff")
    assert of.ensure(str(img), {"mode": "av", "container": "mp4"}, _settings(), threading.Event(), print) is None


def test_direct_video_link_gets_the_chosen_container(ffmpeg_bin, tmp_path):
    from medialab.media import ffmpeg
    src = tmp_path / "clip.webm"
    subprocess.run([ffmpeg_bin, "-y", "-v", "error", "-f", "lavfi", "-i", "testsrc=size=160x120:rate=10:duration=1",
                    "-f", "lavfi", "-i", "sine=duration=1", "-c:v", "libvpx-vp9", "-c:a", "libopus", "-shortest", str(src)],
                   check=True)
    res = of.ensure(str(src), {"mode": "av", "container": "mov"}, _settings(), threading.Event(), lambda p: None)
    out = tmp_path / "clip.mov"
    assert res and res["file_path"] == str(out) and out.is_file()
    info = ffmpeg.probe(out)
    assert info["audio"][0]["codec"] == "aac"
