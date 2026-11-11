"""Download what the human is built from, into assets/cache/mpfb/ (not committed).

    python3 projects/03-character/fetch.py

  * MPFB2, the MakeHuman add-on for Blender (GPL-3.0-or-later code), from
    extensions.blender.org, and installs it into Blender as an extension.
  * The MakeHuman system assets pack (CC0): skins, clothes, hair, eyes.

Both archives are checked against a pinned SHA-256 before use.
"""

from __future__ import annotations

import hashlib
import subprocess
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CACHE = ROOT / "assets" / "cache" / "mpfb"
PACK = CACHE / "pack"

ADDON = (
    "add-on-mpfb-v2.0.18.zip",
    "https://extensions.blender.org/download/"
    "sha256:c075b3e9b94b8e5556a5f03f4653602d02ea306de08126e8f55ed6dee28a2dad/add-on-mpfb-v2.0.18.zip",
    "c075b3e9b94b8e5556a5f03f4653602d02ea306de08126e8f55ed6dee28a2dad",
)
ASSETS = (
    "makehuman_system_assets_cc0.zip",
    "https://files.makehumancommunity.org/asset_packs/makehuman_system_assets/makehuman_system_assets_cc0.zip",
    "b542127a8e25547c7c29c19f2d1d2adb9a664c80396ecd694095dbc8028a0107",
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def download(name: str, url: str, expected: str) -> Path:
    path = CACHE / name
    if not path.exists():
        print(f"  + {name}")
        CACHE.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".part")
        request = urllib.request.Request(url, headers={"User-Agent": "blender-character-builder"})
        with urllib.request.urlopen(request, timeout=600) as response, tmp.open("wb") as out:
            for block in iter(lambda: response.read(1 << 20), b""):
                out.write(block)
        tmp.rename(path)
    found = sha256(path)
    if found != expected:
        raise SystemExit(f"{name}: SHA-256 is {found}, expected {expected}")
    return path


def main():
    addon = download(*ADDON)
    if any(Path.home().glob(".config/blender/*/extensions/user_default/mpfb")):
        print("  = MPFB2 already installed")
    else:
        subprocess.run(["blender", "-b", "--command", "extension", "install-file",
                        "-r", "user_default", "-e", str(addon)], check=True)
    pack = download(*ASSETS)
    if not (PACK / "clothes").is_dir():
        print("  ~ extracting the asset pack")
        with zipfile.ZipFile(pack) as archive:
            archive.extractall(PACK)
    print("ready:", PACK)


if __name__ == "__main__":
    main()
