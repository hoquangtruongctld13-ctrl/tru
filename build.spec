# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for VN TTS Studio
Build: pyinstaller build.spec --clean --noconfirm

Notes:
- Heavy libraries (torch, librosa, neucodec, etc.) are NOT bundled
- They should be copied to the build folder separately
- This keeps the main exe small and build times reasonable
"""

import sys
from pathlib import Path

block_cipher = None

# Get the directory where this spec file is located
SPEC_DIR = Path(SPECPATH)

a = Analysis(
    ['main.py'],
    pathex=[
        str(SPEC_DIR),
        str(SPEC_DIR / 'vntts'),
        str(SPEC_DIR / 'vntts' / 'vieneu_tts'),
        str(SPEC_DIR / 'vntts' / 'utils'),
        str(SPEC_DIR / 'edge'),
        str(SPEC_DIR / 'capcutvoice'),
    ],
    binaries=[],
    datas=[
        # VN TTS voice samples (required)
        ('vntts/sample', 'vntts/sample'),
        # VN TTS utils (phoneme dictionary, etc.)
        ('vntts/utils', 'vntts/utils'),
        # VN TTS core module
        ('vntts/vieneu_tts', 'vntts/vieneu_tts'),
        # VN TTS config
        ('vntts/config.yaml', 'vntts'),
        # Edge TTS module
        ('edge', 'edge'),
        # Capcut voice module
        ('capcutvoice', 'capcutvoice'),
        # Icon
        ('icon.ico', '.'),
    ],
    hiddenimports=[
        # ========================================
        # VN TTS modules
        # ========================================
        'vieneu_tts',
        'vieneu_tts.vieneu_tts',
        'utils',
        'utils.core_utils',
        'utils.normalize_text', 
        'utils.phonemize_text',
        
        # ========================================
        # Edge TTS
        # ========================================
        'edge',
        'edge.communicate',
        'edge.constants',
        'edge.data_classes',
        'edge.exceptions',
        'edge.submaker',
        'edge.util',
        'edge.voices',
        
        # ========================================
        # Capcut voice
        # ========================================
        'capcutvoice',
        'capcutvoice.tts',
        'capcutvoice.tts_helper',
        'capcutvoice.split_text',
        
        # ========================================
        # UI
        # ========================================
        'customtkinter',
        'tkinter',
        'tkinter.filedialog',
        'tkinter.messagebox',
        'PIL',
        'PIL._tkinter_finder',
        
        # ========================================
        # Google Gemini
        # ========================================
        'google',
        'google.genai',
        'google.genai.types',
        
        # ========================================
        # Document processing
        # ========================================
        'docx',
        'docx.document',
        'docx.oxml',
        
        # ========================================
        # Network
        # ========================================
        'requests',
        'urllib3',
        'certifi',
        'websockets',
        
        # ========================================
        # Standard library
        # ========================================
        'asyncio',
        'concurrent',
        'concurrent.futures',
        'threading',
        'multiprocessing',
        'json',
        'yaml',
        'queue',
        'wave',
        'base64',
        
        # ========================================
        # PyAudio (optional)
        # ========================================
        'pyaudio',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Exclude heavy ML/DL libraries - they'll be copied separately
        'torch',
        'torchvision', 
        'torchaudio',
        'librosa',
        'neucodec',
        'phonemizer',
        'transformers',
        'llama_cpp',
        'lmdeploy',
        'onnxruntime',
        'triton',
        'triton_windows',
        
        # Exclude scientific libraries (included with torch)
        'numpy',
        'scipy',
        'pandas',
        'sklearn',
        
        # Exclude development tools
        'pytest',
        'unittest',
        'ipython',
        'jupyter',
        'notebook',
        'matplotlib',
        
        # Exclude unused ML frameworks
        'tensorflow',
        'keras',
        
        # Exclude cuda-specific
        'cuda',
        'cudnn',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,  # Use folder structure, not single file
    name='VNTTSStudio',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # Set to True for debugging
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='icon.ico',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[
        'vcruntime140.dll',
        'vcruntime140_1.dll',
        'msvcp140.dll',
        'python*.dll',
    ],
    name='VNTTSStudio',
)
