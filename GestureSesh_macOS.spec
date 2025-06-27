# -*- mode: python ; coding: utf-8 -*-
import os
from PyInstaller.utils.hooks import collect_submodules
from PyInstaller.building.osx import BUNDLE
from PyInstaller.building.api import COLLECT, EXE, PYZ
from PyInstaller.building.build_main import Analysis

block_cipher = None
hiddenimports = collect_submodules('pygame')

a = Analysis(
    ['GestureSesh.py'],
    pathex=[],
    binaries=[],
    datas=[('sounds/*.mp3', 'sounds')],
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='GestureSesh',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    name='GestureSesh',
)

app = BUNDLE(
    coll,
    name='GestureSesh.app',
    icon='ui/resources/icons/brush.icns',
    bundle_identifier='com.gesturesesh.gesturesesh',
    version='0.4.3',
    codesign_identity=os.environ.get('CODESIGN_IDENTITY'),
)