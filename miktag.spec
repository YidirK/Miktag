# miktag.spec
# Run with: pyinstaller miktag.spec

import sys
from pathlib import Path

block_cipher = None
IS_WIN   = sys.platform == "win32"
IS_MAC   = sys.platform == "darwin"
IS_LINUX = sys.platform.startswith("linux")

a = Analysis(
    ['app.py'],
    pathex=['.'],
    binaries=[],
    datas=[
        # Bundle the entire templates folder
        ('templates', 'templates'),
        ('static',    'static'),
    ],
    hiddenimports=[
        # Flask internals
        'flask', 'jinja2', 'werkzeug',
        # PyWebView backends
        'webview',
        'webview.platforms.winforms',   # Windows
        'webview.platforms.cocoa',      # macOS
        'webview.platforms.gtk',        # Linux GTK
        'webview.platforms.qt',         # Linux Qt fallback
        # Mutagen formats
        'mutagen', 'mutagen.mp3', 'mutagen.id3',
        'mutagen.flac', 'mutagen.mp4', 'mutagen.oggvorbis',
        # Shazam / async
        'shazamio', 'aiohttp', 'asyncio',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'matplotlib', 'numpy', 'pandas', 'PIL'],
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
    name='miktag',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,          # No terminal window
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    # Windows: embed icon
    icon='assets/icon.ico' if IS_WIN else (
         'assets/icon.icns' if IS_MAC else None),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='miktag',
)

# macOS: wrap in a .app bundle
if IS_MAC:
    app = BUNDLE(
        coll,
        name='miktag.app',
        icon='assets/icon.icns',
        bundle_identifier='com.hergol.miktag',
        info_plist={
            'NSHighResolutionCapable': True,
            'LSMinimumSystemVersion': '10.13.0',
            'CFBundleShortVersionString': '1.0.0',
            'NSMicrophoneUsageDescription': 'miktag reads audio files to identify tracks.',
        },
    )
