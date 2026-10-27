"""Install the verified official Keyboop DMG. Never redistribute or modify Keyboop."""
import hashlib
import json
import os
import platform
import plistlib
import re
import shutil
import subprocess
import tempfile
import urllib.request
from pathlib import Path

RELEASE_API = "https://api.github.com/repos/iffuno/keyboop/releases/latest"
ASSET = re.compile(r"^Keyboop-[0-9][0-9.]*\.dmg$")
MAX_DMG = 250 * 1024 * 1024


def installed_path():
    app_dirs = (Path.home() / "Applications", Path("/Applications"))
    for directory in app_dirs:
        for item in [directory / "Keyboop.app", *sorted(directory.glob("*Keyboop*.app"))]:
            info = item / "Contents" / "Info.plist"
            if not info.is_file():
                continue
            try:
                bundle_id = plistlib.loads(info.read_bytes()).get("CFBundleIdentifier", "")
            except (ValueError, OSError, TypeError):
                continue
            if bundle_id == "ru.keyboop.app" or bundle_id.startswith("ru.keyboop.app."):
                return item
    return None


def asset_from_release(release):
    for entry in release.get("assets", []):
        name = entry.get("name", "")
        url = entry.get("browser_download_url", "")
        size = entry.get("size", 0)
        if (ASSET.fullmatch(name)
                and url.startswith("https://github.com/iffuno/keyboop/releases/download/")
                and url.endswith("/" + name)
                and isinstance(size, int) and 100000 < size < MAX_DMG):
            return entry
    raise RuntimeError("Official Keyboop release has no supported DMG")


def _fetch_json(url):
    req = urllib.request.Request(url, headers={
        "Accept": "application/vnd.github+json", "User-Agent": "KeyboopOmniVoiceInstaller/0.2"
    })
    with urllib.request.urlopen(req, timeout=30) as response:
        return json.load(response)


def install_keyboop(launch=True):
    if platform.system() != "Darwin":
        raise RuntimeError("Keyboop requires macOS")
    prior = installed_path()
    if prior:
        return prior
    release = _fetch_json(RELEASE_API)
    asset = asset_from_release(release)
    with tempfile.TemporaryDirectory(prefix="kov-keyboop-") as root:
        root = Path(root)
        dmg = root / asset["name"]
        digest = hashlib.sha256()
        size = 0
        req = urllib.request.Request(asset["browser_download_url"],
                                     headers={"User-Agent": "KeyboopOmniVoiceInstaller/0.2"})
        with urllib.request.urlopen(req, timeout=90) as response, dmg.open("wb") as out:
            while True:
                block = response.read(1024 * 1024)
                if not block:
                    break
                size += len(block)
                if size > MAX_DMG:
                    raise RuntimeError("Keyboop DMG exceeds maximum size")
                digest.update(block)
                out.write(block)
        if size != asset["size"]:
            raise RuntimeError("Keyboop download size mismatch")
        reported_digest = asset.get("digest")
        if reported_digest and reported_digest.startswith("sha256:"):
            if digest.hexdigest() != reported_digest.removeprefix("sha256:"):
                raise RuntimeError("Keyboop download SHA256 mismatch")
        mount = root / "mounted"
        mount.mkdir()
        subprocess.run(["hdiutil", "attach", "-readonly", "-nobrowse",
                        "-mountpoint", str(mount), str(dmg)],
                       capture_output=True, text=True, check=True, timeout=60)
        try:
            candidates = list(mount.rglob("Keyboop.app"))
            if len(candidates) != 1 or not candidates[0].is_dir():
                raise RuntimeError("Expected a single Keyboop.app in official DMG")
            app = candidates[0]
            subprocess.run(["codesign", "--verify", "--deep", "--strict", str(app)],
                           check=True, capture_output=True, timeout=30)
            subprocess.run(["spctl", "--assess", "--type", "execute", str(app)],
                           check=True, capture_output=True, timeout=30)
            target_dir = Path.home() / "Applications"
            target_dir.mkdir(parents=True, exist_ok=True)
            dest = target_dir / "Keyboop.app"
            if dest.exists():
                return dest
            subprocess.run(["ditto", str(app), str(dest)],
                           check=True, capture_output=True, timeout=60)
            subprocess.run(["codesign", "--verify", "--deep", "--strict", str(dest)],
                           check=True, capture_output=True, timeout=30)
        finally:
            subprocess.run(["hdiutil", "detach", str(mount)],
                           check=False, capture_output=True, timeout=60)
    if launch:
        subprocess.run(["open", str(dest)], check=False, timeout=15)
    return dest
