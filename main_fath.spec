# -*- mode: python ; coding: utf-8 -*-
# Build spec file cho FathTTS với VieNeu-TTS
# Sử dụng: pyinstaller main_fath.spec --clean

import sys
from pathlib import Path

# Đường dẫn VieNeu-TTS
vieneu_path = Path('.') / 'VieNeu-TTS'

# Block cipher (None = không mã hóa)
block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=[
        str(vieneu_path),
        str(vieneu_path / 'vieneu_tts'),
        str(vieneu_path / 'utils'),
    ],
    binaries=[
        # Thêm các DLL cần thiết nếu có
        # ('path/to/llama.dll', '.'),
    ],
    datas=[
        # VieNeu-TTS sample voices
        ('VieNeu-TTS/sample', 'VieNeu-TTS/sample'),
        # VieNeu-TTS utils (phoneme dict, etc.)
        ('VieNeu-TTS/utils', 'VieNeu-TTS/utils'),
        # VieNeu-TTS core module
        ('VieNeu-TTS/vieneu_tts', 'VieNeu-TTS/vieneu_tts'),
        # Config file
        ('VieNeu-TTS/config.yaml', 'VieNeu-TTS'),
        # Edge TTS module
        ('edge', 'edge'),
        # CapCut voice data (nếu có)
        # ('capcutvoice', 'capcutvoice'),
        # App icon
        ('icon.ico', '.'),
    ],
    hiddenimports=[
        # ========================================
        # VieNeu-TTS modules
        # ========================================
        'vieneu_tts',
        'utils',
        'utils.core_utils',
        'utils.normalize_text', 
        'utils.phonemize_text',
        
        # ========================================
        # llama.cpp cho model GGUF
        # ========================================
        'llama_cpp',
        'llama_cpp.llama',
        'llama_cpp.llama_cpp',
        
        # ========================================
        # Phonemizer cho text-to-phoneme
        # ========================================
        'phonemizer',
        'phonemizer.phonemize',
        'phonemizer.backend',
        'phonemizer.backend.espeak',
        'phonemizer.backend.espeak.espeak',
        'phonemizer.backend.espeak.wrapper',
        'phonemizer.separator',
        'phonemizer.logger',
        
        # ========================================
        # Audio processing
        # ========================================
        'librosa',
        'librosa.core',
        'librosa.feature',
        'librosa.util',
        'soundfile',
        'neucodec',
        'soxr',
        'resampy',
        
        # ========================================
        # PyTorch
        # ========================================
        'torch',
        'torch.nn',
        'torch.nn.functional',
        'torch.jit',
        'torchaudio',
        'torchaudio.functional',
        'torchaudio.transforms',
        
        # ========================================
        # ONNX Runtime
        # ========================================
        'onnxruntime',
        
        # ========================================
        # UI & Other
        # ========================================
        'customtkinter',
        'tkinter',
        'PIL',
        'PIL._tkinter_finder',
        
        # ========================================
        # Google Gemini (cho các tab khác)
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
        
        # ========================================
        # Scientific computing
        # ========================================
        'numpy',
        'scipy',
        'scipy.signal',
        'scipy.fft',
        
        # ========================================
        # Transformers (cho VieNeu-TTS non-GGUF)
        # ========================================
        'transformers',
        'transformers.models',
        'transformers.models.auto',
        'safetensors',
        'huggingface_hub',
        
        # ========================================
        # Other utilities
        # ========================================
        'yaml',
        'json',
        'asyncio',
        'concurrent',
        'concurrent.futures',
        'threading',
        'multiprocessing',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # ========================================
        # Exclude GPU-specific packages (CPU build)
        # ========================================
        'lmdeploy',
        'triton',
        'triton_windows',
        'cuda',
        'cudnn',
        
        # ========================================
        # Exclude development tools
        # ========================================
        'pytest',
        'unittest',
        'ipython',
        'jupyter',
        'notebook',
        
        # ========================================
        # Exclude unused large packages
        # ========================================
        'matplotlib',
        'pandas',
        'sklearn',
        'tensorflow',
        'keras',
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
    exclude_binaries=True,  # False nếu muốn onefile
    name='FathTTS',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # True để debug, False để release
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='icon.ico',
    version='file_version_info.txt' if Path('file_version_info.txt').exists() else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[
        # Exclude từ UPX compression (có thể gây lỗi)
        'vcruntime140.dll',
        'vcruntime140_1.dll',
        'msvcp140.dll',
        'python*.dll',
    ],
    name='FathTTS',
)
