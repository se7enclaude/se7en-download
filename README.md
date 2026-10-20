# se7en — Télécharger · IA · Convertir · Découper · Lire

**Télécharger :** [se7en-Setup (Windows 10/11)](https://github.com/se7enclaude/se7en-download/releases/latest/download/se7en-Setup.exe)
— une fois installé, se7en se met à jour tout seul. Au premier lancement, Windows SmartScreen peut afficher
un avertissement (programme non signé) : « Informations complémentaires » → « Exécuter quand même ».

Logiciel desktop Windows tout-en-un, en 9 onglets :

| # | Onglet | Ce qu'il fait |
|---|---|---|
| 01 | **Télécharger** | ≈1 800 sites (yt-dlp), images (gallery-dl), liens directs · modes Vidéo+Audio / Muet / Audio / **Image** · « Lisible partout » (H.264/AAC) |
| 02 | **File** | file d'attente commune : pause, reprise, priorité, relance automatique |
| 03 | **IA** | Agrandir (Real-ESRGAN, Real-CUGAN, UltraSharp, HAT, Nomos, SPAN…), **Visages** (GFPGAN/CodeFormer), **Détourage**, **Colorisation**, **Fluidifier** (RIFE 60/120 fps) — images et vidéos |
| 04 | **Convertir** | vidéo, audio, image, sous-titres ; remux sans perte, taille cible, volume uniformisé |
| 05 | **Découper** | garder / supprimer des passages, sans perte ou à l'image près, fondus |
| 06 | **Lecteur** | lit tout (MKV, AVI, HEVC, FLAC, WMA… convertis à la volée), file et bibliothèque |
| 07 | **Historique** | tout ce qui a été produit, rejouable |
| 08 | **Doublons** | fichiers identiques (hash) et photos/vidéos similaires (dHash) |
| 09 | **Stats** | activité, plateformes, temps GPU, espace disque |

Mises à jour automatiques depuis GitHub Releases, sons d'interface, animation de lancement « se7en ».

> Utilisez se7en uniquement pour des contenus que vous possédez, sous licence libre, ou que vous êtes autorisé
> à télécharger. Le logiciel ne contourne **ni DRM, ni paywall, ni contrôle d'accès**, et ne demande/stocke jamais
> de mot de passe.

---

## 1. Démarrage rapide (utilisateur)

| Édition | Fichier | Données |
|---|---|---|
| Installeur (à envoyer) | `dist\se7en-Setup-1.1.0.exe` | `%LOCALAPPDATA%\MediaLab` |
| Mise à jour | `dist\se7en-Update-1.1.0.exe` (téléchargé automatiquement) | — |
| Portable | `dist\se7en-Portable-1.1.0.zip` → extraire → `se7en.exe` | `<dossier>\data` (fichier `portable.flag`) |

Tout est inclus : FFmpeg (NVENC / Quick Sync / AMF), Deno, Real-ESRGAN, Real-CUGAN, RIFE et les modèles ONNX
(DirectML : toute carte graphique DirectX 12, CPU sinon). Installation par utilisateur, sans droits administrateur.
Prérequis : Windows 10 1809+ / 11 x64, runtime WebView2 (présent sur Windows 11 ; l'installeur l'ajoute sinon).

## 2. Lancer depuis les sources (développement)

Prérequis : Python 3.11–3.13, Node.js 20+.

```powershell
# Backend
python -m venv backend\.venv
backend\.venv\Scripts\pip install -r backend\requirements-dev.txt

# Frontend
cd frontend; npm ci; npm run build; cd ..

# Application desktop (fenêtre WebView2)
cd backend; .\.venv\Scripts\python -m medialab
```

Mode développement avec rechargement à chaud de l'UI :

```powershell
cd backend;  .\.venv\Scripts\python -m medialab --dev     # API sur :8765, jeton "dev"
cd frontend; npm run dev                                   # http://localhost:5173
```

Autres modes : `python -m medialab --server --open-browser` (API + UI dans le navigateur), `--debug` (logs détaillés).

## 3. Build (installeur + portable)

```powershell
powershell -ExecutionPolicy Bypass -File packaging\build.ps1 -Repo moncompte/se7en   # tests, UI, PyInstaller, composants, portable, 2 installeurs, latest.json
powershell -ExecutionPolicy Bypass -File packaging\publish.ps1                        # publie la version sur GitHub Releases
```

Nécessite [Inno Setup 6](https://jrsoftware.org/isinfo.php) (`winget install JRSoftware.InnoSetup`). Les composants
sont téléchargés une fois (releases officielles, SHA-256 vérifié) et gardés dans `build\component-cache`.

### Mises à jour automatiques

1. se7en lit `https://github.com/<repo>/releases/latest/download/latest.json` au démarrage puis toutes les 6 h.
2. Une version plus récente est téléchargée en arrière-plan (`se7en-Update-x.y.z.exe`, programme seul, sans les
   modèles déjà installés), vérifiée par SHA-256, puis installée à la fermeture de se7en — ou tout de suite via
   « Redémarrer et mettre à jour ». Les tâches en cours sont mises en pause et reprennent ensuite.
3. Édition portable : le zip est déballé à côté, le dossier `data` n'est jamais touché.

Pour publier : augmenter `__version__` dans `backend/medialab/__init__.py`, écrire `packaging/notes.md`,
lancer `build.ps1` puis `publish.ps1` (GitHub CLI connecté : `build\tools\gh\bin\gh.exe auth login`).

## 4. Identité visuelle (se7en Design System)

L'interface applique le design system fourni (`design-system/`, copie de référence) :
noir cinéma (`#050505`), un seul accent rouge signal (`#F22B2B`, le « 7 »), Syne 800 pour les titres,
Geist / Geist Mono pour l'interface (polices embarquées, fonctionne hors ligne), angles quasi carrés,
libellés MONO MAJUSCULES, lignes de balayage, repères HUD, champ de pixels réactif au curseur et motif
**pixel-resolve** (un média part de gros pixels et se résout net).

**Animation de lancement « se7en »** (`frontend/src/components/Splash.tsx`, portée du kit) : curseur rouge →
le mot se résout en 9 étapes de pixels (144p → 4K) sous une ligne de scan rouge → balayage de lumière →
tagline tapée → fondu vers l'application. Clic ou touche pour passer ; clic sur le logo pour la rejouer ;
désactivable dans Réglages › Général. Si le moteur n'est pas encore prêt, elle reste sur le logo net.

## 5. Architecture

```
┌────────────────────────── se7en.exe (un seul processus) ─────────────────────────┐
│  Fenêtre WebView2 (pywebview)  ──HTTP/WebSocket 127.0.0.1 + jeton──►  FastAPI     │
│  React + TypeScript (Vite)                                            │           │
│                                                    ┌──────────────────┼────────┐  │
│                                                    │ JobManager (SQLite, file,  │  │
│                                                    │ priorités, reprise, retry) │  │
│                                                    └──┬──────────────────┬─────┘  │
│                         Download providers ◄──────────┘                  └──► Upscale engine
│                         yt-dlp · gallery-dl · direct                          ncnn-Vulkan · PyTorch · Classic
│                                   │                                                  │
└───────────────────────────────────┼──────────────────────────────────────────────────┼┘
                                FFmpeg (fusion, remux, métadonnées, NVENC)  ◄───────────┘
```

**Pourquoi ce choix** (comparaison demandée) :

| Option | Verdict |
|---|---|
| Electron | Écarté : embarque Chromium (~150 Mo, ~150 Mo RAM au repos), exactement l'« app Electron générique » à éviter. |
| Tauri + Rust | Excellent shell, mais le cœur (yt-dlp, IA) est en Python : il faudrait un sidecar Python + IPC Rust↔Python + deux chaînes d'outils. |
| Node.js backend | yt-dlp et l'écosystème IA sont Python ; Node imposerait de piloter des sous-processus pour tout. |
| **Python + WebView2 (retenu)** | Même moteur de rendu que Tauri sur Windows (WebView2, déjà dans Windows 11), un seul langage backend, yt-dlp utilisé comme bibliothèque (hooks de progression fins, sélection de formats sur mesure). |

Le frontend ne parle qu'HTTP/WebSocket : le shell pourra être remplacé par Tauri sans toucher l'UI.

Sécurité locale : l'API n'écoute que sur `127.0.0.1`, exige un jeton aléatoire par session (en-tête ou `?token=`) et
refuse les en-têtes `Host` étrangers (anti-CSRF / DNS-rebinding). Cookies importés chiffrés par DPAPI Windows.

## 6. Structure du projet

```
backend/medialab/
  main.py              point d'entrée (fenêtre, serveur, instance unique, crash log)
  app.py               API REST + WebSocket, service de l'UI
  settings.py db.py    réglages typés (JSON) · SQLite (jobs, historique, presets)
  components.py        détection / installation FFmpeg, Real-ESRGAN, Deno, aria2, mise à jour yt-dlp
  hardware.py          GPU (NVML : VRAM, usage, température), CPU/RAM
  errors.py            classification des erreurs → code + message + conseil + retry possible
  downloader/          base (SourceProvider) · registry · ytdlp_provider · gallery_provider · direct_provider
                       formats (qualités réelles, tailles, codecs, Smart Quality) · naming · cookies · platforms
  jobs/                manager (file, concurrence, pause/reprise/annulation/retry/priorité) · workers
  media/ffmpeg.py      probe, exécution avec progression, encodeurs réellement fonctionnels (NVENC testé)
  upscale/             models (registre) · planning (échelles, tuiles/VRAM) · engine (image, aperçu)
                       video (segments + checkpoints) · filters · face (GFPGAN optionnel)
                       backends/ ncnn.py · torch_backend.py · classic.py
  cli.py               se7en-cli (intégrations : After Effects, Resolve, scripts)
backend/tests/         60 tests (pytest)
frontend/src/          pages (Télécharger, File, Upscale, Historique, Réglages, Journal), composants se7en, store, i18n FR/EN
design-system/         design system se7en fourni (tokens, composants, kit desktop, animation de référence)
packaging/             medialab.spec (PyInstaller) · installer.iss (Inno Setup) · build.ps1 · fetch_components.py
integrations/          script After Effects « Send to Upscaler » (se7en_SendToUpscaler.jsx) + doc Premiere/Resolve/API
plugins/               exemple de plugin
```

## 7. Tests

```powershell
cd backend;  .\.venv\Scripts\python -m pytest -q      # 60 tests : formats, Smart Quality, nommage, erreurs,
                                                     # planification, VRAM/OOM, API, sécurité, file d'attente
cd frontend; npm test                                # complétude des traductions FR/EN
```

Validé en conditions réelles pendant le développement (RTX 5070 Ti, FFmpeg 9.0) :
analyse YouTube (8 qualités 144p→4K60, tailles exactes, codecs) · téléchargement 360p et 1080p60 (fusion vidéo+audio,
miniature et métadonnées intégrées) · **pause/reprise** d'un téléchargement sans redémarrage · MP3 320 ·
anti-écrasement `(1)` · upscale image ×4 et ×8 · upscale vidéo ×2 segmenté (audio synchronisé, 360/360 images,
BT.709) · **reprise d'un rendu interrompu à 50 %** depuis le dernier segment · aperçu + comparaison · CLI ·
exe PyInstaller (démarrage API 0,6 s, fermeture propre 2,4 s, instance unique, mode portable).

## 8. Étendre

* **Plateforme** : rien à faire pour les ~1 800 sites de yt-dlp (mise à jour du moteur : Réglages › Composants).
  Pour une source spécifique : sous-classe de `SourceProvider` enregistrée par un plugin.
* **Modèle IA** : déposer `nom.param` + `nom.bin` (ncnn) dans `models\ncnn`, ou `.pth`/`.safetensors`
  (ESRGAN, SwinIR, HAT, DAT…) dans `models\torch` ; un `nom.json` optionnel définit nom/échelle/catégories.
* **Backend d'upscaling** (TensorRT, DirectML, VSR temporel) : implémenter `UpscaleBackend` (3 méthodes) + `register_backend`.
* **Plugins** : fichier Python dans `plugins\` exposant `register(api)` (providers, backends, routes, événements).
* **Traductions** : `frontend/src/i18n/*.ts` (un test vérifie que toutes les clés existent).

### Backend PyTorch optionnel (SwinIR, HAT, visages…)

```powershell
backend\.venv\Scripts\pip install torch torchvision --index-url https://download.pytorch.org/whl/cu128   # RTX 50xx : CUDA 12.8+
backend\.venv\Scripts\pip install -r backend\requirements-torch.txt
```

## 9. Limites connues (honnêtes)

* **Signature du code** : l'exécutable n'est pas signé (certificat payant) ; SmartScreen peut afficher un avertissement
  au premier lancement (« Informations complémentaires › Exécuter quand même »).
* **Licences des modèles** : UltraSharp, ClearReality et CodeFormer sont sous licence non commerciale (usage personnel) ;
  c'est indiqué dans l'interface et dans Réglages › Composants.
* **Cohérence temporelle** : Real-ESRGAN traite chaque image indépendamment. se7en réduit le scintillement
  (lissage temporel + deflicker FFmpeg, modèle AnimeVideo v3 conçu pour la vidéo), mais ce n'est pas un vrai modèle
  de super-résolution vidéo récurrent. L'architecture (`upscale_dir` par segment) permet d'en brancher un (ex. RealBasicVSR) via PyTorch.
* **Défloutage** : aucun modèle de deblur n'est fourni ; l'option est affichée comme indisponible plutôt que simulée.
* **HDR** : les modèles travaillent en SDR 8 bits ; une source HDR est tone-mappée en SDR avant l'IA.
* **Backend PyTorch** : optionnel, non inclus (≈3 Go) ; tout ce qui est livré tourne via ncnn-Vulkan et ONNX/DirectML.
* **Colorisation vidéo** : DeOldify colorise image par image ; un lissage temporel des couleurs limite le scintillement.
* **8×** : deux passes IA si l'image intermédiaire reste raisonnable, sinon IA ×4 + agrandissement Lanczos (affiché dans le plan).
* **YouTube** : yt-dlp requiert un runtime JavaScript (Deno, installable en un clic, ou Node.js s'il est présent).
