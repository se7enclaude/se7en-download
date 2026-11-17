"""Regressions fixed in 1.7.0 (review of the whole application)."""
from medialab.downloader import formats as fmt
from medialab.downloader.registry import extract_urls
from medialab.errors import classify
from medialab.subtitles.llm import clean_hesitations


def test_urls_keep_a_closing_bracket_that_belongs_to_them():
    assert extract_urls("voir (https://en.wikipedia.org/wiki/Heat_(1995_film)).") == \
        ["https://en.wikipedia.org/wiki/Heat_(1995_film)"]
    assert extract_urls("[https://example.com/a]") == ["https://example.com/a"]
    assert extract_urls("https://example.com/a, https://example.com/b.") == \
        ["https://example.com/a", "https://example.com/b"]


def test_errors_are_not_classified_on_letters_inside_other_words():
    assert classify("[patreon] 123: Unable to download JSON: HTTP Error 500").code == "server_error"
    assert classify("[generic] hdrmovie: getaddrinfo failed").code == "network"
    assert classify("[Errno 28] No space left on device; file deleted").code == "disk_full"
    assert classify("peer closed connection without sending complete message body").code == "network"
    assert classify("This video is DRM protected").code == "drm"


def test_a_muxed_format_does_not_expect_a_separate_audio_track():
    formats = [
        {"format_id": "18", "ext": "mp4", "vcodec": "avc1.42001E", "acodec": "mp4a.40.2", "height": 360, "width": 640,
         "filesize": 1000},
        {"format_id": "140", "ext": "m4a", "vcodec": "none", "acodec": "mp4a.40.2", "abr": 128, "filesize": 300},
    ]
    sel = fmt.select(formats, mode="av", quality="360", container="mp4", vcodec="compat",
                     audio_format="best", audio_bitrate=None)
    assert sel["spec"] == "18"
    assert sel["audio"] is None  # counted in the expected size otherwise: the bar never reached 100 %


def test_a_bare_video_file_is_a_video():
    assert fmt.has_video({"url": "x", "ext": "mp4"})
    assert not fmt.has_video({"url": "x", "ext": "m4a"})
    assert fmt.acodec_family("mp4a.40.34") == "mp3"
    assert fmt.acodec_family("mp4a.40.2") == "aac"


def test_hesitations_never_remove_real_words():
    assert clean_hesitations("Nous nous sommes vus et vous vous trompez", "fr") == \
        "Nous nous sommes vus et vous vous trompez"
    assert clean_hesitations("He had had enough", "en") == "He had had enough"
    assert clean_hesitations("me gusta este libro", "es") == "me gusta este libro"
    assert clean_hesitations("je je pense euh que oui", "fr") == "je pense que oui"
