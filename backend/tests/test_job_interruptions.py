"""Pause / annulation / suppression d'une tâche en cours avec le vrai JobManager.

yt-dlp ne lève pas toujours « Canceled » quand on l'interrompt : sur un flux HLS/DASH, le fragment
en cours d'écriture disparaît et il lève UnavailableVideoError. Ce n'est pas un échec : la tâche
ne doit jamais repartir toute seule (« Retrying in 2s »).
"""
import threading
import time
from pathlib import Path

import pytest
from yt_dlp.utils import UnavailableVideoError

from medialab.config import paths
from medialab.db import Database
from medialab.jobs.manager import JobManager
from medialab.settings import SettingsStore


def ytdlp_like_worker(job, ctx):
    """Comme yt-dlp sur un flux fragmenté : l'interruption fait disparaître le .part-FragN."""
    opts = job["options"]
    if opts.get("parts_dir"):
        Path(opts["parts_dir"]).mkdir(parents=True, exist_ok=True)
        (Path(opts["parts_dir"]) / "video.part-Frag3").write_bytes(b"x")
        ctx.remember({"_parts_dir": opts["parts_dir"]})
    ctx.progress({"stage": "downloading", "percent": 1.0, "speed": 1000.0})
    while not ctx.cancel.is_set():
        time.sleep(0.01)
    raise UnavailableVideoError(FileNotFoundError(2, "No such file or directory", "video.mp4.part-Frag3.part"))


@pytest.fixture
def manager(tmp_path):
    jm = JobManager(Database(tmp_path / "jobs.db"), SettingsStore(tmp_path / "settings.json"))
    jm.register_worker("fake", ytdlp_like_worker, lambda: 2)
    # Le fournisseur proposerait une nouvelle tentative pour cette erreur : c'est ce qui relançait la tâche.
    jm._fallback_for = lambda job, code, attempt: {"label": "Retrying"}
    jm.start()
    yield jm
    jm.shutdown()
    jm.db.close()


def wait_for(cond, timeout=10.0):
    t0 = time.time()
    while time.time() - t0 < timeout:
        v = cond()
        if v:
            return v
        time.sleep(0.02)
    raise AssertionError("timeout")


def running(jm, job_id):
    return wait_for(lambda: job_id in jm._running and jm.get(job_id)["status"] == "downloading")


def stays(jm, job_id, status, seconds=0.6):
    t0 = time.time()
    while time.time() - t0 < seconds:
        assert jm.get(job_id)["status"] == status
        time.sleep(0.05)


def test_pause_is_not_a_failure(manager):
    job = manager.add("fake", "https://example.com/hls", {})
    running(manager, job["id"])
    manager.pause(job["id"])
    wait_for(lambda: job["id"] not in manager._running)
    j = manager.get(job["id"])
    assert j["status"] == "paused", j
    assert j["attempts"] == 0 and not j.get("error")
    assert "_not_before" not in (j.get("options") or {})
    stays(manager, job["id"], "paused")


def test_cancel_is_not_a_failure(manager, tmp_path):
    parts = tmp_path / "out" / ".medialab-parts"
    job = manager.add("fake", "https://example.com/hls", {})
    # same layout as ytdlp_provider: <sortie>\.medialab-parts\<id>
    manager.db.update_job(job["id"], options={"parts_dir": str(parts / job["id"])})
    running(manager, job["id"])
    assert (parts / job["id"]).is_dir()
    manager.cancel(job["id"])
    wait_for(lambda: job["id"] not in manager._running)
    j = manager.get(job["id"])
    assert j["status"] == "canceled", j
    assert not j.get("error")
    stays(manager, job["id"], "canceled")
    assert not (parts / job["id"]).exists()  # partial files removed with the task
    assert not parts.exists()  # the empty staging folder too


def test_remove_while_running_deletes_the_task(manager):
    job = manager.add("fake", "https://example.com/hls", {})
    running(manager, job["id"])
    manager.remove(job["id"])
    wait_for(lambda: job["id"] not in manager._running)
    time.sleep(0.3)
    assert manager.db.get_job(job["id"]) is None  # not re-inserted as « waiting » by a retry


def test_real_failures_still_retry(manager):
    def broken(job, ctx):
        raise UnavailableVideoError(OSError("disk error"))
    manager.register_worker("broken", broken, lambda: 1)
    job = manager.add("broken", "https://example.com/hls", {})
    j = wait_for(lambda: (x := manager.get(job["id"]))["attempts"] >= 1 and x)
    assert j["status"] in ("waiting", "analyzing", "processing", "downloading", "failed")
    assert j["error"]


def test_cleanup_never_touches_other_folders(manager, tmp_path):
    keep = tmp_path / "Videos" / "important"
    keep.mkdir(parents=True)
    job = manager.add("fake", "u", {}, start_paused=True)
    manager.db.update_job(job["id"], options={"_parts_dir": str(keep)})
    manager.cancel(job["id"])
    assert keep.is_dir()


def test_prune_old_installers():
    from medialab import __version__
    from medialab.updater import updater
    folder = paths().data / "updates"
    folder.mkdir(parents=True, exist_ok=True)
    old = folder / "se7en-Update-1.0.0.exe"
    current = folder / f"se7en-Update-{__version__}.exe"
    newer = folder / "se7en-Update-99.0.0.exe"
    portable = folder / "se7en-Portable-Update-1.0.0.zip"
    part = folder / "se7en-Update-99.0.0.exe.part"
    other = folder / "notes.txt"
    for f in (old, current, newer, portable, part, other):
        f.write_bytes(b"x")
    try:
        updater.prune_downloads()
        assert not old.exists() and not current.exists() and not portable.exists() and not part.exists()
        assert newer.exists() and other.exists()
    finally:
        for f in (newer, other):
            f.unlink(missing_ok=True)


def test_extension_from_content_type():
    from medialab.downloader.direct_provider import ext_from_ctype
    assert ext_from_ctype("image/jpeg") == ".jpg"
    assert ext_from_ctype("video/mp4; charset=binary") == ".mp4"
    assert ext_from_ctype("audio/mpeg") == ".mp3"
    assert ext_from_ctype("text/html") is None
    assert ext_from_ctype(None) is None


def test_convert_resume_does_not_download_again(tmp_path, monkeypatch):
    """« Convertir en » interrompu : la reprise convertit le fichier déjà téléchargé, sans doublon."""
    from medialab.downloader.base import DownloadResult
    from medialab.downloader import output_format
    from medialab.errors import Canceled
    from medialab.jobs import workers
    from medialab.jobs.manager import JobContext

    calls = {"download": 0, "convert": 0}
    stored: dict = {}
    src = tmp_path / "clip.webm"

    class Provider:
        def download(self, url, options, ctx):
            calls["download"] += 1
            src.write_bytes(b"media")
            return DownloadResult(file_path=str(src), title="clip", size=5, format="WEBM")

    def ensure(path, opts, s, cancel, progress):
        calls["convert"] += 1
        if calls["convert"] == 1:
            raise Canceled("paused")
        return {"file_path": str(tmp_path / "clip.mp4"), "size": 4, "format": "MP4", "meta": {"target": "mp4"}}

    monkeypatch.setattr(workers.registry, "get", lambda pid: Provider())
    monkeypatch.setattr(output_format, "ensure", ensure)
    worker = workers.make_download_worker(SettingsStore(tmp_path / "s.json"))
    job = {"id": "j1", "source": "https://example.com/v", "title": "clip",
           "options": {"mode": "av", "container": "mp4"}}

    def ctx():
        return JobContext(job=job, cancel=threading.Event(), progress=lambda p: None,
                          set_status=lambda s: None, temp_dir=tmp_path, attempt=0, strategy={},
                          remember=lambda v: stored.update(v))

    with pytest.raises(Canceled):
        worker(job, ctx())
    job["options"] = {**job["options"], **stored}  # what the manager keeps in the task options
    out = worker(job, ctx())
    assert calls == {"download": 1, "convert": 2}
    assert out["file_path"].endswith("clip.mp4") and out["format"] == "MP4"
