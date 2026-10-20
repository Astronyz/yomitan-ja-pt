#!/usr/bin/env python3
"""Download latest public Yomitan source dictionaries."""
from __future__ import annotations

import shutil
import ssl
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT / "work" / "source-archive"
UA = "yomitan-ja-pt-updater/1.0 (https://github.com/CosmionLabs/yomitan-ja-pt)"

SOURCES = [
    (
        "jitendex-yomitan.zip",
        "https://github.com/stephenmk/stephenmk.github.io/releases/download/2026.10.03.0/jitendex-yomitan.zip",
        "2026.07.09.0",
    ),
    (
        "JMnedict.zip",
        "https://github.com/yomidevs/jmdict-yomitan/releases/download/2026-10-20/JMnedict.zip",
        "2026-10-19",
    ),
    (
        "JMdict_english_with_examples.zip",
        "https://github.com/yomidevs/jmdict-yomitan/releases/download/2026-10-20/JMdict_english_with_examples.zip",
        "2026-10-19",
    ),
    (
        "KANJIDIC_portuguese.zip",
        "https://github.com/yomidevs/jmdict-yomitan/releases/download/2026-10-20/KANJIDIC_portuguese.zip",
        "2026-196",
    ),
]


def download(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".part")
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    ctx = ssl.create_default_context()
    print(f"downloading {url}")
    with urllib.request.urlopen(req, context=ctx, timeout=600) as resp, tmp.open("wb") as out:
        shutil.copyfileobj(resp, out)
        length = resp.headers.get("Content-Length")
    tmp.replace(dest)
    print(f"saved {dest.name} ({dest.stat().st_size} bytes, content-length={length})")


def main() -> None:
    ARCHIVE.mkdir(parents=True, exist_ok=True)
    for name, url, old_rev in SOURCES:
        current = ROOT / name
        if current.exists():
            backup = ARCHIVE / f"{current.stem}-{old_rev}{current.suffix}"
            if not backup.exists():
                shutil.copy2(current, backup)
                print(f"backed up {name} -> {backup.name}")
        download(url, current)
    # rebuild_clean.py reads the later Portuguese KANJIDIC from this filename
    shutil.copy2(ROOT / "KANJIDIC_portuguese.zip", ROOT / "KANJIDIC_portuguese (1).zip")
    print("copied KANJIDIC_portuguese.zip -> KANJIDIC_portuguese (1).zip")


if __name__ == "__main__":
    main()
