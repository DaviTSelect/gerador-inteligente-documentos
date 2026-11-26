# -*- mode: python ; coding: utf-8 -*-
import glob
import os
import lxml as _lxml_pkg
from PyInstaller.utils.hooks import collect_all

datas = [('version.txt', '.'), ('../logo.ico', '.')]
binaries = []
hiddenimports = ['openpyxl', 'openpyxl.cell._writer', 'pandas', 'docx', 'win32com', 'win32com.client', 'win32com.server', 'win32api', 'win32con', 'pywintypes', 'truststore']
tmp_ret = collect_all('chardet')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('docx2pdf')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
# lxml: collect_all não captura os .pyd em lxml 6.x; coleta explícita
_lxml_dir = os.path.dirname(_lxml_pkg.__file__)
binaries += [(p, 'lxml') for p in glob.glob(os.path.join(_lxml_dir, '*.pyd'))]
hiddenimports += ['lxml.etree', 'lxml._elementpath', 'lxml.builder', 'lxml.objectify']


a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='GeradorDocumentos',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['../logo.ico'],
)
