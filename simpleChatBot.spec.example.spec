# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['simpleChatBot.py', 'main.py', 'chatbot.py'],
    pathex=[],
    binaries=[],
    datas=[
        ("C:/ProgramData/Anaconda3/envs/chatbot/Lib/site-packages/altair/vegalite/v5/schema/vega-lite-schema.json",
         "./altair/vegalite/v4/schema/"
         ),
        ("C:/ProgramData/Anaconda3/envs/chatbot/Lib/site-packages/streamlit/static",
         "./streamlit/static"
         ),
        ("C:/ProgramData/Anaconda3/envs/chatbot/Lib/site-packages/streamlit/runtime",
         "./streamlit/runtime"
         ),
        ],
    hiddenimports=[],
    hookspath=['./hooks'],
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
    name='simpleChatBot',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
