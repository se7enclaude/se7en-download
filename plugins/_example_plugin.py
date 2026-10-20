"""Example Media Lab plugin (files starting with "_" are not loaded).

Copy to %LOCALAPPDATA%\\MediaLab\\plugins\\my_plugin.py (or <app>\\plugins\\)
and restart Media Lab. A plugin can:

* add a download provider  (api.add_provider)
* add an upscale backend   (api.add_upscale_backend)
* add API routes           (api.add_router)  -> /api/plugins/<prefix>/...
* react to events          (api.on_event)
"""
from fastapi import APIRouter

PLUGIN_NAME = "Example plugin"


def register(api):
    router = APIRouter()

    @router.get("/hello")
    def hello():
        return {"hello": "from a plugin"}

    api.add_router(router, "example")

    def on_event(ev):
        if ev["type"] == "notify" and ev["data"].get("kind") == "success":
            api.log.info("Plugin saw a finished task: %s", ev["data"].get("title"))

    api.on_event(on_event)

    # Example: a provider for an internal media server (sketch)
    # from medialab.downloader.base import SourceProvider, DownloadResult, media_info
    # class MyServerProvider(SourceProvider):
    #     id, name, priority = "myserver", "My media server", 30
    #     def can_handle(self, url): return url.startswith("https://media.example.com/")
    #     def analyze(self, url, settings): return media_info(url=url, provider=self.id, ...)
    #     def download(self, url, options, ctx): ...; return DownloadResult(file_path=...)
    # api.add_provider(MyServerProvider())
