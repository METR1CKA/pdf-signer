"""Receta de PyInstaller para el binario de PDF Signer.

Construir con: pyinstaller pdf-signer.spec --noconfirm
En Windows/Linux el resultado es dist/pdf-signer(.exe); en macOS, dist/pdf-signer.app.
"""

import sys

from PyInstaller.utils.hooks import collect_all

datas, binaries, hiddenimports = collect_all("pymupdf")

a = Analysis(
    ["main.py"],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="pdf-signer",
    console=False,
    upx=False,  # UPX dispara falsos positivos de antivirus
)

if sys.platform == "darwin":
    app = BUNDLE(
        exe,
        name="pdf-signer.app",
    )
