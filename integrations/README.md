# Integrations

se7en exposes its engine through a **local, token-protected API** and a
**command-line client** (`se7en-cli.exe`). Any host application that can run
a command can use it.

## After Effects (included)

`after-effects/se7en_SendToUpscaler.jsx` is a dockable ScriptUI panel:

1. Copy it to `…\Adobe After Effects <version>\Support Files\Scripts\ScriptUI Panels\`
2. Enable *Preferences › Scripting & Expressions › Allow Scripts to Write Files and Access Network*
3. *Window › se7en_SendToUpscaler.jsx*, select footage, **Send to Upscaler**

The result is rendered by se7en (it appears in its queue and history) and
imported back into the project next to the original.

## Premiere Pro / DaVinci Resolve (same mechanism)

* **DaVinci Resolve** (Python scripting, *Workspace › Scripts*):
  ```python
  import subprocess
  out = subprocess.run([r"C:\Program Files\se7en\se7en-cli.exe", "upscale", clip_path,
                        "--scale", "2", "--wait"], capture_output=True, text=True).stdout.strip()
  resolve.GetMediaStorage().AddItemListToMediaPool([out])
  ```
* **Premiere Pro** (UXP/CEP panel): call the CLI with `child_process`, then
  `app.project.importFiles([result])`.

## CLI reference

```
se7en-cli upscale <files…> [--model ID] [--scale N | --width W --height H] [--denoise 0-3] [--sharpen 0-3] [--output-dir DIR] [--wait]
se7en-cli download <url> [--quality best|2160|…|144] [--mode av|video|audio] [--container mp4|mkv|webm] [--output-dir DIR] [--wait]
se7en-cli status
```

With `--wait`, progress goes to stderr and the output path is printed on stdout
(exit code 0), or the explained error with exit code 1.

## HTTP API

The running app writes `%LOCALAPPDATA%\MediaLab\session.json` (`port`, `token`).
Send the token in the `X-MediaLab-Token` header. Main endpoints:
`POST /api/analyze`, `POST /api/downloads`, `POST /api/upscale/jobs`,
`GET /api/jobs`, `GET /api/jobs/{id}`, WebSocket `/api/ws?token=…` for live events.
