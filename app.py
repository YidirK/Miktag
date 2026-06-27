#!/usr/bin/env python3

import asyncio
import uuid
import shutil
import re
import base64
import threading
import sys
import os
from pathlib import Path

# ── Frozen / dev path resolution ──────────────────────────────────────────────
if getattr(sys, 'frozen', False):
    BASE_DIR    = Path(sys._MEIPASS)
    RUNTIME_DIR = Path(sys.executable).parent
else:
    BASE_DIR    = Path(__file__).parent
    RUNTIME_DIR = BASE_DIR

TEMPLATE_DIR = BASE_DIR / "templates"
STATIC_DIR   = BASE_DIR / "static"

# ── Dependency check ──────────────────────────────────────────────────────────
MISSING = []
try:
    from shazamio import Shazam
except ImportError:
    MISSING.append("shazamio")
try:
    from mutagen.id3 import (ID3, TIT2, TPE1, TALB, TCON, APIC,
                              ID3NoHeaderError, TDRC)
    from mutagen.flac import FLAC, Picture
    from mutagen.mp4 import MP4, MP4Cover
    from mutagen.oggvorbis import OggVorbis
except ImportError:
    MISSING.append("mutagen")
try:
    import requests
except ImportError:
    MISSING.append("requests")
try:
    from flask import Flask, send_from_directory, request, jsonify
except ImportError:
    MISSING.append("flask")
try:
    import webview
except ImportError:
    MISSING.append("pywebview")

if MISSING:
    print(f"\n Missing packages: {', '.join(MISSING)}")
    print(f"   Run: pip install {' '.join(MISSING)}\n")
    sys.exit(1)

# ── Flask App ─────────────────────────────────────────────────────────────────
app = Flask(__name__, template_folder=str(TEMPLATE_DIR),
            static_folder=str(STATIC_DIR))

SUPPORTED_EXT = {".mp3", ".flac", ".m4a", ".ogg", ".aac", ".wav"}
jobs: dict = {}

# ── Core Logic ────────────────────────────────────────────────────────────────

def parse_shazam_result(result: dict) -> dict:
    data = {}
    try:
        track = result.get("track", {})
        data["title"]  = track.get("title", "")
        data["artist"] = track.get("subtitle", "")
        data["genre"]  = track.get("genres", {}).get("primary", "")
        for section in track.get("sections", []):
            if section.get("type") == "SONG":
                for meta in section.get("metadata", []):
                    key = meta.get("title", "").lower()
                    val = meta.get("text", "")
                    if "album" in key:
                        data["album"] = val
                    elif "released" in key or "year" in key:
                        data["year"] = val[:4]
        images = track.get("images", {})
        data["cover_url"] = images.get("coverarthq") or images.get("coverart") or ""
    except Exception:
        pass
    return data


def download_cover(url: str):
    if not url:
        return None
    try:
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            return r.content
    except Exception:
        pass
    return None


def write_tags(path: Path, title, artist, album, genre, year, cover_data):
    ext = path.suffix.lower()
    try:
        if ext == ".mp3":
            try:
                audio = ID3(str(path))
            except ID3NoHeaderError:
                audio = ID3()
            audio.add(TIT2(encoding=3, text=title))
            audio.add(TPE1(encoding=3, text=artist))
            if album:      audio.add(TALB(encoding=3, text=album))
            if genre:      audio.add(TCON(encoding=3, text=genre))
            if year:       audio.add(TDRC(encoding=3, text=year))
            if cover_data: audio.add(APIC(encoding=3, mime="image/jpeg",
                                          type=3, desc="Cover", data=cover_data))
            audio.save(str(path))
        elif ext == ".flac":
            audio = FLAC(str(path))
            audio["title"], audio["artist"] = title, artist
            if album: audio["album"] = album
            if genre: audio["genre"] = genre
            if year:  audio["date"]  = year
            if cover_data:
                pic = Picture()
                pic.type = 3; pic.mime = "image/jpeg"; pic.data = cover_data
                audio.clear_pictures(); audio.add_picture(pic)
            audio.save()
        elif ext in (".m4a", ".aac"):
            audio = MP4(str(path))
            audio["\xa9nam"] = title; audio["\xa9ART"] = artist
            if album: audio["\xa9alb"] = album
            if genre: audio["\xa9gen"] = genre
            if year:  audio["\xa9day"] = year
            if cover_data:
                audio["covr"] = [MP4Cover(cover_data,
                                          imageformat=MP4Cover.FORMAT_JPEG)]
            audio.save()
        elif ext == ".ogg":
            audio = OggVorbis(str(path))
            audio["title"] = title; audio["artist"] = artist
            if album: audio["album"] = album
            if genre: audio["genre"] = genre
            if year:  audio["date"]  = year
            audio.save()
    except Exception as e:
        raise RuntimeError(f"Tag write failed: {e}")


def sanitize(name: str) -> str:
    name = re.sub(r'[<>:"/\\|?*]', "", name)
    return name.strip(". ") or "Unknown"


# ── Async scan worker ─────────────────────────────────────────────────────────

async def _scan_worker(job_id: str, folder: Path, config: dict):
    job = jobs[job_id]
    job["status"] = "running"

    files = sorted([f for f in folder.rglob("*")
                    if f.suffix.lower() in SUPPORTED_EXT])
    job["total"] = len(files)

    if not files:
        job["status"] = "done"
        job["message"] = "No audio files found."
        return

    shazam = Shazam()
    delay  = float(config.get("rate_limit_delay", 1.5))

    for i, fp in enumerate(files):
        if job.get("cancelled"):
            job["status"] = "cancelled"
            break

        track = {
            "path": str(fp), "original_path": str(fp),
            "status": "running",
            "title": "", "artist": "", "album": "", "genre": "", "year": "",
            "cover_base64": None, "error": ""
        }
        job["tracks"].append(track)
        job["progress"] = i + 1

        try:
            result = await shazam.recognize(str(fp))
            meta   = parse_shazam_result(result)

            if not meta.get("title"):
                track["status"] = "skipped"
                track["error"]  = "Not recognized by Shazam"
            else:
                track.update({
                    "title":  meta["title"],
                    "artist": meta["artist"],
                    "album":  meta.get("album", ""),
                    "genre":  meta.get("genre", ""),
                    "year":   meta.get("year", ""),
                })

                cover_data = None
                if config.get("download_covers", True) and meta.get("cover_url"):
                    cover_data = await asyncio.to_thread(
                        download_cover, meta["cover_url"])
                    if cover_data:
                        track["cover_base64"] = \
                            base64.b64encode(cover_data).decode()

                await asyncio.to_thread(
                    write_tags, fp,
                    track["title"], track["artist"],
                    track["album"], track["genre"],
                    track["year"],  cover_data
                )

                if config.get("rename_files", True) \
                        and track["artist"] and track["title"]:
                    new_name = (sanitize(
                        f"{track['artist']} - {track['title']}") + fp.suffix)
                    new_path = fp.parent / new_name
                    if new_path != fp and not new_path.exists():
                        fp.rename(new_path)
                        track["path"] = str(new_path)

                track["status"] = "done"

        except Exception as e:
            track["status"] = "error"
            track["error"]  = str(e)

        if i < len(files) - 1:
            await asyncio.sleep(delay)

    if not job.get("cancelled"):
        job["status"] = "done"


def run_scan_thread(job_id: str, folder: Path, config: dict):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(_scan_worker(job_id, folder, config))
    finally:
        loop.close()


# ── Flask Routes ──────────────────────────────────────────────────────────────

@app.get("/")
def index():
    return send_from_directory(str(TEMPLATE_DIR), "index.html")


@app.post("/api/scan")
def start_scan():
    data       = request.json or {}
    folder_str = data.get("folder_path", "").strip()
    config     = data.get("config", {})

    folder = Path(folder_str)
    if not folder.exists() or not folder.is_dir():
        return jsonify({"error": "Folder not found or not a directory."}), 400

    job_id = str(uuid.uuid4())
    jobs[job_id] = {
        "job_id": job_id, "status": "pending",
        "progress": 0, "total": 0, "tracks": []
    }

    t = threading.Thread(target=run_scan_thread,
                         args=(job_id, folder, config), daemon=True)
    t.start()
    return jsonify({"job_id": job_id})


@app.get("/api/scan/<job_id>")
def get_scan(job_id):
    job = jobs.get(job_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404
    return jsonify(job)


@app.post("/api/scan/<job_id>/cancel")
def cancel_scan(job_id):
    job = jobs.get(job_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404
    job["cancelled"] = True
    return jsonify({"ok": True})


@app.post("/api/organize")
def organize():
    data     = request.json or {}
    job_id   = data.get("job_id")
    scheme   = data.get("scheme", "artist/album")
    out_root = data.get("output_folder", "")

    job = jobs.get(job_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404
    if job["status"] != "done":
        return jsonify({"error": "Scan not finished"}), 400

    done_tracks = [t for t in job["tracks"] if t["status"] == "done"]
    if not done_tracks:
        return jsonify({"moved": 0})

    base  = Path(out_root) if out_root else Path(done_tracks[0]["path"]).parent
    moved = 0

    for t in done_tracks:
        cur   = Path(t["path"])
        parts = {
            "artist": sanitize(t["artist"] or "Unknown Artist"),
            "album":  sanitize(t["album"]  or "Unknown Album"),
            "genre":  sanitize(t["genre"]  or "Unknown Genre"),
        }
        if scheme == "genre/artist/album":
            dest_dir = base / parts["genre"] / parts["artist"] / parts["album"]
        elif scheme == "artist/album":
            dest_dir = base / parts["artist"] / parts["album"]
        elif scheme == "artist":
            dest_dir = base / parts["artist"]
        else:
            dest_dir = base

        dest_dir.mkdir(parents=True, exist_ok=True)
        dest = dest_dir / cur.name
        c = 1
        while dest.exists() and dest != cur:
            dest = dest_dir / f"{cur.stem} ({c}){cur.suffix}"
            c += 1

        if dest != cur:
            shutil.move(str(cur), str(dest))
            t["path"] = str(dest)
            moved += 1

    return jsonify({"moved": moved})


@app.get("/api/pick-folder")
def pick_folder():

    import subprocess
    chosen = None
    try:
        if sys.platform == "darwin":
            script = ('POSIX path of (choose folder '
                      'with prompt "Select your music folder")')
            r = subprocess.run(["osascript", "-e", script],
                               capture_output=True, text=True, timeout=60)
            if r.returncode == 0:
                chosen = r.stdout.strip()
        elif sys.platform == "win32":
            ps = ("Add-Type -AssemblyName System.Windows.Forms;"
                  "$d = New-Object System.Windows.Forms.FolderBrowserDialog;"
                  "$d.Description = 'Select your music folder';"
                  "if ($d.ShowDialog() -eq 'OK') { $d.SelectedPath }")
            r = subprocess.run(["powershell", "-NoProfile", "-Command", ps],
                               capture_output=True, text=True, timeout=60)
            if r.returncode == 0 and r.stdout.strip():
                chosen = r.stdout.strip()
        else:
            for cmd in [
                ["zenity", "--file-selection", "--directory",
                 "--title=Select music folder"],
                ["kdialog", "--getexistingdirectory",
                 os.path.expanduser("~")],
            ]:
                try:
                    r = subprocess.run(cmd, capture_output=True,
                                       text=True, timeout=60)
                    if r.returncode == 0 and r.stdout.strip():
                        chosen = r.stdout.strip()
                        break
                except FileNotFoundError:
                    continue
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    if chosen:
        return jsonify({"path": chosen})
    return jsonify({"path": None, "cancelled": True})


@app.get("/api/jobs")
def list_jobs():
    return jsonify([
        {"job_id": j["job_id"], "status": j["status"],
         "progress": j["progress"], "total": j["total"]}
        for j in jobs.values()
    ])


# ── PyWebView API (folder picker via native dialog) ───────────────────────────

class MiktagAPI:


    def pick_folder(self):
        result = webview.windows[0].create_file_dialog(
            webview.FOLDER_DIALOG,
            allow_multiple=False
        )
        if result and len(result) > 0:
            return result[0]
        return None


# ── Entry point ───────────────────────────────────────────────────────────────

def start_flask():
    """Run Flask in a background thread (used in GUI mode)."""
    app.run(host="127.0.0.1", port=5000, debug=False,
            use_reloader=False, threaded=True)


if __name__ == "__main__":
    # ── GUI mode (default) ────────────────────────────────────────
    flask_thread = threading.Thread(target=start_flask, daemon=True)
    flask_thread.start()

    # Give Flask a moment to bind
    import time; time.sleep(0.8)

    api = MiktagAPI()
    window = webview.create_window(
        title    = "miktag",
        url      = "http://127.0.0.1:5000",
        width    = 1100,
        height   = 720,
        min_size = (800, 560),
        js_api   = api,
    )

    # Use CEF on Windows for best compatibility; default on others
    gui = "cef" if sys.platform == "win32" else None
    webview.start(gui=gui, debug=False)
