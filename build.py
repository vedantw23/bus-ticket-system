from __future__ import annotations

import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parent
STATIC_SRC = ROOT / "static"
PUBLIC_STATIC = ROOT / "public" / "static"


def main() -> None:
    PUBLIC_STATIC.mkdir(parents=True, exist_ok=True)
    for source in STATIC_SRC.rglob("*"):
        if source.is_file():
            destination = PUBLIC_STATIC / source.relative_to(STATIC_SRC)
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
    print(f"Prepared Vercel public assets in {PUBLIC_STATIC}")


if __name__ == "__main__":
    main()
