# -*- mode: python ; coding: utf-8 -*-
import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_all

repo_root = Path(SPECPATH).parent.parent
icon_png = repo_root / "share" / "icons" / "hicolor" / "128x128" / "apps" / "financeguru.png"
build_assets = repo_root / "packaging" / "pyinstaller" / "build-assets"

# curl_cffi's compiled extension + bundled libcurl aren't reachable by
# PyInstaller's static import scan; collect_all is curl_cffi's own documented
# PyInstaller mitigation (a known Windows-specific pain point).
curl_datas, curl_binaries, curl_hidden = collect_all("curl_cffi")

icon_file = None
if sys.platform == "win32":
    icon_file = str(build_assets / "financeguru.ico")
elif sys.platform == "darwin":
    icon_file = str(build_assets / "financeguru.icns")

a = Analysis(
    [str(repo_root / "src" / "financeguru" / "main.py")],
    pathex=[str(repo_root / "src")],
    binaries=curl_binaries,
    datas=[(str(icon_png), ".")] + curl_datas,
    hiddenimports=["_cffi_backend"] + curl_hidden,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz, a.scripts, [],
    exclude_binaries=True,
    name="FinanceGuru",
    console=False,
    icon=icon_file,
)
coll = COLLECT(exe, a.binaries, a.datas, name="FinanceGuru")

if sys.platform == "darwin":
    app = BUNDLE(
        coll,
        name="FinanceGuru.app",
        icon=icon_file,
        bundle_identifier="io.github.CommanderBosko.FinanceGuru",
        info_plist={"NSHighResolutionCapable": True, "CFBundleShortVersionString": "0.1.0"},
    )
