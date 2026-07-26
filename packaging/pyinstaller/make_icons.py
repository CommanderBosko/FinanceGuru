from pathlib import Path

from PIL import Image

_SRC = Path(__file__).resolve().parents[2] / "share/icons/hicolor/128x128/apps/financeguru.png"
_OUT_DIR = Path(__file__).resolve().parent / "build-assets"


def main() -> None:
    _OUT_DIR.mkdir(exist_ok=True)
    img = Image.open(_SRC)
    img.save(
        _OUT_DIR / "financeguru.ico",
        sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)],
    )
    img.save(_OUT_DIR / "financeguru.icns")


if __name__ == "__main__":
    main()
