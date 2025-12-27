import json
import os
import re
import wave
import asyncio
import threading
import tkinter as tk  
from tkinter import filedialog, messagebox
import customtkinter as ctk 
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from queue import Queue, Empty
import time
import subprocess
import glob
import random
import requests
import base64
import shutil
import sys
import concurrent.futures
from urllib.parse import quote

# =============================================================================
# PATH SETUP - Add module paths for PyInstaller build
# =============================================================================

def _setup_paths():
    """Setup sys.path for both development and PyInstaller builds"""
    if getattr(sys, 'frozen', False):
        # Running as PyInstaller bundle
        app_dir = os.path.dirname(sys.executable)
        
        # Add _libs folder for heavy libraries
        libs_dir = os.path.join(app_dir, '_libs')
        if os.path.exists(libs_dir) and libs_dir not in sys.path:
            sys.path.insert(0, libs_dir)
    else:
        # Running as script
        app_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Add module paths
    if app_dir not in sys.path:
        sys.path.insert(0, app_dir)
    
    # Add vntts paths for VN TTS imports
    vntts_dir = os.path.join(app_dir, 'vntts')
    if os.path.exists(vntts_dir) and vntts_dir not in sys.path:
        sys.path.insert(0, vntts_dir)
    
    return app_dir

_APP_DIR = _setup_paths()

# Import authentication module
from auth_module import AuthManager, require_login

# Cấu hình giao diện CustomTkinter
ctk.set_appearance_mode("Dark")  # Modes: "System" (standard), "Dark", "Light"
ctk.set_default_color_theme("blue")  # Themes: "blue" (standard), "green", "dark-blue"

try:
    import pyaudio
    HAS_PYAUDIO = True
except ImportError:
    HAS_PYAUDIO = False

from google import genai
from google.genai import types


# =============================================================================
# CONFIGURATION
# =============================================================================

MODEL = "models/gemini-2.5-flash-native-audio-preview-12-2025"

RECEIVE_SAMPLE_RATE = 24000
AUDIO_CHANNELS = 1
AUDIO_SAMPLE_WIDTH = 2

VOICES = [
    "Zephyr", "Puck", "Charon", "Kore", "Fenrir", "Leda", "Orus", "Aoede",
    "Callirrhoe", "Autonoe", "Enceladus", "Iapetus", "Umbriel", "Algieba",
    "Despina", "Erinome", "Algenib", "Rasalgethi", "Laomedeia", "Achernar",
    "Alnilam", "Schedar", "Gacrux", "Pulcherrima", "Achird", "Zubenelgenubi",
    "Vindemiatrix", "Sadachbia", "Sadaltager", "Sulafat"
]

MEDIA_RESOLUTIONS = {
    "Low (66 tokens/image)": "MEDIA_RESOLUTION_LOW",
    "Medium (258 tokens/image)": "MEDIA_RESOLUTION_MEDIUM", 
    "High (Auto)": "MEDIA_RESOLUTION_HIGH",
}

DEFAULT_SYSTEM_INSTRUCTION = "Chỉ cần đọc chính xác những gì tôi gửi. Không thêm, không bớt, không giải thích gì thêm."

# =============================================================================
# CAPCUT VOICE CONFIGURATION
# =============================================================================

CAPCUT_TTS_URL = 'https://api16-normal-v6.tiktokv.com/media/api/text/speech/invoke'

# Default Capcut Voices (from list voice.txt)
DEFAULT_CAPCUT_VOICES = [
    # Vietnamese
    {"voice_id": "vi_female_huong", "display_name": "Giọng Nữ Xàm lz", "category": "Tiếng Việt", "gender": "Nữ", "language": "vi"},
    {"voice_id": "BV074_streaming", "display_name": "Cô Gái Nói Nhiều", "category": "Tiếng Việt", "gender": "Nữ", "language": "vi"},
    {"voice_id": "BV075_streaming", "display_name": "Thằng Cha nói lắm", "category": "Tiếng Việt", "gender": "Nam", "language": "vi"},
    # Disney
    {"voice_id": "en_us_ghostface", "display_name": "Ghost Face (Disney)", "category": "Disney", "gender": "Khác", "language": "en"},
    {"voice_id": "en_us_chewbacca", "display_name": "Chewbacca (Disney)", "category": "Disney", "gender": "Khác", "language": "en"},
    {"voice_id": "en_us_c3po", "display_name": "C3PO (Disney)", "category": "Disney", "gender": "Khác", "language": "en"},
    {"voice_id": "en_us_stitch", "display_name": "Stitch (Disney)", "category": "Disney", "gender": "Khác", "language": "en"},
    {"voice_id": "en_us_stormtrooper", "display_name": "Stormtrooper (Disney)", "category": "Disney", "gender": "Khác", "language": "en"},
    {"voice_id": "en_us_rocket", "display_name": "Rocket (Disney)", "category": "Disney", "gender": "Khác", "language": "en"},
    # English
    {"voice_id": "en_au_001", "display_name": "Úc - Nữ", "category": "Tiếng Anh", "gender": "Nữ", "language": "en"},
    {"voice_id": "en_au_002", "display_name": "Úc - Nam", "category": "Tiếng Anh", "gender": "Nam", "language": "en"},
    {"voice_id": "en_uk_001", "display_name": "Anh - Nam 1", "category": "Tiếng Anh", "gender": "Nam", "language": "en"},
    {"voice_id": "en_uk_003", "display_name": "Anh - Nam 2", "category": "Tiếng Anh", "gender": "Nam", "language": "en"},
    {"voice_id": "en_us_001", "display_name": "Mỹ - Nữ 1", "category": "Tiếng Anh", "gender": "Nữ", "language": "en"},
    {"voice_id": "en_us_002", "display_name": "Mỹ - Nữ 2", "category": "Tiếng Anh", "gender": "Nữ", "language": "en"},
    {"voice_id": "en_us_006", "display_name": "Mỹ - Nam 1", "category": "Tiếng Anh", "gender": "Nam", "language": "en"},
    {"voice_id": "en_us_007", "display_name": "Mỹ - Nam 2", "category": "Tiếng Anh", "gender": "Nam", "language": "en"},
    {"voice_id": "en_us_009", "display_name": "Mỹ - Nam 3", "category": "Tiếng Anh", "gender": "Nam", "language": "en"},
    {"voice_id": "en_us_010", "display_name": "Mỹ - Nam 4", "category": "Tiếng Anh", "gender": "Nam", "language": "en"},
    # Europe
    {"voice_id": "fr_001", "display_name": "Pháp - Nam 1", "category": "Châu Âu", "gender": "Nam", "language": "fr"},
    {"voice_id": "fr_002", "display_name": "Pháp - Nam 2", "category": "Châu Âu", "gender": "Nam", "language": "fr"},
    {"voice_id": "de_001", "display_name": "Đức - Nữ", "category": "Châu Âu", "gender": "Nữ", "language": "de"},
    {"voice_id": "de_002", "display_name": "Đức - Nam", "category": "Châu Âu", "gender": "Nam", "language": "de"},
    {"voice_id": "es_002", "display_name": "Tây Ban Nha - Nam", "category": "Châu Âu", "gender": "Nam", "language": "es"},
    # America
    {"voice_id": "es_mx_002", "display_name": "Mexico - Nam", "category": "Châu Mỹ", "gender": "Nam", "language": "es"},
    {"voice_id": "br_001", "display_name": "Brazil - Nữ 1", "category": "Châu Mỹ", "gender": "Nữ", "language": "pt"},
    {"voice_id": "br_003", "display_name": "Brazil - Nữ 2", "category": "Châu Mỹ", "gender": "Nữ", "language": "pt"},
    {"voice_id": "br_004", "display_name": "Brazil - Nữ 3", "category": "Châu Mỹ", "gender": "Nữ", "language": "pt"},
    {"voice_id": "br_005", "display_name": "Brazil - Nam", "category": "Châu Mỹ", "gender": "Nam", "language": "pt"},
    # Asia
    {"voice_id": "id_001", "display_name": "Indonesia - Nữ", "category": "Châu Á", "gender": "Nữ", "language": "id"},
    {"voice_id": "jp_001", "display_name": "Nhật Bản - Nữ 1", "category": "Châu Á", "gender": "Nữ", "language": "ja"},
    {"voice_id": "jp_003", "display_name": "Nhật Bản - Nữ 2", "category": "Châu Á", "gender": "Nữ", "language": "ja"},
    {"voice_id": "jp_005", "display_name": "Nhật Bản - Nữ 3", "category": "Châu Á", "gender": "Nữ", "language": "ja"},
    {"voice_id": "jp_006", "display_name": "Nhật Bản - Nam", "category": "Châu Á", "gender": "Nam", "language": "ja"},
    {"voice_id": "kr_002", "display_name": "Hàn Quốc - Nam 1", "category": "Châu Á", "gender": "Nam", "language": "ko"},
    {"voice_id": "kr_003", "display_name": "Hàn Quốc - Nữ", "category": "Châu Á", "gender": "Nữ", "language": "ko"},
    {"voice_id": "kr_004", "display_name": "Hàn Quốc - Nam 2", "category": "Châu Á", "gender": "Nam", "language": "ko"},
    # Singing
    {"voice_id": "en_female_f08_salut_damour", "display_name": "Alto (Nữ cao)", "category": "Ca hát", "gender": "Nữ", "language": "en"},
    {"voice_id": "en_male_m03_lobby", "display_name": "Tenor (Nam cao)", "category": "Ca hát", "gender": "Nam", "language": "en"},
    {"voice_id": "en_female_f08_warmy_breeze", "display_name": "Warmy Breeze (Nữ ấm áp)", "category": "Ca hát", "gender": "Nữ", "language": "en"},
    {"voice_id": "en_male_m03_sunshine_soon", "display_name": "Sunshine Soon (Nam sáng)", "category": "Ca hát", "gender": "Nam", "language": "en"},
    # Special
    {"voice_id": "en_male_narration", "display_name": "Kể chuyện (Nam)", "category": "Đặc biệt", "gender": "Nam", "language": "en"},
    {"voice_id": "en_male_funny", "display_name": "Hài hước (Nam)", "category": "Đặc biệt", "gender": "Nam", "language": "en"},
    {"voice_id": "en_female_emotional", "display_name": "Cảm xúc (Nữ)", "category": "Đặc biệt", "gender": "Nữ", "language": "en"},
]

# Language list for filters
CAPCUT_LANGUAGES = ["Tất cả", "vi", "en", "ja", "ko", "fr", "de", "es", "pt", "id"]
CAPCUT_GENDERS = ["Tất cả", "Nam", "Nữ", "Khác"]

# =============================================================================
# EDGE TTS CONFIGURATION  
# =============================================================================

EDGE_TTS_VOICE_URL = "https://speech.platform.bing.com/consumer/speech/synthesize/readaloud/voices/list?trustedclienttoken=6A5AA1D4EAFF4E9FB37E23D68491D6F4"

# Complete list of Edge TTS supported languages with full names
# Maps display name -> language code for filtering
EDGE_TTS_LANGUAGE_MAP = {
    "Tất cả": "",
    "Tiếng Việt (Vietnamese)": "vi",
    "Tiếng Anh (English)": "en",
    "Tiếng Nhật (Japanese)": "ja",
    "Tiếng Hàn (Korean)": "ko",
    "Tiếng Trung (Chinese)": "zh",
    "Tiếng Pháp (French)": "fr",
    "Tiếng Đức (German)": "de",
    "Tiếng Tây Ban Nha (Spanish)": "es",
    "Tiếng Bồ Đào Nha (Portuguese)": "pt",
    "Tiếng Nga (Russian)": "ru",
    "Tiếng Ý (Italian)": "it",
    "Tiếng Ả Rập (Arabic)": "ar",
    "Tiếng Thái (Thai)": "th",
    "Tiếng Indonesia (Indonesian)": "id",
    "Tiếng Hindi (Hindi)": "hi",
    "Tiếng Hà Lan (Dutch)": "nl",
    "Tiếng Ba Lan (Polish)": "pl",
    "Tiếng Thổ Nhĩ Kỳ (Turkish)": "tr",
    "Tiếng Séc (Czech)": "cs",
    "Tiếng Đan Mạch (Danish)": "da",
    "Tiếng Phần Lan (Finnish)": "fi",
    "Tiếng Hy Lạp (Greek)": "el",
    "Tiếng Do Thái (Hebrew)": "he",
    "Tiếng Hungary (Hungarian)": "hu",
    "Tiếng Na Uy (Norwegian)": "nb",
    "Tiếng Rumani (Romanian)": "ro",
    "Tiếng Slovak (Slovak)": "sk",
    "Tiếng Thụy Điển (Swedish)": "sv",
    "Tiếng Ukraina (Ukrainian)": "uk",
    "Tiếng Bengal (Bengali)": "bn",
    "Tiếng Gujarat (Gujarati)": "gu",
    "Tiếng Kannada (Kannada)": "kn",
    "Tiếng Malayalam (Malayalam)": "ml",
    "Tiếng Marathi (Marathi)": "mr",
    "Tiếng Tamil (Tamil)": "ta",
    "Tiếng Telugu (Telugu)": "te",
    "Tiếng Urdu (Urdu)": "ur",
    "Tiếng Mã Lai (Malay)": "ms",
    "Tiếng Filipino (Filipino)": "fil",
    "Tiếng Catalan (Catalan)": "ca",
    "Tiếng Croatia (Croatian)": "hr",
    "Tiếng Bulgaria (Bulgarian)": "bg",
    "Tiếng Slovenia (Slovenian)": "sl",
    "Tiếng Estonia (Estonian)": "et",
    "Tiếng Latvia (Latvian)": "lv",
    "Tiếng Lithuania (Lithuanian)": "lt",
    "Tiếng Serbia (Serbian)": "sr",
    "Tiếng Swahili (Swahili)": "sw",
    "Tiếng Afrikaans (Afrikaans)": "af",
    "Tiếng Amharic (Amharic)": "am",
    "Tiếng Azerbaijan (Azerbaijani)": "az",
    "Tiếng Basque (Basque)": "eu",
    "Tiếng Bosnia (Bosnian)": "bs",
    "Tiếng Galician (Galician)": "gl",
    "Tiếng Iceland (Icelandic)": "is",
    "Tiếng Georgia (Georgian)": "ka",
    "Tiếng Kazakhstan (Kazakh)": "kk",
    "Tiếng Khmer (Khmer)": "km",
    "Tiếng Lào (Lao)": "lo",
    "Tiếng Macedonia (Macedonian)": "mk",
    "Tiếng Mông Cổ (Mongolian)": "mn",
    "Tiếng Myanmar (Burmese)": "my",
    "Tiếng Nepal (Nepali)": "ne",
    "Tiếng Pashto (Pashto)": "ps",
    "Tiếng Sinhala (Sinhala)": "si",
    "Tiếng Somali (Somali)": "so",
    "Tiếng Sundanese (Sundanese)": "su",
    "Tiếng Uzbek (Uzbek)": "uz",
    "Tiếng Zulu (Zulu)": "zu",
    "Tiếng Ireland (Irish)": "ga",
    "Tiếng Welsh (Welsh)": "cy",
    "Tiếng Malta (Maltese)": "mt",
    "Tiếng Javanese (Javanese)": "jv",
}
EDGE_TTS_LANGUAGES = list(EDGE_TTS_LANGUAGE_MAP.keys())
EDGE_TTS_GENDERS = ["Tất cả", "Male", "Female"]

# =============================================================================
# VN TTS CONFIGURATION (Vietnamese Text-to-Speech)
# =============================================================================

# VN TTS directory path (relative to main.py)
VIENEU_TTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "vntts")

# Model backbone configurations
VIENEU_BACKBONE_CONFIGS = {
    "VN TTS (GPU)": {
        "repo": "pnnbao-ump/VieNeu-TTS",
        "supports_streaming": True,
        "description": "Chất lượng cao nhất, yêu cầu GPU",
        "requires_gpu": True,
        # GPU optimization settings
        "memory_util": 0.5,  # GPU memory utilization (0.3-0.8)
        "enable_prefix_caching": True,  # Speed up repeated generation
        "quant_policy": 0,  # KV cache quantization: 0=off, 4=int4, 8=int8
    },
    "VN TTS Q8 (CPU/GPU)": {
        "repo": "pnnbao-ump/VieNeu-TTS-q8-gguf",
        "supports_streaming": True,
        "description": "Cân bằng chất lượng/tốc độ (CPU/GPU)",
        "requires_gpu": False,
        # GGUF settings
        "n_gpu_layers": -1,  # -1 = all layers on GPU if available
        "flash_attn": True,  # Enable flash attention on GPU
    },
    "VN TTS Q4 (Nhanh)": {
        "repo": "pnnbao-ump/VieNeu-TTS-q4-gguf",
        "supports_streaming": True,
        "description": "Nhanh nhất, nhẹ nhất (CPU tối ưu)",
        "requires_gpu": False,
        # GGUF settings
        "n_gpu_layers": -1,  # -1 = all layers on GPU if available
        "flash_attn": True,  # Enable flash attention on GPU
    },
}

# Codec configurations
VIENEU_CODEC_CONFIGS = {
    "NeuCodec (Standard)": {
        "repo": "neuphonic/neucodec",
        "description": "Codec chuẩn, tốc độ trung bình",
        "use_preencoded": False
    },
    "NeuCodec ONNX (Fast CPU)": {
        "repo": "neuphonic/neucodec-onnx-decoder",
        "description": "Tối ưu cho CPU, cần pre-encoded codes",
        "use_preencoded": True
    },
}

# Pre-configured voice samples
VIENEU_VOICE_SAMPLES = {
    "Vĩnh (nam miền Nam)": {
        "audio": os.path.join(VIENEU_TTS_DIR, "sample", "Vĩnh (nam miền Nam).wav"),
        "text": os.path.join(VIENEU_TTS_DIR, "sample", "Vĩnh (nam miền Nam).txt"),
        "codes": os.path.join(VIENEU_TTS_DIR, "sample", "Vĩnh (nam miền Nam).pt"),
        "gender": "Nam",
        "accent": "Miền Nam"
    },
    "Bình (nam miền Bắc)": {
        "audio": os.path.join(VIENEU_TTS_DIR, "sample", "Bình (nam miền Bắc).wav"),
        "text": os.path.join(VIENEU_TTS_DIR, "sample", "Bình (nam miền Bắc).txt"),
        "codes": os.path.join(VIENEU_TTS_DIR, "sample", "Bình (nam miền Bắc).pt"),
        "gender": "Nam",
        "accent": "Miền Bắc"
    },
    "Ngọc (nữ miền Bắc)": {
        "audio": os.path.join(VIENEU_TTS_DIR, "sample", "Ngọc (nữ miền Bắc).wav"),
        "text": os.path.join(VIENEU_TTS_DIR, "sample", "Ngọc (nữ miền Bắc).txt"),
        "codes": os.path.join(VIENEU_TTS_DIR, "sample", "Ngọc (nữ miền Bắc).pt"),
        "gender": "Nữ",
        "accent": "Miền Bắc"
    },
    "Dung (nữ miền Nam)": {
        "audio": os.path.join(VIENEU_TTS_DIR, "sample", "Dung (nữ miền Nam).wav"),
        "text": os.path.join(VIENEU_TTS_DIR, "sample", "Dung (nữ miền Nam).txt"),
        "codes": os.path.join(VIENEU_TTS_DIR, "sample", "Dung (nữ miền Nam).pt"),
        "gender": "Nữ",
        "accent": "Miền Nam"
    },
    "Tuyên (nam miền Bắc)": {
        "audio": os.path.join(VIENEU_TTS_DIR, "sample", "Tuyên (nam miền Bắc).wav"),
        "text": os.path.join(VIENEU_TTS_DIR, "sample", "Tuyên (nam miền Bắc).txt"),
        "codes": os.path.join(VIENEU_TTS_DIR, "sample", "Tuyên (nam miền Bắc).pt"),
        "gender": "Nam",
        "accent": "Miền Bắc"
    },
    "Nguyên (nam miền Nam)": {
        "audio": os.path.join(VIENEU_TTS_DIR, "sample", "Nguyên (nam miền Nam).wav"),
        "text": os.path.join(VIENEU_TTS_DIR, "sample", "Nguyên (nam miền Nam).txt"),
        "codes": os.path.join(VIENEU_TTS_DIR, "sample", "Nguyên (nam miền Nam).pt"),
        "gender": "Nam",
        "accent": "Miền Nam"
    },
    "Sơn (nam miền Nam)": {
        "audio": os.path.join(VIENEU_TTS_DIR, "sample", "Sơn (nam miền Nam).wav"),
        "text": os.path.join(VIENEU_TTS_DIR, "sample", "Sơn (nam miền Nam).txt"),
        "codes": os.path.join(VIENEU_TTS_DIR, "sample", "Sơn (nam miền Nam).pt"),
        "gender": "Nam",
        "accent": "Miền Nam"
    },
    "Đoan (nữ miền Nam)": {
        "audio": os.path.join(VIENEU_TTS_DIR, "sample", "Đoan (nữ miền Nam).wav"),
        "text": os.path.join(VIENEU_TTS_DIR, "sample", "Đoan (nữ miền Nam).txt"),
        "codes": os.path.join(VIENEU_TTS_DIR, "sample", "Đoan (nữ miền Nam).pt"),
        "gender": "Nữ",
        "accent": "Miền Nam"
    },
    "Ly (nữ miền Bắc)": {
        "audio": os.path.join(VIENEU_TTS_DIR, "sample", "Ly (nữ miền Bắc).wav"),
        "text": os.path.join(VIENEU_TTS_DIR, "sample", "Ly (nữ miền Bắc).txt"),
        "codes": os.path.join(VIENEU_TTS_DIR, "sample", "Ly (nữ miền Bắc).pt"),
        "gender": "Nữ",
        "accent": "Miền Bắc"
    },
}

# GGUF models only support these 4 voices
VIENEU_GGUF_ALLOWED_VOICES = [
    "Vĩnh (nam miền Nam)",
    "Bình (nam miền Bắc)",
    "Ngọc (nữ miền Bắc)",
    "Dung (nữ miền Nam)",
]

# VN TTS default settings
VIENEU_MAX_CHARS_PER_CHUNK = 256
VIENEU_DEFAULT_DEVICE = "Auto"  # Auto, CPU, CUDA
VIENEU_SAMPLE_RATE = 24000

# Enhanced Retry settings
MAX_RETRIES = 5  # Tăng số lần retry
RECOVERY_EXTRA_RETRIES = 1  # Extra retries for recovery mode (missing chunk retry)
BASE_RETRY_DELAY = 2  # Delay cơ bản (giây)
MAX_RETRY_DELAY = 30  # Delay tối đa (giây)
RETRY_JITTER = 0.5  # Random jitter để tránh thundering herd
CAPCUT_RATE_LIMIT_DELAY = 0.5  # Delay giữa các requests để tránh rate limiting

# Text chunking settings
CAPCUT_MAX_CHUNK_SIZE = 450  # Capcut max chars per API call (500 limit with safety margin)
CAPCUT_LONG_TEXT_THRESHOLD = 450  # Threshold to trigger chunking for Capcut (matches CAPCUT_MAX_CHUNK_SIZE)
EDGE_MAX_CHUNK_SIZE = 1000  # Edge TTS max chars per chunk
EDGE_LONG_TEXT_THRESHOLD = 1000  # Threshold to trigger chunking for Edge TTS
GEMINI_DEFAULT_CHUNK_SIZE = 300  # Default chunk size for Gemini TTS file processing
MIN_CHUNK_RATIO = 0.5  # Minimum chunk size ratio before force breaking
PUNCTUATION_SEARCH_WINDOW = 100  # Characters to search backwards for punctuation
MIN_CHUNK_RATIO_V2 = 0.25  # For v2 mode: minimum chunk ratio before forcing break

# Punctuation marks for "Ngắt dòng v2" mode - used to find break points
# Note: Dash '-' is included for breaking but NOT removed (keeps compound words readable)
SENTENCE_BREAK_PUNCTUATION = ['.', '!', '?', ',', '-', ';', ':', '。', '！', '？', '，', '；', '：']
# Punctuation marks to remove before sending to API (for v2 mode)
# Note: Dash '-' is NOT removed to preserve compound words and hyphenated terms
PUNCTUATION_TO_REMOVE = ['.', '!', '?', ',', ';', ':', '。', '！', '？', '，', '；', '：']
FFMPEG_TIMEOUT_SECONDS = 300  # FFmpeg merge timeout

# Connection error patterns - lỗi cần retry nhiều hơn
CONNECTION_ERROR_PATTERNS = [
    "no audio",
    "0 bytes",
    "connection",
    "timeout",
    "reset",
    "refused",
    "unavailable",
    "overloaded",
    "rate limit",
    "quota",
    "503",
    "502",
    "500",
    "429",
]

# Audio file validation
MIN_AUDIO_FILE_SIZE = 100  # Minimum bytes for a valid audio file

# Error message display
ERROR_MSG_MAX_LENGTH = 50  # Maximum characters to display in error messages


# =============================================================================
# PATH UTILITIES
# =============================================================================

def get_app_dir() -> str:
    """
    Lấy thư mục gốc của app.
    - Nếu chạy từ exe (PyInstaller): trả về thư mục chứa file exe
    - Nếu chạy từ script: trả về thư mục chứa script
    
    Lưu ý: Không dùng sys._MEIPASS vì đó là thư mục tạm khi giải nén exe
    """
    if getattr(sys, 'frozen', False):
        # Đang chạy từ exe được build bởi PyInstaller
        # sys.executable = đường dẫn đến file .exe
        return os.path.dirname(sys.executable)
    else:
        # Đang chạy từ script Python
        return os.path.dirname(os.path.abspath(__file__))


def get_default_ffmpeg_path() -> str:
    """
    Lấy đường dẫn mặc định của ffmpeg.
    Ưu tiên: thư mục app > system PATH
    """
    app_dir = get_app_dir()
    
    # Kiểm tra ffmpeg trong thư mục app
    if sys.platform == "win32":
        local_ffmpeg = os.path.join(app_dir, "ffmpeg.exe")
    else:
        local_ffmpeg = os.path.join(app_dir, "ffmpeg")
    
    if os.path.exists(local_ffmpeg):
        return local_ffmpeg
    
    # Fallback: dùng ffmpeg từ system PATH
    return "ffmpeg.exe" if sys.platform == "win32" else "ffmpeg"


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class Subtitle:
    index: int
    start_time: str
    end_time: str
    text: str


@dataclass
class TTSConfig:
    voice: str = "Kore"
    media_resolution: str = "MEDIA_RESOLUTION_MEDIUM"
    thinking_mode: bool = False
    thinking_budget: int = 1024
    affective_dialog: bool = False
    proactive_audio: bool = False
    system_instruction: str = DEFAULT_SYSTEM_INSTRUCTION
    speed: float = 1.2
    # Multi-worker settings
    multi_worker_enabled: bool = False
    workers_per_key: int = 2
    # Live session mode - phiên làm việc liên tục như cuộc gọi điện thoại
    live_session_enabled: bool = False
    # Keep voice beta mode - wrap text in {content} for Gemini to maintain consistent voice
    keep_voice_beta: bool = False


@dataclass 
class GeneratedAudio:
    index: int
    file_path: str
    text: str
    duration_ms: float


@dataclass
class TextChunk:
    """Chunk of text for long text TTS"""
    index: int
    text: str
    original_length: int


# =============================================================================
# PARSERS & UTILS
# =============================================================================

def parse_srt(content: str) -> List[Subtitle]:
    subtitles = []
    blocks = re.split(r'\n\s*\n', content.strip())
    for block in blocks:
        lines = block.strip().split('\n')
        if len(lines) >= 3:
            try:
                index = int(lines[0].strip())
                time_match = re.match(
                    r'(\d{2}:\d{2}:\d{2},\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2},\d{3})',
                    lines[1].strip()
                )
                if time_match:
                    text = '\n'.join(lines[2:]).strip()
                    text = re.sub(r'<[^>]+>', '', text)
                    if text:
                        subtitles.append(Subtitle(index, time_match.group(1), time_match.group(2), text))
            except:
                continue
    return subtitles


def parse_txt(content: str) -> List[Subtitle]:
    return [Subtitle(i, "", "", line.strip()) 
            for i, line in enumerate(content.strip().split('\n'), 1) if line.strip()]


def parse_vtt(content: str) -> List[Subtitle]:
    """Parse VTT (WebVTT) subtitle format"""
    subtitles = []
    
    # Remove WEBVTT header and metadata
    lines = content.strip().split('\n')
    
    # Find start of cues (skip header)
    start_idx = 0
    for i, line in enumerate(lines):
        if line.strip() == 'WEBVTT' or line.startswith('NOTE') or line.startswith('STYLE'):
            continue
        if '-->' in line:
            start_idx = i - 1 if i > 0 and lines[i-1].strip().isdigit() else i
            break
        if line.strip() == '':
            start_idx = i + 1
    
    # Parse cues
    content_from_cues = '\n'.join(lines[start_idx:])
    blocks = re.split(r'\n\s*\n', content_from_cues.strip())
    
    index = 1
    for block in blocks:
        block_lines = block.strip().split('\n')
        if not block_lines:
            continue
        
        # Check if first line is index number
        time_line_idx = 0
        if block_lines[0].strip().isdigit():
            time_line_idx = 1
        
        if len(block_lines) > time_line_idx:
            # VTT uses . for milliseconds, SRT uses ,
            time_match = re.match(
                r'(\d{2}:\d{2}:\d{2}[.,]\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2}[.,]\d{3})',
                block_lines[time_line_idx].strip()
            )
            if time_match:
                start_time = time_match.group(1).replace('.', ',')
                end_time = time_match.group(2).replace('.', ',')
                text = '\n'.join(block_lines[time_line_idx + 1:]).strip()
                # Remove VTT tags like <c>, </c>, <v Speaker>, etc.
                text = re.sub(r'<[^>]+>', '', text)
                if text:
                    subtitles.append(Subtitle(index, start_time, end_time, text))
                    index += 1
    
    return subtitles


def parse_subtitle_file(file_path: str) -> List[Subtitle]:
    """Parse subtitle file (SRT, VTT, or TXT) and return list of subtitles"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    ext = os.path.splitext(file_path)[1].lower()
    
    if ext == '.vtt':
        return parse_vtt(content)
    elif ext == '.srt':
        return parse_srt(content)
    else:
        return parse_txt(content)


def save_wave_file(filename: str, pcm_data: bytes, rate: int = RECEIVE_SAMPLE_RATE):
    with wave.open(filename, "wb") as wf:
        wf.setnchannels(AUDIO_CHANNELS)
        wf.setsampwidth(AUDIO_SAMPLE_WIDTH)
        wf.setframerate(rate)
        wf.writeframes(pcm_data)


def split_text_into_chunks(text: str, chunk_size: int = 500) -> List[TextChunk]:
    """
    Split text into chunks of approximately chunk_size characters.
    Tries to split at sentence boundaries when possible.
    Removes extra whitespace and newlines.
    """
    # Clean text: remove extra whitespace and newlines
    cleaned_text = ' '.join(text.split())
    
    if not cleaned_text:
        return []
    
    chunks = []
    current_pos = 0
    chunk_index = 1
    
    while current_pos < len(cleaned_text):
        # Get the next chunk_size characters
        end_pos = min(current_pos + chunk_size, len(cleaned_text))
        
        # If not at the end, try to find a good breaking point
        if end_pos < len(cleaned_text):
            # Look for sentence endings (. ! ?) within the last 20% of the chunk
            search_start = current_pos + int(chunk_size * 0.8)
            chunk_text = cleaned_text[current_pos:end_pos]
            
            # Find the last sentence ending
            best_break = -1
            for i in range(len(chunk_text) - 1, int(len(chunk_text) * 0.8) - 1, -1):
                if chunk_text[i] in '.!?。！？' and (i + 1 >= len(chunk_text) or chunk_text[i + 1] == ' '):
                    best_break = i + 1
                    break
            
            # If no sentence break found, try comma or space
            if best_break == -1:
                for i in range(len(chunk_text) - 1, int(len(chunk_text) * 0.8) - 1, -1):
                    if chunk_text[i] in ',，;；':
                        best_break = i + 1
                        break
            
            # If still no break found, use space
            if best_break == -1:
                for i in range(len(chunk_text) - 1, int(len(chunk_text) * 0.5) - 1, -1):
                    if chunk_text[i] == ' ':
                        best_break = i + 1
                        break
            
            if best_break != -1:
                end_pos = current_pos + best_break
        
        chunk_content = cleaned_text[current_pos:end_pos].strip()
        if chunk_content:
            chunks.append(TextChunk(
                index=chunk_index,
                text=chunk_content,
                original_length=len(chunk_content)
            ))
            chunk_index += 1
        
        current_pos = end_pos
    
    return chunks


def split_text_smart(text: str, max_chars: int = 450, include_spaces: bool = True) -> List[TextChunk]:
    """
    Smart text splitting for Capcut/Edge TTS.
    
    Logic:
    - Split at safe points: ! , . - or complete words
    - Does not cut in the middle of words
    - max_chars includes spaces if include_spaces=True
    
    Args:
        text: Input text
        max_chars: Maximum characters per chunk (default 450 for Capcut)
        include_spaces: Count spaces in character count
    
    Returns:
        List of TextChunk objects
    """
    # Clean text: normalize whitespace
    cleaned_text = ' '.join(text.split())
    
    if not cleaned_text:
        return []
    
    chunks = []
    current_pos = 0
    chunk_index = 1
    
    # Safe break characters (priority order)
    punctuation_breaks = ['!', '.', ',', '-', '?', ';', ':']
    
    while current_pos < len(cleaned_text):
        remaining = len(cleaned_text) - current_pos
        
        if remaining <= max_chars:
            # Last chunk
            chunk_content = cleaned_text[current_pos:].strip()
            if chunk_content:
                chunks.append(TextChunk(
                    index=chunk_index,
                    text=chunk_content,
                    original_length=len(chunk_content)
                ))
            break
        
        # Find the best break point within max_chars
        chunk_text = cleaned_text[current_pos:current_pos + max_chars]
        best_break = -1
        
        # Priority 1: Find punctuation break (! . , -)
        for punct in punctuation_breaks:
            # Search from end backwards within the search window
            search_start = max(0, len(chunk_text) - PUNCTUATION_SEARCH_WINDOW)
            for i in range(len(chunk_text) - 1, search_start, -1):
                if chunk_text[i] == punct:
                    # Check if next char is space or end
                    if i + 1 >= len(chunk_text) or chunk_text[i + 1] == ' ':
                        best_break = i + 1
                        break
            if best_break != -1:
                break
        
        # Priority 2: If no punctuation found, find last space (complete word)
        if best_break == -1:
            for i in range(len(chunk_text) - 1, 0, -1):
                if chunk_text[i] == ' ':
                    best_break = i
                    break
        
        # Priority 3: Force break at max_chars (should rarely happen)
        if best_break == -1 or best_break < max_chars * MIN_CHUNK_RATIO:
            best_break = max_chars
        
        chunk_content = cleaned_text[current_pos:current_pos + best_break].strip()
        if chunk_content:
            chunks.append(TextChunk(
                index=chunk_index,
                text=chunk_content,
                original_length=len(chunk_content)
            ))
            chunk_index += 1
        
        current_pos = current_pos + best_break
        # Skip leading spaces
        while current_pos < len(cleaned_text) and cleaned_text[current_pos] == ' ':
            current_pos += 1
    
    return chunks


def clean_text_for_tts(text: str) -> str:
    """
    Clean text for TTS by removing extra whitespace and newlines.
    Returns a single-line text with normalized spaces.
    """
    # Replace newlines with spaces
    text = text.replace('\n', ' ').replace('\r', ' ')
    # Normalize multiple spaces to single space
    cleaned = ' '.join(text.split())
    return cleaned


def remove_trailing_punctuation(text: str) -> str:
    """
    Remove trailing punctuation from text for v2 mode.
    Only removes punctuation at the end of the text.
    """
    text = text.strip()
    while text and text[-1] in PUNCTUATION_TO_REMOVE:
        text = text[:-1].strip()
    return text


def split_text_by_punctuation_v2(text: str, target_chunk_size: int = 300, remove_punct: bool = True) -> List[TextChunk]:
    """
    Split text by punctuation marks (Ngắt dòng v2).
    
    This mode prioritizes breaking at punctuation marks (., !, ?, ,, -, etc.)
    within the target chunk size range. If no punctuation is found within range,
    it will allow chunk size violations to preserve sentence integrity.
    
    Args:
        text: Input text
        target_chunk_size: Target maximum characters per chunk (default 300)
        remove_punct: If True, removes trailing punctuation from each chunk
    
    Returns:
        List of TextChunk objects
    """
    # Clean text: normalize whitespace
    cleaned_text = clean_text_for_tts(text)
    
    if not cleaned_text:
        return []
    
    chunks = []
    current_pos = 0
    chunk_index = 1
    
    while current_pos < len(cleaned_text):
        remaining = len(cleaned_text) - current_pos
        
        if remaining <= target_chunk_size:
            # Last chunk - take everything remaining
            chunk_content = cleaned_text[current_pos:].strip()
            if remove_punct:
                chunk_content = remove_trailing_punctuation(chunk_content)
            if chunk_content:
                chunks.append(TextChunk(
                    index=chunk_index,
                    text=chunk_content,
                    original_length=len(chunk_content)
                ))
            break
        
        # Look for punctuation within target range
        search_end = min(current_pos + target_chunk_size, len(cleaned_text))
        chunk_text = cleaned_text[current_pos:search_end]
        
        best_break = -1
        
        # Priority 1: Find sentence-ending punctuation (. ! ?) within target range
        sentence_enders = ['.', '!', '?', '。', '！', '？']
        for i in range(len(chunk_text) - 1, -1, -1):
            if chunk_text[i] in sentence_enders:
                best_break = i + 1
                break
        
        # Priority 2: If no sentence ender found, look for comma or dash
        if best_break == -1:
            secondary_breaks = [',', '-', ';', ':', '，', '；', '：']
            for i in range(len(chunk_text) - 1, -1, -1):
                if chunk_text[i] in secondary_breaks:
                    best_break = i + 1
                    break
        
        # Priority 3: If no punctuation found in target range, extend search beyond target
        # to find the next punctuation mark. This allows chunk size to exceed target (up to 2x)
        # to preserve sentence integrity. This is intentional for v2 mode.
        if best_break == -1:
            # Search forward from target position - may result in chunks up to 2x target size
            extended_search_start = current_pos + target_chunk_size
            extended_search_end = min(extended_search_start + target_chunk_size, len(cleaned_text))
            extended_text = cleaned_text[extended_search_start:extended_search_end]
            
            for i, char in enumerate(extended_text):
                if char in SENTENCE_BREAK_PUNCTUATION:
                    best_break = target_chunk_size + i + 1
                    break
            
            # If still no punctuation found, use space as fallback
            if best_break == -1:
                # Look for last space within reasonable range
                combined_text = cleaned_text[current_pos:extended_search_end]
                for i in range(len(combined_text) - 1, target_chunk_size // 2, -1):
                    if combined_text[i] == ' ':
                        best_break = i + 1
                        break
        
        # Priority 4: Force break at target size if nothing else works
        # Use MIN_CHUNK_RATIO_V2 (25%) as minimum - very short chunks usually indicate
        # parsing issues and should force a clean break at target size instead
        if best_break == -1 or best_break < int(target_chunk_size * MIN_CHUNK_RATIO_V2):
            best_break = target_chunk_size
        
        chunk_content = cleaned_text[current_pos:current_pos + best_break].strip()
        if remove_punct:
            chunk_content = remove_trailing_punctuation(chunk_content)
        
        if chunk_content:
            chunks.append(TextChunk(
                index=chunk_index,
                text=chunk_content,
                original_length=len(chunk_content)
            ))
            chunk_index += 1
        
        current_pos = current_pos + best_break
        # Skip leading spaces
        while current_pos < len(cleaned_text) and cleaned_text[current_pos] == ' ':
            current_pos += 1
    
    return chunks


def merge_mp3_files_ffmpeg(input_files: List[str], output_file: str, ffmpeg_path: str = "ffmpeg.exe") -> bool:
    """
    Merge multiple MP3 files into one using ffmpeg.
    Returns True if successful, False otherwise.
    """
    if not input_files:
        return False
    
    # Sort files by index (assuming format: chunk_0001.mp3)
    input_files_sorted = sorted(input_files)
    
    try:
        # Convert all paths to absolute paths
        input_files_abs = [os.path.abspath(f) for f in input_files_sorted]
        output_file_abs = os.path.abspath(output_file)
        
        # Create a file list for ffmpeg concat in the same directory as output
        list_file = output_file_abs + ".txt"
        with open(list_file, "w", encoding="utf-8") as f:
            for file in input_files_abs:
                # Use forward slashes for FFmpeg compatibility
                safe_path = file.replace("\\", "/")
                f.write(f"file '{safe_path}'\n")
        
        # Run ffmpeg to concatenate
        cmd = [
            ffmpeg_path,
            "-y",  # Overwrite output
            "-f", "concat",
            "-safe", "0",
            "-i", list_file,
            "-c", "copy",
            output_file_abs
        ]
        
        print(f"FFmpeg command: {' '.join(cmd)}")
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=FFMPEG_TIMEOUT_SECONDS
        )
        
        # Clean up list file
        if os.path.exists(list_file):
            os.remove(list_file)
        
        if result.returncode != 0:
            print(f"FFmpeg stderr: {result.stderr}")
            print(f"FFmpeg stdout: {result.stdout}")
            return False
        
        return True
        
    except FileNotFoundError:
        print(f"FFmpeg not found at: {ffmpeg_path}")
        return False
    except subprocess.TimeoutExpired:
        print("FFmpeg timed out")
        return False
    except Exception as e:
        print(f"Error merging files: {e}")
        import traceback
        traceback.print_exc()
        return False


def read_document_file(file_path: str) -> str:
    """
    Read content from txt, doc, or docx files.
    Returns the text content.
    """
    ext = os.path.splitext(file_path)[1].lower()
    
    if ext == '.txt':
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    elif ext in ['.doc', '.docx']:
        try:
            # Try to use python-docx for docx files
            from docx import Document
            doc = Document(file_path)
            return '\n'.join([para.text for para in doc.paragraphs])
        except ImportError:
            raise ImportError("python-docx library is required to read .docx files. Install with: pip install python-docx")
        except Exception as e:
            raise Exception(f"Error reading docx file: {e}")
    else:
        raise ValueError(f"Unsupported file format: {ext}")


def merge_wav_files_ffmpeg(input_files: List[str], output_file: str, ffmpeg_path: str = "ffmpeg.exe") -> bool:
    """
    Merge multiple WAV files into one using ffmpeg.
    Returns True if successful, False otherwise.
    """
    if not input_files:
        return False
    
    # Sort files by index (assuming format: chunk_0001.wav)
    input_files_sorted = sorted(input_files)
    
    try:
        # Convert all paths to absolute paths
        input_files_abs = [os.path.abspath(f) for f in input_files_sorted]
        output_file_abs = os.path.abspath(output_file)
        
        # Create a file list for ffmpeg concat in the same directory as output
        list_file = output_file_abs + ".txt"
        with open(list_file, "w", encoding="utf-8") as f:
            for file in input_files_abs:
                # Use forward slashes for FFmpeg compatibility
                safe_path = file.replace("\\", "/")
                f.write(f"file '{safe_path}'\n")
        
        # Run ffmpeg to concatenate
        cmd = [
            ffmpeg_path,
            "-y",  # Overwrite output
            "-f", "concat",
            "-safe", "0",
            "-i", list_file,
            "-c", "copy",
            output_file_abs
        ]
        
        print(f"FFmpeg command: {' '.join(cmd)}")
        print(f"List file content:")
        with open(list_file, "r") as f:
            print(f.read())
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )
        
        # Clean up list file
        if os.path.exists(list_file):
            os.remove(list_file)
        
        if result.returncode != 0:
            print(f"FFmpeg stderr: {result.stderr}")
            print(f"FFmpeg stdout: {result.stdout}")
            return False
        
        return True
        
    except FileNotFoundError:
        print(f"FFmpeg not found at: {ffmpeg_path}")
        return False
    except subprocess.TimeoutExpired:
        print("FFmpeg timed out")
        return False
    except Exception as e:
        print(f"Error merging files: {e}")
        import traceback
        traceback.print_exc()
        return False


def is_connection_error(error_str: str) -> bool:
    """Check if error is likely a connection/temporary issue that warrants more retries"""
    error_lower = error_str.lower()
    return any(pattern in error_lower for pattern in CONNECTION_ERROR_PATTERNS)


def cleanup_event_loop(loop: asyncio.AbstractEventLoop) -> None:
    """
    Properly cleanup an asyncio event loop to prevent CPU/memory leaks.
    
    This is critical for Edge TTS workers that create new event loops per request.
    Without proper cleanup, orphaned threads can cause CPU spikes.
    
    Args:
        loop: The asyncio event loop to cleanup
    """
    if loop is None:
        return
    
    try:
        # Cancel all pending tasks
        pending = asyncio.all_tasks(loop)
        for task in pending:
            task.cancel()
        # Run until all tasks are cancelled
        if pending:
            loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
    except Exception:
        pass
    finally:
        try:
            loop.run_until_complete(loop.shutdown_asyncgens())
        except Exception:
            pass
        loop.close()
        asyncio.set_event_loop(None)


# =============================================================================
# CAPCUT VOICE TTS FUNCTIONS
# =============================================================================

def capcut_prepare_text(text: str) -> str:
    """
    Prepare text for Capcut TTS API
    
    QUAN TRỌNG: API TikTok/CapCut yêu cầu định dạng application/x-www-form-urlencoded
    trong đó SPACE phải được encode thành '+', KHÔNG phải '%20'.
    
    Thứ tự thay thế khớp với code C# trong CapCutTtsService.cs:
    1) + → " cộng " (vì + là ký tự đặc biệt trong URL)
    2) space → "+"
    3) & → " và " (vì & là ký tự đặc biệt trong URL)
    """
    # 1) Thay thế + trước (vì bước 2 sẽ thêm nhiều dấu + mới)
    text = text.replace('+', ' cộng ')
    # 2) QUAN TRỌNG: Space -> "+" (KHÔNG dùng %20)
    text = text.replace(' ', '+')
    # 3) Thay thế & thành " và "
    text = text.replace('&', '+và+')
    return text



def capcut_create_tts(text: str, voice_id: str, session_id: str, output_file: str, retries: int = 3, debug: bool = True) -> tuple:
    """
    Create TTS audio using Capcut/TikTok API
    Returns (success: bool, error_info: dict or None)
    """
    if debug:
        print(f"[DEBUG Capcut TTS] Starting TTS request...")
        print(f"[DEBUG Capcut TTS] Voice ID: {voice_id}")
        # Mask session ID for security - only show length and first 4 chars
        masked_session = f"{session_id[:4]}****({len(session_id)} chars)" if len(session_id) > 4 else "****"
        print(f"[DEBUG Capcut TTS] Session ID: {masked_session}")
        print(f"[DEBUG Capcut TTS] Text length: {len(text)} chars")
        print(f"[DEBUG Capcut TTS] Output file: {output_file}")
    
    if not session_id:
        if debug:
            print("[DEBUG Capcut TTS] ERROR: Session ID is empty!")
        return (False, {"error": "Session ID không được để trống"})
    
    stripped_text = text.strip()
    if not stripped_text or not re.search(r'[a-zA-Z0-9À-ỹ]', stripped_text):
        if debug:
            print(f"[DEBUG Capcut TTS] ERROR: Text is empty or invalid: '{stripped_text[:50]}'")
        return (False, {"error": "Text trống hoặc không hợp lệ"})
    
    req_text = capcut_prepare_text(text)
    url = f'{CAPCUT_TTS_URL}/?text_speaker={voice_id}&req_text={req_text}&speaker_map_type=0&aid=1233'
    headers = {
        'User-Agent': 'com.zhiliaoapp.musically/2022600030 (Linux; U; Android 7.1.2; es_ES; SM-G988N; Build/NRD90M;tt-ok/3.12.13.1)',
        'Cookie': f'sessionid={session_id}',
        'Accept-Encoding': 'gzip,deflate,compress'
    }
    
    if debug:
        print(f"[DEBUG Capcut TTS] Request URL: {url[:100]}...")
        print(f"[DEBUG Capcut TTS] Headers Cookie: sessionid=****")
    
    for attempt in range(retries):
        try:
            if debug:
                print(f"[DEBUG Capcut TTS] Attempt {attempt + 1}/{retries}...")
            
            response = requests.post(url, headers=headers, timeout=10)
            
            if debug:
                print(f"[DEBUG Capcut TTS] HTTP Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                status_code = data.get('status_code')
                status_msg = data.get('status_msg', 'No message')
                
                if debug:
                    print(f"[DEBUG Capcut TTS] API status_code: {status_code}")
                    print(f"[DEBUG Capcut TTS] API status_msg: {status_msg}")
                    print(f"[DEBUG Capcut TTS] Response keys: {list(data.keys())}")
                
                if status_code == 1:
                    if debug:
                        print("[DEBUG Capcut TTS] ERROR: Invalid or expired session ID")
                    return (False, {"error": f"Session ID không hợp lệ hoặc hết hạn (status_code: {status_code}, msg: {status_msg})"})
                elif status_code == 2:
                    if debug:
                        print("[DEBUG Capcut TTS] ERROR: Text too long")
                    return (False, {"error": "Text quá dài"})
                elif status_code == 4:
                    if debug:
                        print("[DEBUG Capcut TTS] ERROR: Invalid voice ID")
                    return (False, {"error": "Voice ID không hợp lệ"})
                elif status_code == 5:
                    if debug:
                        print("[DEBUG Capcut TTS] ERROR: Missing session ID in request")
                    return (False, {"error": "Thiếu Session ID"})
                elif status_code != 0:
                    if debug:
                        print(f"[DEBUG Capcut TTS] ERROR: Unknown error code: {status_code}")
                    return (False, {"error": f"Lỗi không xác định: {status_code}, msg: {status_msg}"})
                
                encoded_voice = data.get('data', {}).get('v_str')
                if encoded_voice:
                    if debug:
                        print(f"[DEBUG Capcut TTS] SUCCESS: Got audio data, length: {len(encoded_voice)} chars")
                    
                    # Create output directory if needed
                    output_dir = os.path.dirname(output_file)
                    if output_dir:
                        os.makedirs(output_dir, exist_ok=True)
                    
                    with open(output_file, 'wb') as f:
                        f.write(base64.b64decode(encoded_voice))
                    
                    if debug:
                        file_size = os.path.getsize(output_file) if os.path.exists(output_file) else 0
                        print(f"[DEBUG Capcut TTS] File saved: {output_file}, size: {file_size} bytes")
                    
                    return (True, None)
                else:
                    if debug:
                        print("[DEBUG Capcut TTS] ERROR: No audio data in response")
                        print(f"[DEBUG Capcut TTS] Response data keys: {list(data.get('data', {}).keys()) if data.get('data') else 'No data'}")
                    return (False, {"error": "Không nhận được audio data"})
            else:
                if debug:
                    print(f"[DEBUG Capcut TTS] HTTP Error: {response.status_code}")
                    try:
                        print(f"[DEBUG Capcut TTS] Response body: {response.text[:200]}")
                    except:
                        pass
                if attempt < retries - 1:
                    time.sleep(1)
                    continue
                return (False, {"error": f"HTTP Error: {response.status_code}"})
        except Exception as e:
            if debug:
                print(f"[DEBUG Capcut TTS] Exception: {type(e).__name__}: {str(e)}")
            if attempt < retries - 1:
                time.sleep(1)
                continue
            return (False, {"error": str(e)})
    
    return (False, {"error": "Đã hết số lần thử"})


# =============================================================================
# EDGE TTS FUNCTIONS
# =============================================================================

def fetch_edge_voices() -> List[Dict[str, Any]]:
    """Fetch voice list from Edge TTS API"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36 Edg/143.0.0.0',
            'Accept': '*/*',
        }
        response = requests.get(EDGE_TTS_VOICE_URL, headers=headers, timeout=10)
        if response.status_code == 200:
            voices = response.json()
            # Process voices to add language field
            for voice in voices:
                locale = voice.get('Locale', '')
                voice['Language'] = locale.split('-')[0] if locale else ''
            return voices
        return []
    except Exception as e:
        print(f"Error fetching Edge voices: {e}")
        return []


def calculate_retry_delay(attempt: int, is_conn_error: bool = False) -> float:
    """
    Calculate retry delay with exponential backoff and jitter.
    Connection errors get longer delays to allow recovery.
    """
    # Exponential backoff: 2^attempt * base_delay
    delay = min(BASE_RETRY_DELAY * (2 ** (attempt - 1)), MAX_RETRY_DELAY)
    
    # Add extra delay for connection errors
    if is_conn_error:
        delay = min(delay * 1.5, MAX_RETRY_DELAY)
    
    # Add random jitter to prevent thundering herd
    jitter = delay * RETRY_JITTER * random.random()
    
    return delay + jitter


# =============================================================================
# AUDIO PLAYER
# =============================================================================

class AudioPlayer:
    """Audio player for WAV and MP3 files"""
    
    def __init__(self):
        self.is_playing = False
        self.should_stop = False
        self.current_file = None
        self.play_thread = None
        self._temp_wav_file = None  # Temp file for MP3->WAV conversion
        
        if HAS_PYAUDIO:
            self.pya = pyaudio.PyAudio()
        else:
            self.pya = None
    
    def _convert_mp3_to_wav(self, mp3_path: str) -> Optional[str]:
        """Convert MP3 to WAV using FFmpeg for playback"""
        try:
            # Create temp WAV file using os.path.splitext for safe extension handling
            base_path, ext = os.path.splitext(mp3_path)
            temp_wav = base_path + '_temp_play.wav'
            wav_version = base_path + '.wav'
            if os.path.exists(wav_version):
                # If WAV version already exists, use it
                return wav_version
            
            # Use FFmpeg to convert
            ffmpeg_path = get_default_ffmpeg_path()
            cmd = [
                ffmpeg_path,
                "-y",  # Overwrite output
                "-i", mp3_path,
                "-acodec", "pcm_s16le",
                "-ar", "24000",
                "-ac", "1",
                temp_wav
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0 and os.path.exists(temp_wav):
                self._temp_wav_file = temp_wav
                return temp_wav
            else:
                print(f"FFmpeg conversion failed: {result.stderr}")
                return None
        except (FileNotFoundError, OSError) as e:
            print(f"FFmpeg not found or OS error: {e}")
            return None
        except subprocess.TimeoutExpired:
            print("FFmpeg conversion timed out")
            return None
        except Exception as e:
            print(f"Error converting MP3 to WAV: {e}")
            return None
    
    def play(self, file_path: str, on_complete=None):
        """Play a WAV or MP3 file"""
        if not HAS_PYAUDIO:
            print("PyAudio not available - cannot play audio")
            return
        
        self.stop()
        self.should_stop = False
        self.current_file = file_path
        
        def _play():
            try:
                self.is_playing = True
                
                # Check file extension
                play_file = file_path
                if file_path.lower().endswith('.mp3'):
                    # Convert MP3 to WAV first
                    converted = self._convert_mp3_to_wav(file_path)
                    if converted:
                        play_file = converted
                    else:
                        print(f"Cannot convert MP3 file: {file_path}")
                        return
                
                # Play the WAV file
                wf = wave.open(play_file, 'rb')
                
                stream = self.pya.open(
                    format=self.pya.get_format_from_width(wf.getsampwidth()),
                    channels=wf.getnchannels(),
                    rate=wf.getframerate(),
                    output=True
                )
                
                chunk_size = 1024
                data = wf.readframes(chunk_size)
                
                while data and not self.should_stop:
                    stream.write(data)
                    data = wf.readframes(chunk_size)
                
                stream.stop_stream()
                stream.close()
                wf.close()
                
            except Exception as e:
                print(f"Play error: {e}")
                import traceback
                traceback.print_exc()
            finally:
                self.is_playing = False
                # Cleanup temp file
                if self._temp_wav_file and os.path.exists(self._temp_wav_file):
                    try:
                        os.remove(self._temp_wav_file)
                    except (OSError, IOError):
                        pass
                    self._temp_wav_file = None
                if on_complete and not self.should_stop:
                    on_complete()
        
        self.play_thread = threading.Thread(target=_play, daemon=True)
        self.play_thread.start()
    
    def stop(self):
        """Stop playback"""
        self.should_stop = True
        if self.play_thread and self.play_thread.is_alive():
            self.play_thread.join(timeout=1)
        self.is_playing = False
    
    def cleanup(self):
        """Cleanup resources"""
        self.stop()
        if self._temp_wav_file and os.path.exists(self._temp_wav_file):
            try:
                os.remove(self._temp_wav_file)
            except (OSError, IOError):
                pass
        if self.pya:
            self.pya.terminate()


# =============================================================================
# TRUE PERSISTENT TTS SESSION - FIXED IMPLEMENTATION  
# =============================================================================
# Khác với implementation cũ (tạo session mới cho mỗi request),
# class này giữ MỘT WebSocket session mở và gửi nhiều requests qua session đó.
# Giống như cách Google AI Studio hoạt động - kết nối một lần và giữ mở.
# =============================================================================

class TruePersistentSession:
    """
    TRUE Persistent TTS Session - Giữ một kết nối WebSocket DUY NHẤT.
    
    Cách hoạt động (ĐÚNG như AI Studio):
    1. connect() - Mở WebSocket và bắt đầu background task
    2. generate_audio(text) - Gửi text và đợi nhận audio (qua CÙNG session)
    3. disconnect() - Đóng session khi hoàn tất
    
    Session sẽ tự động reconnect nếu bị timeout (~10 phút).
    """
    
    def __init__(self, api_key: str, config: TTSConfig, log_callback=None):
        self.api_key = api_key
        self.config = config
        self.log = log_callback or print
        
        # Client và session
        self.client = None
        self.session = None
        self._live_config = None
        
        # State
        self.is_connected = False
        self._running = False
        
        # Queues for communication with session task
        self._request_queue = None
        self._request_lock = None
        self._session_task = None
        
    def _setup_client(self, api_version: str = "v1beta"):
        """Setup Google GenAI client"""
        self.client = genai.Client(
            http_options={"api_version": api_version},
            api_key=self.api_key,
        )
    
    def _build_config(self) -> types.LiveConnectConfig:
        """Build LiveConnectConfig cho TTS"""
        cfg = {
            "response_modalities": ["AUDIO"],
            "speech_config": types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                        voice_name=self.config.voice
                    )
                )
            ),
            # Context window compression để hỗ trợ sessions dài hơn
            "context_window_compression": types.ContextWindowCompressionConfig(
                trigger_tokens=25600,
                sliding_window=types.SlidingWindow(target_tokens=12800),
            ),
        }
        
        if self.config.system_instruction:
            cfg["system_instruction"] = self.config.system_instruction
        
        if self.config.thinking_mode:
            cfg["thinking_config"] = types.ThinkingConfig(
                thinking_budget=self.config.thinking_budget,
                include_thoughts=True
            )
            
        if self.config.affective_dialog:
            cfg["enable_affective_dialog"] = True
            
        if self.config.proactive_audio:
            cfg["proactivity"] = {"proactive_audio": True}
        
        return types.LiveConnectConfig(**cfg)
    
    async def connect(self) -> bool:
        """Kết nối và bắt đầu persistent session"""
        if self.is_connected:
            self.log("⚠️ Session đã được kết nối", "WARNING")
            return True
        
        try:
            api_version = "v1alpha" if (self.config.affective_dialog or 
                                        self.config.proactive_audio) else "v1beta"
            
            self._setup_client(api_version)
            self._live_config = self._build_config()
            
            self._request_queue = asyncio.Queue()
            self._request_lock = asyncio.Lock()
            
            self.log(f"🔗 Đang kết nối Persistent Session...", "INFO")
            self.log(f"🎭 Voice: {self.config.voice}", "INFO")
            
            self._running = True
            self._session_task = asyncio.create_task(self._session_manager())
            
            # Wait for connection to establish
            for _ in range(20):  # Wait up to 10 seconds
                await asyncio.sleep(0.5)
                if self.is_connected:
                    self.log(f"✅ Persistent Session đã kết nối!", "SUCCESS")
                    return True
            
            self.log(f"❌ Timeout khi kết nối session", "ERROR")
            return False
                
        except Exception as e:
            self.log(f"❌ Lỗi kết nối: {str(e)}", "ERROR")
            self.is_connected = False
            return False
    
    async def _session_manager(self):
        """Background task giữ session mở và xử lý requests"""
        reconnect_delay = 1.0
        
        while self._running:
            try:
                self.log(f"📡 Mở WebSocket connection...", "INFO")
                
                async with self.client.aio.live.connect(
                    model=MODEL,
                    config=self._live_config
                ) as session:
                    self.session = session
                    self.is_connected = True
                    reconnect_delay = 1.0  # Reset on success
                    
                    self.log(f"✅ WebSocket đã kết nối, sẵn sàng nhận requests", "SUCCESS")
                    
                    # Process requests while connected
                    while self._running and self.is_connected:
                        try:
                            # Wait for request with timeout
                            request = await asyncio.wait_for(
                                self._request_queue.get(),
                                timeout=60.0
                            )
                            
                            if request is None:  # Shutdown signal
                                self.log(f"🔌 Nhận tín hiệu đóng session", "INFO")
                                break
                            
                            text, response_future = request
                            
                            try:
                                audio_data = await self._send_and_receive(session, text)
                                response_future.set_result(audio_data)
                            except Exception as e:
                                response_future.set_exception(e)
                                
                        except asyncio.TimeoutError:
                            # No requests - just continue waiting
                            continue
                        except Exception as e:
                            self.log(f"⚠️ Lỗi xử lý request: {str(e)}", "WARNING")
                
                self.is_connected = False
                self.session = None
                
            except Exception as e:
                self.is_connected = False
                self.session = None
                
                if self._running:
                    self.log(f"⚠️ Session bị ngắt: {str(e)}", "WARNING")
                    self.log(f"🔄 Reconnect sau {reconnect_delay}s...", "INFO")
                    await asyncio.sleep(reconnect_delay)
                    reconnect_delay = min(reconnect_delay * 2, 30.0)
        
        self.log(f"🔌 Session manager đã dừng", "INFO")
    
    async def _send_and_receive(self, session, text: str) -> bytes:
        """Gửi text và nhận audio response qua persistent session"""
        input_text = text
        if self.config.keep_voice_beta:
            input_text = "{" + text + "}"
        
        preview = input_text[:50] + "..." if len(input_text) > 50 else input_text
        self.log(f"📝 Gửi: {preview}", "INFO")
        
        audio_chunks = []
        
        # Sử dụng session.send() giống như WorkerEngine gốc - KHÔNG dùng send_client_content
        await session.send(input=input_text, end_of_turn=True)
        
        # Nhận audio - chỉ dùng response.data giống như code gốc
        async for response in session.receive():
            if data := response.data:
                audio_chunks.append(data)
        
        if audio_chunks:
            total_bytes = sum(len(c) for c in audio_chunks)
            self.log(f"✅ Nhận {len(audio_chunks)} chunks ({total_bytes} bytes)", "SUCCESS")
            return b''.join(audio_chunks)
        
        self.log(f"⚠️ Không nhận được audio data", "WARNING")
        return b''
    
    async def generate_audio(self, text: str) -> Optional[bytes]:
        """Gửi text và nhận audio thông qua persistent session"""
        if not self._running:
            self.log("❌ Session chưa được khởi động", "ERROR")
            return None
        
        # Wait for connection if not connected
        wait_count = 0
        while not self.is_connected and wait_count < 20:
            await asyncio.sleep(0.5)
            wait_count += 1
        
        if not self.is_connected:
            self.log("❌ Session không có kết nối", "ERROR")
            return None
        
        async with self._request_lock:
            try:
                # Create future for response
                loop = asyncio.get_event_loop()
                response_future = loop.create_future()
                
                # Put request in queue
                await self._request_queue.put((text, response_future))
                
                # Wait for response
                try:
                    audio_data = await asyncio.wait_for(response_future, timeout=120.0)
                    return audio_data
                except asyncio.TimeoutError:
                    self.log(f"⏰ Timeout waiting for audio", "ERROR")
                    return None
                    
            except Exception as e:
                self.log(f"❌ Lỗi generate_audio: {str(e)}", "ERROR")
                return None
    
    async def disconnect(self):
        """Ngắt kết nối và cleanup"""
        self._running = False
        self.is_connected = False
        
        # Send shutdown signal
        if self._request_queue:
            await self._request_queue.put(None)
        
        # Wait for session task to finish
        if self._session_task:
            try:
                await asyncio.wait_for(self._session_task, timeout=5.0)
            except asyncio.TimeoutError:
                self._session_task.cancel()
        
        self.session = None
        self.client = None
        self._live_config = None
        
        self.log("🔌 Đã ngắt kết nối Persistent Session", "INFO")
    
    def stop(self):
        """Dừng session (sync version)"""
        self._running = False


# Alias để tương thích ngược với code cũ
PersistentTTSSession = TruePersistentSession


# =============================================================================
# LIVE SESSION WORKER ENGINE - Sử dụng True Persistent Session
# =============================================================================

class LiveSessionWorkerEngine:
    """
    Worker Engine sử dụng True Persistent Session.
    Mỗi worker giữ MỘT session mở và gửi nhiều requests qua session đó.
    """
    
    def __init__(self, worker_id: int, api_key: str, config: TTSConfig, log_callback=None):
        self.worker_id = worker_id
        self.api_key = api_key
        self.config = config
        self.log = log_callback or print
        self.session: Optional[TruePersistentSession] = None
        self.is_connected = False
        
    async def connect(self) -> bool:
        """Khởi tạo và kết nối session"""
        self.session = TruePersistentSession(
            api_key=self.api_key,
            config=self.config,
            log_callback=self.log
        )
        success = await self.session.connect()
        self.is_connected = success
        return success
    
    async def disconnect(self):
        """Ngắt kết nối session"""
        if self.session:
            await self.session.disconnect()
        self.is_connected = False
    
    async def generate_audio(self, text: str) -> bytes:
        """Generate audio sử dụng persistent session"""
        if not self.is_connected or not self.session:
            await self.connect()
        
        audio_data = await self.session.generate_audio(text)
        if audio_data is None or len(audio_data) == 0:
            raise ValueError(f"Failed to generate audio: no data for '{text[:50]}...'")
        return audio_data
    
    def recreate_session(self):
        """Đánh dấu cần recreate session"""
        self.is_connected = False



# =============================================================================
# WORKER ENGINE
# =============================================================================

class WorkerEngine:
    def __init__(self, worker_id: int, api_key: str, config: TTSConfig):
        self.worker_id = worker_id
        self.api_key = api_key
        self.config = config
        self._setup_client()
    
    def _setup_client(self):
        api_version = "v1alpha" if self.config.affective_dialog or self.config.proactive_audio else "v1beta"
        self.client = genai.Client(
            http_options={"api_version": api_version},
            api_key=self.api_key,
        )
    
    def _build_config(self) -> types.LiveConnectConfig:
        cfg = {
            "response_modalities": ["AUDIO"],
            "speech_config": types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=self.config.voice)
                )
            ),
            "media_resolution": self.config.media_resolution,
            "context_window_compression": types.ContextWindowCompressionConfig(
                trigger_tokens=25600,
                sliding_window=types.SlidingWindow(target_tokens=12800),
            ),
        }
        
        # FIXED: Đặt system_instruction trong config để API xử lý đúng cách
        # thay vì nối vào text input (cách cũ không tối ưu)
        if self.config.system_instruction:
            cfg["system_instruction"] = self.config.system_instruction
        
        if self.config.thinking_mode:
            cfg["thinking_config"] = types.ThinkingConfig(
                thinking_budget=self.config.thinking_budget,
                include_thoughts=True
            )
        
        if self.config.affective_dialog:
            cfg["enable_affective_dialog"] = True
        
        if self.config.proactive_audio:
            cfg["proactivity"] = {"proactive_audio": True}
        
        return types.LiveConnectConfig(**cfg)
    
    async def generate_audio(self, text: str) -> bytes:
        chunks = []
        config = self._build_config()
        
        # FIXED: Chỉ gửi text thuần, system_instruction đã được đặt trong config
        # (Giống như cách Live_session.py xử lý)
        input_text = text
        
        # Keep voice beta mode - wrap text in {content} for consistent voice
        if self.config.keep_voice_beta:
            input_text = "{" + text + "}"
            
        print(f"DEBUG [Worker {self.worker_id}] Sending: {input_text[:100]}...")

        async with self.client.aio.live.connect(model=MODEL, config=config) as session:
            await session.send(input=input_text, end_of_turn=True)
            async for response in session.receive():
                if data := response.data:
                    chunks.append(data)
        
        return b''.join(chunks)
    
    def recreate_client(self):
        """Recreate client connection - useful after connection errors"""
        self._setup_client()


# =============================================================================
# MULTI-THREAD PROCESSOR 
# =============================================================================

class MultiThreadProcessor:
    def __init__(self, api_keys: List[str], config: TTSConfig, 
                 log_callback, status_callback, progress_callback, audio_callback):
        self.api_keys = [k.strip() for k in api_keys if k.strip()]
        self.config = config
        self.log = log_callback
        self.update_status = status_callback
        self.update_progress = progress_callback
        self.on_audio_generated = audio_callback
        
        self.task_queue: asyncio.Queue = None
        self.results: Dict[int, bool] = {}
        self.is_running = False
        
        self.total_tasks = 0
        self.completed_tasks = 0
        self.lock = asyncio.Lock()
    
    def _get_total_workers(self) -> int:
        """Calculate total number of workers based on config"""
        if self.config.multi_worker_enabled:
            return len(self.api_keys) * self.config.workers_per_key
        return len(self.api_keys)
    
    def _get_worker_assignments(self) -> List[tuple]:
        """
        Get list of (worker_id, api_key) tuples.
        If multi-worker is enabled, same key is assigned to multiple workers.
        """
        assignments = []
        worker_id = 0
        
        if self.config.multi_worker_enabled:
            for api_key in self.api_keys:
                for _ in range(self.config.workers_per_key):
                    assignments.append((worker_id, api_key))
                    worker_id += 1
        else:
            for api_key in self.api_keys:
                assignments.append((worker_id, api_key))
                worker_id += 1
        
        return assignments
    
    async def process_all(self, subtitles: List[Subtitle], output_dir: Path, prefix: str):
        if not self.api_keys:
            self.log("❌ No API keys!", "ERROR")
            return
        
        self.is_running = True
        self.total_tasks = len(subtitles)
        self.completed_tasks = 0
        self.results = {}
        
        self.task_queue = asyncio.Queue()
        for sub in subtitles:
            await self.task_queue.put(sub)
        
        # Get worker assignments
        worker_assignments = self._get_worker_assignments()
        total_workers = len(worker_assignments)
        
        # Log startup info
        if self.config.multi_worker_enabled:
            self.log(f"🚀 Multi-Worker Mode: {len(self.api_keys)} API key(s) × {self.config.workers_per_key} worker(s) = {total_workers} total workers", "INFO")
        else:
            self.log(f"🚀 Starting {total_workers} workers for {self.total_tasks} subtitles", "INFO")
        
        # Create workers
        workers = [
            asyncio.create_task(self._worker(worker_id, api_key, output_dir, prefix))
            for worker_id, api_key in worker_assignments
        ]
        
        await asyncio.gather(*workers)
        
        successful = sum(1 for v in self.results.values() if v)
        self.log(f"\n{'='*50}", "INFO")
        self.log(f"✅ Done! Success: {successful}/{len(self.results)}", "SUCCESS")
    
    async def _worker(self, worker_id: int, api_key: str, output_dir: Path, prefix: str):
        try:
            key_preview = f"...{api_key[-4:]}" if len(api_key) >= 4 else "****"
            
            # Sử dụng LiveSessionWorkerEngine nếu live_session_enabled, ngược lại dùng WorkerEngine
            if self.config.live_session_enabled:
                engine = LiveSessionWorkerEngine(worker_id, api_key, self.config, log_callback=self.log)
                await engine.connect()
                self.log(f"📞 Worker {worker_id} (Key: {key_preview}) started", "INFO")
            else:
                engine = WorkerEngine(worker_id, api_key, self.config)
                self.log(f"🔧 Worker {worker_id} (Key: {key_preview}) started", "INFO")
            
            consecutive_errors = 0
            max_consecutive_errors = 3
            
            while self.is_running:
                try:
                    subtitle = await asyncio.wait_for(self.task_queue.get(), timeout=1.0)
                except asyncio.TimeoutError:
                    if self.task_queue.empty():
                        break
                    continue
                
                if not self.is_running:
                    await self.task_queue.put(subtitle)
                    break
                
                # --- ENHANCED RETRY LOGIC ---
                success = False
                last_error = ""
                
                for attempt in range(1, MAX_RETRIES + 1):
                    try:
                        audio_data = await engine.generate_audio(subtitle.text)
                        
                        if not audio_data:
                            raise ValueError("Received 0 bytes (No Audio) - Connection issue likely")
                        
                        if len(audio_data) < MIN_AUDIO_FILE_SIZE:
                            raise ValueError(f"Audio too short ({len(audio_data)} bytes) - May be incomplete")
                        
                        # --- SPEED PROCESSING ---
                        final_rate = int(RECEIVE_SAMPLE_RATE * self.config.speed)
                        
                        output_file = output_dir / f"{subtitle.index:04d}_{prefix}.wav"
                        
                        save_wave_file(str(output_file), audio_data, rate=final_rate)
                        
                        duration_ms = len(audio_data) / (final_rate * AUDIO_SAMPLE_WIDTH) * 1000
                        
                        status_msg = f"✅ W{worker_id} [{subtitle.index:04d}] ({duration_ms:.0f}ms)"
                        if self.config.speed != 1.0:
                             status_msg += f" [x{self.config.speed:.1f}]"
                        if attempt > 1:
                            status_msg += f" [Retry {attempt-1}]"
                            
                        self.log(status_msg, "SUCCESS")
                        
                        self.results[subtitle.index] = True
                        success = True
                        consecutive_errors = 0  # Reset error counter on success
                        
                        self.on_audio_generated(GeneratedAudio(
                            index=subtitle.index,
                            file_path=str(output_file),
                            text=subtitle.text,
                            duration_ms=duration_ms
                        ))
                        break 
                        
                    except Exception as e:
                        last_error = str(e)
                        is_conn_error = is_connection_error(last_error)
                        
                        if attempt < MAX_RETRIES:
                            delay = calculate_retry_delay(attempt, is_conn_error)
                            
                            # Log retry with appropriate detail
                            if is_conn_error:
                                self.log(
                                    f"⚠️ W{worker_id} [{subtitle.index:04d}] Connection issue (attempt {attempt}/{MAX_RETRIES}): {last_error[:50]}... Retry in {delay:.1f}s", 
                                    "WARNING"
                                )
                                # Recreate client/session on connection errors
                                if attempt >= 2:
                                    if self.config.live_session_enabled and hasattr(engine, 'recreate_session'):
                                        engine.recreate_session()
                                    elif hasattr(engine, 'recreate_client'):
                                        engine.recreate_client()
                                    self.log(f"🔄 W{worker_id} Recreated client connection", "INFO")
                            else:
                                self.log(
                                    f"⚠️ W{worker_id} [{subtitle.index:04d}] Attempt {attempt}/{MAX_RETRIES} failed: {last_error[:80]} -> Retry in {delay:.1f}s", 
                                    "WARNING"
                                )
                            
                            await asyncio.sleep(delay)
                        else:
                            self.log(f"❌ W{worker_id} [{subtitle.index:04d}] FAILED after {MAX_RETRIES} attempts: {last_error}", "ERROR")
                            self.results[subtitle.index] = False
                            consecutive_errors += 1
                
                # Check for too many consecutive errors (might indicate API key issue)
                if consecutive_errors >= max_consecutive_errors:
                    self.log(f"⚠️ W{worker_id} Too many consecutive errors - pausing for 30s...", "WARNING")
                    await asyncio.sleep(30)
                    consecutive_errors = 0
                    # Recreate client/session dựa trên engine type
                    if self.config.live_session_enabled and hasattr(engine, 'recreate_session'):
                        engine.recreate_session()
                    elif hasattr(engine, 'recreate_client'):
                        engine.recreate_client()
                
                async with self.lock:
                    self.completed_tasks += 1
                    progress = (self.completed_tasks / self.total_tasks) * 100
                    self.update_progress(progress)
                    self.update_status(f"Processing: {self.completed_tasks}/{self.total_tasks}")
                
                self.task_queue.task_done()
            
            self.log(f"🏁 Worker {worker_id} finished", "INFO")
            
        except Exception as e:
            self.log(f"❌ Worker {worker_id} crashed: {e}", "ERROR")
    
    def stop(self):
        self.is_running = False


# =============================================================================
# LONG TEXT PROCESSOR (Enhanced with Multi-Worker per Key)
# =============================================================================

class LongTextProcessor:
    """Processor for long text TTS with chunking and merging"""
    
    def __init__(self, api_keys: List[str], config: TTSConfig,
                 log_callback, status_callback, progress_callback):
        self.api_keys = [k.strip() for k in api_keys if k.strip()]
        self.config = config
        self.log = log_callback
        self.update_status = status_callback
        self.update_progress = progress_callback
        
        self.is_running = False
        self.task_queue: asyncio.Queue = None
        self.results: Dict[int, str] = {}  # index -> file_path
        self.failed_chunks: Dict[int, str] = {}  # index -> text (for retry)
        self.chunks_data: Dict[int, str] = {}  # index -> text (original chunks)
        self.total_tasks = 0
        self.completed_tasks = 0
        self.lock = asyncio.Lock()
    
    def _get_worker_assignments(self) -> List[tuple]:
        """
        Get list of (worker_id, api_key) tuples.
        If multi-worker is enabled, same key is assigned to multiple workers.
        """
        assignments = []
        worker_id = 0
        
        if self.config.multi_worker_enabled:
            for api_key in self.api_keys:
                for _ in range(self.config.workers_per_key):
                    assignments.append((worker_id, api_key))
                    worker_id += 1
        else:
            for api_key in self.api_keys:
                assignments.append((worker_id, api_key))
                worker_id += 1
        
        return assignments
    
    def _save_chunk_map(self, temp_dir: str, chunks: List[TextChunk]):
        """Save chunk map to JSON file for tracking and recovery"""
        chunk_map = {
            "total_chunks": len(chunks),
            "chunks": {c.index: {"text": c.text, "length": c.original_length} for c in chunks}
        }
        map_file = os.path.join(temp_dir, "_chunk_map.json")
        with open(map_file, "w", encoding="utf-8") as f:
            json.dump(chunk_map, f, ensure_ascii=False, indent=2)
        return map_file
    
    def _load_chunk_map(self, temp_dir: str) -> Optional[Dict]:
        """Load chunk map from JSON file"""
        map_file = os.path.join(temp_dir, "_chunk_map.json")
        if os.path.exists(map_file):
            with open(map_file, "r", encoding="utf-8") as f:
                return json.load(f)
        return None
    
    def _get_missing_chunks(self, total_chunks: int) -> List[int]:
        """Get list of missing chunk indices"""
        expected = set(range(1, total_chunks + 1))
        generated = set(self.results.keys())
        missing = expected - generated
        return sorted(list(missing))
    
    async def _retry_missing_chunks(self, missing_indices: List[int], temp_dir: str) -> int:
        """
        Retry generating missing chunks.
        Returns the number of successfully regenerated chunks.
        """
        if not missing_indices:
            return 0
        
        self.log(f"🔄 Đang retry {len(missing_indices)} chunks bị thiếu: {missing_indices}", "INFO")
        
        # Create new task queue with missing chunks
        retry_queue = asyncio.Queue()
        for idx in missing_indices:
            if idx in self.chunks_data:
                chunk = TextChunk(index=idx, text=self.chunks_data[idx], original_length=len(self.chunks_data[idx]))
                await retry_queue.put(chunk)
            else:
                self.log(f"❌ Không tìm thấy text cho chunk {idx}", "ERROR")
        
        if retry_queue.empty():
            return 0
        
        # Get worker assignments (fewer workers for retry to be more reliable)
        worker_assignments = self._get_worker_assignments()
        # Use fewer workers for retry (max 2 per key or half of original)
        retry_workers = min(len(worker_assignments), max(2, len(worker_assignments) // 2))
        
        retry_success = 0
        retry_lock = asyncio.Lock()
        
        async def retry_worker(worker_id: int, api_key: str):
            nonlocal retry_success
            try:
                # Sử dụng WorkerEngine cho retry (more stable)
                engine = WorkerEngine(worker_id, api_key, self.config)
                
                while True:
                    try:
                        chunk = await asyncio.wait_for(retry_queue.get(), timeout=1.0)
                    except asyncio.TimeoutError:
                        if retry_queue.empty():
                            break
                        continue
                    
                    # Extra retry logic for recovery - use RECOVERY_EXTRA_RETRIES for additional attempts
                    recovery_max_retries = MAX_RETRIES + RECOVERY_EXTRA_RETRIES
                    for attempt in range(1, recovery_max_retries + 1):
                        try:
                            audio_data = await engine.generate_audio(chunk.text)
                            
                            if not audio_data or len(audio_data) < MIN_AUDIO_FILE_SIZE:
                                raise ValueError("Audio too short or empty")
                            
                            final_rate = int(RECEIVE_SAMPLE_RATE * self.config.speed)
                            output_file = os.path.join(temp_dir, f"chunk_{chunk.index:04d}.wav")
                            
                            save_wave_file(output_file, audio_data, rate=final_rate)
                            
                            async with retry_lock:
                                self.results[chunk.index] = output_file
                                retry_success += 1
                            
                            self.log(f"✅ RETRY OK: Chunk [{chunk.index:04d}]", "SUCCESS")
                            break
                            
                        except Exception as e:
                            if attempt < recovery_max_retries:
                                delay = calculate_retry_delay(attempt, is_connection_error(str(e)))
                                self.log(f"⚠️ RETRY [{chunk.index:04d}] Attempt {attempt} failed, retry in {delay:.1f}s", "WARNING")
                                await asyncio.sleep(delay)
                                engine.recreate_client()
                            else:
                                self.log(f"❌ RETRY FAILED: Chunk [{chunk.index:04d}]: {str(e)[:50]}", "ERROR")
                    
                    retry_queue.task_done()
                    
            except Exception as e:
                self.log(f"❌ Retry worker {worker_id} crashed: {e}", "ERROR")
        
        # Start retry workers
        retry_tasks = [
            asyncio.create_task(retry_worker(i, worker_assignments[i % len(worker_assignments)][1]))
            for i in range(retry_workers)
        ]
        
        await asyncio.gather(*retry_tasks)
        
        return retry_success
    
    async def process_text(self, text: str, output_file: str, chunk_size: int = 1000,
                          temp_dir: str = None, ffmpeg_path: str = "ffmpeg.exe",
                          delete_chunks: bool = True, chunk_v2_mode: bool = False) -> bool:
        """
        Process long text into a single audio file.
        Returns True if successful.
        
        Args:
            text: Input text to process
            output_file: Output file path
            chunk_size: Target chunk size in characters
            temp_dir: Temporary directory for chunks
            ffmpeg_path: Path to ffmpeg executable
            delete_chunks: Whether to delete temp chunks after merging
            chunk_v2_mode: If True, use punctuation-based chunking (Ngắt dòng v2)
        """
        if not self.api_keys:
            self.log("❌ No API keys!", "ERROR")
            return False
        
        # Create chunks - use v2 mode if enabled
        if chunk_v2_mode:
            chunks = split_text_by_punctuation_v2(text, target_chunk_size=chunk_size, remove_punct=True)
            self.log(f"📝 Ngắt dòng v2: Text split into {len(chunks)} chunks (target {chunk_size} chars)", "INFO")
        else:
            chunks = split_text_into_chunks(text, chunk_size)
            self.log(f"📝 Text split into {len(chunks)} chunks (max {chunk_size} chars each)", "INFO")
        
        if not chunks:
            self.log("❌ No text to process!", "ERROR")
            return False
        
        # Setup temp directory - use absolute path
        output_file_abs = os.path.abspath(output_file)
        if temp_dir is None:
            temp_dir = os.path.join(os.path.dirname(output_file_abs), "_temp_chunks")
        else:
            temp_dir = os.path.abspath(temp_dir)
        os.makedirs(temp_dir, exist_ok=True)
        
        self.log(f"📂 Temp directory: {temp_dir}", "INFO")
        
        # Save chunk map to JSON for tracking
        self._save_chunk_map(temp_dir, chunks)
        
        # Store chunks data for potential retry
        self.chunks_data = {c.index: c.text for c in chunks}
        
        self.is_running = True
        self.total_tasks = len(chunks)
        self.completed_tasks = 0
        self.results = {}
        self.failed_chunks = {}
        
        # Create task queue
        self.task_queue = asyncio.Queue()
        for chunk in chunks:
            await self.task_queue.put(chunk)
        
        # Get worker assignments
        worker_assignments = self._get_worker_assignments()
        total_workers = len(worker_assignments)
        
        # Log startup info
        if self.config.multi_worker_enabled:
            self.log(f"🚀 Multi-Worker Mode: {len(self.api_keys)} API key(s) × {self.config.workers_per_key} worker(s) = {total_workers} total workers", "INFO")
        else:
            self.log(f"🚀 Starting {total_workers} workers for {self.total_tasks} chunks", "INFO")
        
        # Start workers
        workers = [
            asyncio.create_task(self._worker(worker_id, api_key, temp_dir))
            for worker_id, api_key in worker_assignments
        ]
        
        await asyncio.gather(*workers)
        
        # Check for missing chunks and retry if needed
        missing_chunks = self._get_missing_chunks(self.total_tasks)
        
        if missing_chunks:
            self.log(f"⚠️ Phát hiện {len(missing_chunks)} chunks thiếu sau xử lý lần đầu", "WARNING")
            
            # Retry missing chunks
            retry_success = await self._retry_missing_chunks(missing_chunks, temp_dir)
            
            # Check again after retry
            still_missing = self._get_missing_chunks(self.total_tasks)
            
            if still_missing:
                self.log(f"❌ Sau khi retry, vẫn còn {len(still_missing)} chunks thiếu: {still_missing}", "ERROR")
                self.log(f"⚠️ Không thể merge vì thiếu chunks. Các chunks đã tạo được lưu tại: {temp_dir}", "WARNING")
                return False
            else:
                self.log(f"✅ Đã retry thành công tất cả chunks thiếu!", "SUCCESS")
        
        # Final check - verify all files exist
        successful = len([v for v in self.results.values() if v and os.path.exists(v)])
        if successful < self.total_tasks:
            self.log(f"⚠️ Only {successful}/{self.total_tasks} chunks generated. Cannot merge.", "WARNING")
            return False
        
        # Merge files
        self.log("🔧 Merging audio chunks with FFmpeg...", "INFO")
        self.update_status("Merging audio files...")
        
        chunk_files = [self.results[i] for i in sorted(self.results.keys())]
        success = merge_wav_files_ffmpeg(chunk_files, output_file, ffmpeg_path)
        
        if success:
            self.log(f"✅ Merged successfully: {output_file}", "SUCCESS")
            
            # Clean up temp files
            if delete_chunks:
                self.log("🧹 Cleaning up temporary files...", "INFO")
                for f in chunk_files:
                    try:
                        os.remove(f)
                    except Exception:
                        pass
                # Remove chunk map file
                map_file = os.path.join(temp_dir, "_chunk_map.json")
                if os.path.exists(map_file):
                    try:
                        os.remove(map_file)
                    except Exception:
                        pass
                try:
                    os.rmdir(temp_dir)
                except Exception:
                    pass
        else:
            self.log("❌ Failed to merge audio files. Check FFmpeg installation.", "ERROR")
        
        return success
    
    async def _worker(self, worker_id: int, api_key: str, temp_dir: str):
        try:
            key_preview = f"...{api_key[-4:]}" if len(api_key) >= 4 else "****"
            
            # Sử dụng LiveSessionWorkerEngine nếu live_session_enabled, ngược lại dùng WorkerEngine
            if self.config.live_session_enabled:
                engine = LiveSessionWorkerEngine(worker_id, api_key, self.config, log_callback=self.log)
                await engine.connect()
                self.log(f"📞 Worker {worker_id} (Key: {key_preview}) started", "INFO")
            else:
                engine = WorkerEngine(worker_id, api_key, self.config)
                self.log(f"🔧 Worker {worker_id} (Key: {key_preview}) started", "INFO")
            
            consecutive_errors = 0
            max_consecutive_errors = 3
            
            while self.is_running:
                try:
                    chunk = await asyncio.wait_for(self.task_queue.get(), timeout=1.0)
                except asyncio.TimeoutError:
                    if self.task_queue.empty():
                        break
                    continue
                
                if not self.is_running:
                    await self.task_queue.put(chunk)
                    break
                
                # Enhanced retry logic
                success = False
                last_error = ""
                
                for attempt in range(1, MAX_RETRIES + 1):
                    try:
                        audio_data = await engine.generate_audio(chunk.text)
                        
                        if not audio_data:
                            raise ValueError("Received 0 bytes (No Audio) - Connection issue likely")
                        
                        if len(audio_data) < MIN_AUDIO_FILE_SIZE:
                            raise ValueError(f"Audio too short ({len(audio_data)} bytes)")
                        
                        final_rate = int(RECEIVE_SAMPLE_RATE * self.config.speed)
                        output_file = os.path.join(temp_dir, f"chunk_{chunk.index:04d}.wav")
                        
                        save_wave_file(output_file, audio_data, rate=final_rate)
                        
                        duration_ms = len(audio_data) / (final_rate * AUDIO_SAMPLE_WIDTH) * 1000
                        
                        status_msg = f"✅ W{worker_id} Chunk [{chunk.index:04d}] ({duration_ms:.0f}ms)"
                        if attempt > 1:
                            status_msg += f" [Retry {attempt-1}]"
                        self.log(status_msg, "SUCCESS")
                        
                        async with self.lock:
                            self.results[chunk.index] = output_file
                        
                        success = True
                        consecutive_errors = 0
                        break
                        
                    except Exception as e:
                        last_error = str(e)
                        is_conn_error = is_connection_error(last_error)
                        
                        if attempt < MAX_RETRIES:
                            delay = calculate_retry_delay(attempt, is_conn_error)
                            
                            if is_conn_error:
                                self.log(
                                    f"⚠️ W{worker_id} Chunk [{chunk.index:04d}] Connection issue (attempt {attempt}/{MAX_RETRIES}): {last_error[:50]}... Retry in {delay:.1f}s", 
                                    "WARNING"
                                )
                                if attempt >= 2:
                                    # Recreate client/session dựa trên engine type
                                    if self.config.live_session_enabled and hasattr(engine, 'recreate_session'):
                                        engine.recreate_session()
                                    elif hasattr(engine, 'recreate_client'):
                                        engine.recreate_client()
                            else:
                                self.log(
                                    f"⚠️ W{worker_id} Chunk [{chunk.index:04d}] Attempt {attempt}/{MAX_RETRIES} failed: {last_error[:80]} -> Retry in {delay:.1f}s", 
                                    "WARNING"
                                )
                            
                            await asyncio.sleep(delay)
                        else:
                            self.log(f"❌ W{worker_id} Chunk [{chunk.index:04d}] FAILED: {last_error}", "ERROR")
                            consecutive_errors += 1
                
                # Check for too many consecutive errors
                if consecutive_errors >= max_consecutive_errors:
                    self.log(f"⚠️ W{worker_id} Too many consecutive errors - pausing for 30s...", "WARNING")
                    await asyncio.sleep(30)
                    consecutive_errors = 0
                    # Recreate client/session dựa trên engine type
                    if self.config.live_session_enabled and hasattr(engine, 'recreate_session'):
                        engine.recreate_session()
                    elif hasattr(engine, 'recreate_client'):
                        engine.recreate_client()
                
                async with self.lock:
                    self.completed_tasks += 1
                    progress = (self.completed_tasks / self.total_tasks) * 100
                    self.update_progress(progress)
                    self.update_status(f"Chunks: {self.completed_tasks}/{self.total_tasks}")
                
                self.task_queue.task_done()
            
            self.log(f"🏁 Worker {worker_id} finished", "INFO")
            
        except Exception as e:
            self.log(f"❌ Worker {worker_id} crashed: {e}", "ERROR")
    
    def stop(self):
        self.is_running = False


# =============================================================================
# GUI APPLICATION
# =============================================================================

class StudioGUI(ctk.CTk):
    SANITIZED_ERROR_FALLBACK = os.getenv("VN_TTS_ERROR_FALLBACK", "Đã xảy ra lỗi không xác định")
    SANITIZE_URL_PATTERN = re.compile(r"(https?://\S+|github\.com/\S*)")

    def __init__(self):
        super().__init__()

        # Window Setup
        self.title("AIOLuancher TTS")
        
        # FIX: Set window size and center it properly to prevent jumping/lag
        window_width = 1400
        window_height = 900
        
        # Get screen dimensions
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        
        # Calculate center position
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2
        
        # Set geometry with position
        self.geometry(f"{window_width}x{window_height}+{x}+{y}")
        self.minsize(1200, 800)
        
        # Grid layout
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Data & Logic Init
        self.subtitles: List[Subtitle] = []
        self.generated_audios: List[GeneratedAudio] = []
        self.processor: Optional[MultiThreadProcessor] = None
        self.long_text_processor: Optional[LongTextProcessor] = None
        self.is_processing = False
        self.log_queue = Queue()
        self.audio_queue = Queue()
        
        self.player = AudioPlayer()
        self.is_playing_all = False
        self.current_play_index = 0
        self.lt_selected_files: List[str] = []
        
        # Flag to stop consumers on close
        self._is_closing = False

        # Load Settings Variables
        self.settings_file = "settings.json"
        self._init_settings_vars()
        self._load_settings()

        # UI Setup
        self._setup_ui()
        
        # FIX: Update window after all configuration is complete to prevent drag lag
        self.update_idletasks()
        
        # Start Consumers
        self._start_consumers()
        
        # Protocol
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _init_settings_vars(self):
        """Khởi tạo các biến lưu trữ cài đặt"""
        self.api_key_content = ""
        self.sys_instr_content = DEFAULT_SYSTEM_INSTRUCTION
        self.multi_worker_enabled_val = False
        self.workers_per_key_val = 2
        self.voice_val = "Kore"
        self.speed_val = 1.0
        # Thinking mode settings
        self.thinking_mode_val = False
        self.thinking_budget_val = 1024
        self.affective_val = False
        self.proactive_val = False
        # Capcut Voice settings
        self.capcut_session_id = ""
        self.capcut_custom_voices = []  # List of custom voice dicts
        # Edge TTS settings
        self.edge_voices_cache = []  # Cached voice list
        self.edge_last_fetch = 0  # Timestamp of last fetch
        # FFmpeg path - use get_default_ffmpeg_path() to correctly get the app directory
        self.ffmpeg_path = get_default_ffmpeg_path()
        # Ngắt dòng v2 settings
        self.gemini_chunk_v2_enabled = False  # Enable punctuation-based chunking
        self.lt_chunk_v2_enabled = False  # Enable punctuation-based chunking for Long Text
        # Gemini TTS file chunking settings
        self.gemini_chunk_size = GEMINI_DEFAULT_CHUNK_SIZE  # Default 300 chars
        # VN TTS settings
        self.vieneu_backbone = "VN TTS Q4 (Nhanh)"
        self.vieneu_codec = "NeuCodec (Standard)"
        self.vieneu_device = "Auto"

    def _setup_ui(self):
        # Main Tabview
        self.tabview = ctk.CTkTabview(self, width=1380, height=880)
        self.tabview.pack(fill="both", expand=True, padx=10, pady=10)

        # Create Tabs
        self.tab_dashboard = self.tabview.add("Gemini TTS")
        self.tab_longtext = self.tabview.add("Long Text Engine")
        self.tab_multivoice = self.tabview.add("Multi Voice (Đa giọng)")
        self.tab_capcut = self.tabview.add("Capcut Voice")
        self.tab_edge = self.tabview.add("Edge TTS")
        self.tab_vieneu = self.tabview.add("🇻🇳 VN TTS")
        self.tab_script = self.tabview.add("Đọc Kịch Bản")
        self.tab_settings = self.tabview.add("⚙Configuration")

        # Setup Content
        self._setup_settings_tab()
        self._setup_dashboard_tab()
        self._setup_longtext_tab()
        self._setup_multivoice_tab()
        self._setup_capcut_tab()
        self._setup_edge_tab()
        self._setup_vieneu_tab()
        self._setup_script_tab()
        
        # Bind optimized paste handlers to all text inputs to prevent UI lag
        self._bind_optimized_paste_handlers()

    def _bind_optimized_paste_handlers(self):
        """Bind optimized paste handlers to all text input widgets to prevent UI lag"""
        # List of all textbox widgets that may receive long text paste
        textboxes_to_optimize = []
        
        # Capcut text input
        if hasattr(self, 'capcut_text_input'):
            textboxes_to_optimize.append(self.capcut_text_input)
        
        # Edge text input
        if hasattr(self, 'edge_text_input'):
            textboxes_to_optimize.append(self.edge_text_input)
        
        # Long text input
        if hasattr(self, 'lt_txt_input'):
            textboxes_to_optimize.append(self.lt_txt_input)
        
        # Script text input
        if hasattr(self, 'script_text_input'):
            textboxes_to_optimize.append(self.script_text_input)
        
        # VN TTS text input
        if hasattr(self, 'vieneu_text_input'):
            textboxes_to_optimize.append(self.vieneu_text_input)
        
        for textbox in textboxes_to_optimize:
            textbox.bind("<Control-v>", lambda e, tb=textbox: self._optimized_paste(e, tb))
            textbox.bind("<Control-V>", lambda e, tb=textbox: self._optimized_paste(e, tb))
            # Also bind Command-v for Mac
            textbox.bind("<Command-v>", lambda e, tb=textbox: self._optimized_paste(e, tb))
            textbox.bind("<Command-V>", lambda e, tb=textbox: self._optimized_paste(e, tb))
    
    def _optimized_paste(self, event, textbox):
        """
        Optimized paste handler to prevent UI lag when pasting long text.
        Uses chunked insertion with after_idle to keep UI responsive.
        """
        try:
            # Get clipboard content
            clipboard_text = self.clipboard_get()
            
            if not clipboard_text:
                return "break"
            
            # If text is short, paste normally
            if len(clipboard_text) < 5000:
                return None  # Let default handler process
            
            # For long text, use chunked paste to prevent lag
            # Delete selected text first (if any)
            try:
                textbox.delete("sel.first", "sel.last")
            except Exception:
                pass
            
            # Get cursor position
            cursor_pos = textbox.index("insert")
            
            # Disable textbox temporarily to batch the insert
            textbox.configure(state="normal")
            
            # Insert text in chunks to prevent UI freeze
            chunk_size = 10000  # Characters per chunk
            total_len = len(clipboard_text)
            
            def insert_chunk(start_idx):
                if start_idx >= total_len:
                    # Insertion complete, re-enable text editing if needed
                    return
                
                end_idx = min(start_idx + chunk_size, total_len)
                chunk = clipboard_text[start_idx:end_idx]
                
                # Insert at cursor position plus offset
                textbox.insert("insert", chunk)
                
                if end_idx < total_len:
                    # Schedule next chunk insertion
                    self.after_idle(lambda: insert_chunk(end_idx))
            
            # Start insertion
            self.after_idle(lambda: insert_chunk(0))
            
            # Prevent default paste
            return "break"
            
        except Exception as e:
            # Log error using the log method for consistency
            self.log(f"Paste error: {e}", "WARNING")
            return None  # Fall back to default paste

    # ==========================================================================
    # TAB: SETTINGS (CẤU HÌNH) - Restructured
    # ==========================================================================
    def _setup_settings_tab(self):
        tab = self.tab_settings
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_columnconfigure(1, weight=1)
        tab.grid_columnconfigure(2, weight=1)
        tab.grid_rowconfigure(0, weight=1)

        # --- Column 1: GOOGLE GEMINI TTS & THREADING ---
        google_frame = ctk.CTkFrame(tab, fg_color="#1a2332")
        google_frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=10)
        
        # Header
        header_google = ctk.CTkFrame(google_frame, fg_color="#2563eb", height=40)
        header_google.pack(fill="x")
        ctk.CTkLabel(header_google, text="GOOGLE GEMINI TTS", font=("Roboto", 14, "bold"), text_color="white").pack(pady=8)

        # API Keys
        ctk.CTkLabel(google_frame, text="API KEYS (mỗi key 1 dòng)", font=("Roboto", 12, "bold"), text_color="#60a5fa").pack(anchor="w", padx=15, pady=(15, 5))
        ctk.CTkLabel(google_frame, text="Tối đa 5 key, tránh bị Google khoá", text_color="gray", font=("Arial", 10)).pack(anchor="w", padx=15)
        
        self.txt_api_keys = ctk.CTkTextbox(google_frame, height=100, font=("Consolas", 11))
        self.txt_api_keys.pack(fill="x", padx=15, pady=5)
        self.txt_api_keys.insert("1.0", self.api_key_content)

        # System Instruction (Đã thu nhỏ chiều cao xuống 60)
        ctk.CTkLabel(google_frame, text="System Instruction", font=("Roboto", 12, "bold"), text_color="#60a5fa").pack(anchor="w", padx=15, pady=(10, 5))
        self.txt_sys_instr = ctk.CTkTextbox(google_frame, height=60, font=("Roboto", 11))
        self.txt_sys_instr.pack(fill="x", padx=15, pady=5)
        self.txt_sys_instr.insert("1.0", self.sys_instr_content)

        # Model parameters
        ctk.CTkLabel(google_frame, text="Model Parameters", font=("Roboto", 12, "bold"), text_color="#60a5fa").pack(anchor="w", padx=15, pady=(10, 5))
        
        # Grid nhỏ để chứa các switch cho gọn
        switch_frame = ctk.CTkFrame(google_frame, fg_color="transparent")
        switch_frame.pack(fill="x", padx=15)
        
        self.sw_thinking = ctk.CTkSwitch(switch_frame, text="Thinking Mode")
        self.sw_thinking.pack(anchor="w", pady=2)

        self.sw_affective = ctk.CTkSwitch(switch_frame, text="Biểu Cảm")
        self.sw_affective.pack(anchor="w", pady=2)
        
        self.sw_proactive = ctk.CTkSwitch(switch_frame, text="Proactive Audio")
        self.sw_proactive.pack(anchor="w", pady=2)

        self.lbl_budget = ctk.CTkLabel(google_frame, text="Thinking Budget: 1024")
        self.lbl_budget.pack(anchor="w", padx=15, pady=(5, 0))
        
        def update_budget(val):
            self.lbl_budget.configure(text=f"Thinking Budget: {int(val)}")

        self.slider_budget = ctk.CTkSlider(google_frame, from_=0, to=4096, number_of_steps=32, command=update_budget)
        self.slider_budget.set(self.thinking_budget_val)
        self.slider_budget.pack(fill="x", padx=15, pady=5)
        # Update label to match loaded value
        self.lbl_budget.configure(text=f"Thinking Budget: {self.thinking_budget_val}")
        
        # Restore saved switch values
        if self.thinking_mode_val: self.sw_thinking.select()
        if self.affective_val: self.sw_affective.select()
        if self.proactive_val: self.sw_proactive.select()

        # --- MOVED: Multi-Threading Section (Chuyển từ cột Performance sang đây) ---
        ctk.CTkFrame(google_frame, height=2, fg_color="#333").pack(fill="x", padx=15, pady=10) # Divider
        
        ctk.CTkLabel(google_frame, text="Multi-Threading (Tốc độ)", font=("Roboto", 12, "bold"), text_color="#a78bfa").pack(anchor="w", padx=15, pady=(5, 5))
        
        self.sw_multi_worker = ctk.CTkSwitch(google_frame, text="Bật đa luồng (Nhanh hơn)")
        self.sw_multi_worker.pack(anchor="w", padx=15, pady=5)
        if self.multi_worker_enabled_val: self.sw_multi_worker.select()

        self.lbl_workers = ctk.CTkLabel(google_frame, text=f"Workers per Key: {self.workers_per_key_val}")
        self.lbl_workers.pack(anchor="w", padx=15, pady=(5, 0))
        
        def update_worker_lbl(val):
            self.lbl_workers.configure(text=f"Workers per Key: {int(val)}")

        self.slider_workers = ctk.CTkSlider(google_frame, from_=1, to=50, number_of_steps=49, command=update_worker_lbl)
        self.slider_workers.set(self.workers_per_key_val)
        self.slider_workers.pack(fill="x", padx=15, pady=5)


        # --- Column 2: CAPCUT VOICE SETTINGS (Giữ nguyên) ---
        capcut_frame = ctk.CTkFrame(tab, fg_color="#1a2332")
        capcut_frame.grid(row=0, column=1, sticky="nsew", padx=5, pady=10)
        
        header_capcut = ctk.CTkFrame(capcut_frame, fg_color="#dc2626", height=40)
        header_capcut.pack(fill="x")
        ctk.CTkLabel(header_capcut, text="CAPCUT VOICE", font=("Roboto", 14, "bold"), text_color="white").pack(pady=8)

        ctk.CTkLabel(capcut_frame, text="Session ID (TikTok)", font=("Roboto", 12, "bold"), text_color="#f87171").pack(anchor="w", padx=15, pady=(15, 5))
        ctk.CTkLabel(capcut_frame, text="Lấy từ Cookie sessionid của TikTok", text_color="gray", font=("Arial", 10)).pack(anchor="w", padx=15)
        
        self.entry_capcut_session = ctk.CTkEntry(capcut_frame, placeholder_text="Nhập Session ID...", font=("Consolas", 11))
        self.entry_capcut_session.pack(fill="x", padx=15, pady=5)
        if self.capcut_session_id:
            self.entry_capcut_session.insert(0, self.capcut_session_id)

        # Custom Voice section
        ctk.CTkLabel(capcut_frame, text="Thêm Voice ID Mới", font=("Roboto", 12, "bold"), text_color="#f87171").pack(anchor="w", padx=15, pady=(20, 5))
        
        add_voice_frame = ctk.CTkFrame(capcut_frame, fg_color="transparent")
        add_voice_frame.pack(fill="x", padx=15, pady=5)
        
        self.entry_new_voice_id = ctk.CTkEntry(add_voice_frame, placeholder_text="Voice ID (vd: BV074_streaming)", width=200)
        self.entry_new_voice_id.pack(side="left", padx=(0, 5))
        
        self.entry_new_voice_name = ctk.CTkEntry(add_voice_frame, placeholder_text="Tên hiển thị", width=150)
        self.entry_new_voice_name.pack(side="left", padx=(0, 5))
        
        btn_add_voice = ctk.CTkButton(add_voice_frame, text="+ Thêm", width=70, fg_color="#22c55e", command=self._add_custom_capcut_voice)
        btn_add_voice.pack(side="left")

        # Custom voices list
        ctk.CTkLabel(capcut_frame, text="Voice ID Tùy Chỉnh", font=("Roboto", 11), text_color="gray").pack(anchor="w", padx=15, pady=(15, 5))
        
        self.capcut_custom_list = ctk.CTkScrollableFrame(capcut_frame, height=150, fg_color="#111827")
        self.capcut_custom_list.pack(fill="both", expand=True, padx=15, pady=5)
        self._refresh_custom_voice_list()


        # --- Column 3: EDGE TTS CONFIG (Đã đổi tên và bỏ phần Multi-thread) ---
        edge_frame = ctk.CTkFrame(tab, fg_color="#1a2332")
        edge_frame.grid(row=0, column=2, sticky="nsew", padx=5, pady=10)
        
        # Header (Màu tím hoặc xanh đậm cho Edge)
        header_edge = ctk.CTkFrame(edge_frame, fg_color="#7c3aed", height=40)
        header_edge.pack(fill="x")
        ctk.CTkLabel(header_edge, text="EDGE TTS & FFMPEG", font=("Roboto", 14, "bold"), text_color="white").pack(pady=8)

        # FFmpeg Settings Section
        ctk.CTkLabel(edge_frame, text="FFmpeg Path", font=("Roboto", 12, "bold"), text_color="#a78bfa").pack(anchor="w", padx=15, pady=(15, 5))
        ctk.CTkLabel(edge_frame, text="Đường dẫn đến ffmpeg.exe (dùng cho ghép audio)", text_color="gray", font=("Arial", 10)).pack(anchor="w", padx=15)
        
        ffmpeg_row = ctk.CTkFrame(edge_frame, fg_color="transparent")
        ffmpeg_row.pack(fill="x", padx=15, pady=5)
        
        self.entry_ffmpeg_path = ctk.CTkEntry(ffmpeg_row, placeholder_text="Đường dẫn ffmpeg.exe...")
        self.entry_ffmpeg_path.pack(side="left", fill="x", expand=True, padx=(0, 5))
        self.entry_ffmpeg_path.insert(0, self.ffmpeg_path)
        
        btn_browse_ffmpeg = ctk.CTkButton(ffmpeg_row, text="📂", width=40, command=self._browse_ffmpeg)
        btn_browse_ffmpeg.pack(side="right")

        # Edge TTS Cache info
        ctk.CTkLabel(edge_frame, text="Edge TTS Data", font=("Roboto", 12, "bold"), text_color="#a78bfa").pack(anchor="w", padx=15, pady=(20, 5))
        ctk.CTkLabel(edge_frame, text="Dữ liệu giọng đọc từ Microsoft Edge", text_color="gray", font=("Arial", 10)).pack(anchor="w", padx=15)
        
        self.lbl_edge_cache = ctk.CTkLabel(edge_frame, text="Voice cache: Chưa tải", text_color="gray")
        self.lbl_edge_cache.pack(anchor="w", padx=15, pady=(10, 5))
        
        btn_refresh_edge = ctk.CTkButton(edge_frame, text="Tải lại Voice List", fg_color="#6366f1", command=self._refresh_edge_voices)
        btn_refresh_edge.pack(fill="x", padx=15, pady=5)
        
        # Spacer để đẩy nút Save xuống đáy
        ctk.CTkFrame(edge_frame, fg_color="transparent").pack(fill="both", expand=True)

        # Save Button Area
        btn_save = ctk.CTkButton(edge_frame, text="LƯU TẤT CẢ CÀI ĐẶT", height=50, 
                                 fg_color="#22c55e", hover_color="#16a34a", font=("Roboto", 14, "bold"),
                                 command=self._save_settings_from_ui)
        btn_save.pack(side="bottom", fill="x", padx=15, pady=15)

    # ==========================================================================
    # TAB 1: STUDIO DASHBOARD (SRT/LINE)
    # ==========================================================================
    def _setup_dashboard_tab(self):
        tab = self.tab_dashboard
        
        # Chia layout: Left (Controls & File) - Right (Preview & Logs)
        main_paned = ctk.CTkFrame(tab, fg_color="transparent")
        main_paned.pack(fill="both", expand=True)
        
        # --- LEFT SIDEBAR ---
        left_col = ctk.CTkFrame(main_paned, width=400, corner_radius=10)
        left_col.pack(side="left", fill="y", padx=(0, 10), pady=5)
        
        # 1. File Input
        ctk.CTkLabel(left_col, text="FILE IO", font=("Roboto", 14, "bold"), text_color="#3B8ED0").pack(anchor="w", padx=15, pady=(15, 5))
        
        self.entry_file = ctk.CTkEntry(left_col, placeholder_text="Chọn SRT/TXT file...")
        self.entry_file.pack(fill="x", padx=15, pady=5)
        
        btn_browse_in = ctk.CTkButton(left_col, text="Browse Input", command=self._browse_input, fg_color="#444", hover_color="#555")
        btn_browse_in.pack(fill="x", padx=15, pady=2)

        self.entry_out = ctk.CTkEntry(left_col, placeholder_text="./tts_output")
        self.entry_out.insert(0, "./tts_output")
        self.entry_out.pack(fill="x", padx=15, pady=(15, 5))
        
        btn_browse_out = ctk.CTkButton(left_col, text="Browse Output", command=self._browse_output, fg_color="#444", hover_color="#555")
        btn_browse_out.pack(fill="x", padx=15, pady=2)

        self.entry_prefix = ctk.CTkEntry(left_col, placeholder_text="File prefix (e.g. audio)")
        self.entry_prefix.insert(0, "audio")
        self.entry_prefix.pack(fill="x", padx=15, pady=(15, 5))

        # 2. Voice Config
        ctk.CTkLabel(left_col, text="VOICE CONFIG", font=("Roboto", 14, "bold"), text_color="#3B8ED0").pack(anchor="w", padx=15, pady=(25, 5))
        
        self.combo_voice = ctk.CTkComboBox(left_col, values=VOICES)
        self.combo_voice.set(self.voice_val)
        self.combo_voice.pack(fill="x", padx=15, pady=5)

        self.combo_res = ctk.CTkComboBox(left_col, values=list(MEDIA_RESOLUTIONS.keys()))
        self.combo_res.set("Medium (258 tokens/image)")
        self.combo_res.pack(fill="x", padx=15, pady=5)

        lbl_speed = ctk.CTkLabel(left_col, text="Speed: 1.0x")
        lbl_speed.pack(anchor="w", padx=15, pady=(10, 0))
        
        def update_speed(val):
            lbl_speed.configure(text=f"Speed: {float(val):.1f}x")
            
        self.slider_speed = ctk.CTkSlider(left_col, from_=0.5, to=2.0, command=update_speed)
        self.slider_speed.set(1.0)
        self.slider_speed.pack(fill="x", padx=15, pady=5)

        # Live Session Mode checkbox - phiên làm việc liên tục như cuộc gọi điện thoại
        self.tts_sw_live_session = ctk.CTkSwitch(left_col, text="Live Session Mode")
        self.tts_sw_live_session.pack(anchor="w", padx=15, pady=(15, 5))
        
        # Keep Voice Beta Mode - giữ giọng ổn định bằng cách wrap text trong {content}
        self.tts_sw_keep_voice_beta = ctk.CTkSwitch(left_col, text="Giữ giọng beta")
        self.tts_sw_keep_voice_beta.pack(anchor="w", padx=15, pady=(5, 5))
        
        # Chunk settings for file processing (txt, docs, etc.)
        ctk.CTkLabel(left_col, text="CHUNK CONFIG (File dịch)", font=("Roboto", 12, "bold"), text_color="#3B8ED0").pack(anchor="w", padx=15, pady=(15, 5))
        
        chunk_frame = ctk.CTkFrame(left_col, fg_color="transparent")
        chunk_frame.pack(fill="x", padx=15, pady=5)
        
        ctk.CTkLabel(chunk_frame, text="Chunk size:", font=("Roboto", 10)).pack(side="left")
        self.gemini_chunk_size_entry = ctk.CTkEntry(chunk_frame, placeholder_text="300", width=70)
        self.gemini_chunk_size_entry.insert(0, str(self.gemini_chunk_size))
        self.gemini_chunk_size_entry.pack(side="left", padx=5)
        
        # Ngắt dòng v2 checkbox
        self.gemini_sw_chunk_v2 = ctk.CTkSwitch(left_col, text="Ngắt dòng v2 (theo dấu câu)")
        self.gemini_sw_chunk_v2.pack(anchor="w", padx=15, pady=5)
        if self.gemini_chunk_v2_enabled:
            self.gemini_sw_chunk_v2.select()
        
        # 3. Actions
        ctk.CTkLabel(left_col, text="ACTIONS", font=("Roboto", 14, "bold"), text_color="#3B8ED0").pack(anchor="w", padx=15, pady=(30, 5))
        
        self.btn_load = ctk.CTkButton(left_col, text="1. LOAD FILE", command=self._load_file, fg_color="#E09F3E", hover_color="#B57F2E", text_color="black")
        self.btn_load.pack(fill="x", padx=15, pady=5)
        
        self.btn_start = ctk.CTkButton(left_col, text="2. Bắt đầu tạo voice", command=self._start, height=40, font=("Roboto", 13, "bold"))
        self.btn_start.pack(fill="x", padx=15, pady=5)
        
        self.btn_stop = ctk.CTkButton(left_col, text="STOP", command=self._stop, fg_color="#D62828", hover_color="#A11D1D", state="disabled")
        self.btn_stop.pack(fill="x", padx=15, pady=5)

        # Progress
        self.progress_bar = ctk.CTkProgressBar(left_col)
        self.progress_bar.set(0)
        self.progress_bar.pack(fill="x", padx=15, pady=(20, 5))
        
        self.lbl_status = ctk.CTkLabel(left_col, text="Ready", text_color="gray")
        self.lbl_status.pack(padx=15)

        # --- RIGHT MAIN AREA ---
        right_col = ctk.CTkFrame(main_paned, fg_color="transparent")
        right_col.pack(side="left", fill="both", expand=True)
        right_col.grid_rowconfigure(1, weight=1)
        right_col.grid_columnconfigure(0, weight=1)

        # Top: Audio Preview List (Custom Scrollable Frame)
        preview_frame = ctk.CTkFrame(right_col, fg_color="#2B2B2B", corner_radius=10)
        preview_frame.grid(row=0, column=0, sticky="nsew", pady=(0, 10))
        
        header_frame = ctk.CTkFrame(preview_frame, height=40, fg_color="#333333")
        header_frame.pack(fill="x", padx=2, pady=2)
        ctk.CTkLabel(header_frame, text="Generated Audio Queue", font=("Roboto", 13, "bold")).pack(side="left", padx=10)
        
        ctk.CTkButton(header_frame, text="Clear List", width=80, height=25, fg_color="#555", command=self._clear_audio_list).pack(side="right", padx=5)
        ctk.CTkButton(header_frame, text="Play All", width=80, height=25, fg_color="green", command=self._play_all).pack(side="right", padx=5)
        ctk.CTkButton(header_frame, text="Stop Audio", width=80, height=25, fg_color="red", command=self._stop_playback).pack(side="right", padx=5)
        
        # Scrollable container for rows
        self.audio_scroll = ctk.CTkScrollableFrame(preview_frame, label_text="Audio Files")
        self.audio_scroll.pack(fill="both", expand=True, padx=5, pady=5)

        # Bottom: Logs
        log_frame = ctk.CTkFrame(right_col, height=200, fg_color="#1A1A1A")
        log_frame.grid(row=1, column=0, sticky="nsew")
        
        ctk.CTkLabel(log_frame, text="System Log", font=("Consolas", 12)).pack(anchor="w", padx=5, pady=2)
        self.txt_log = ctk.CTkTextbox(log_frame, font=("Consolas", 11), state="disabled", text_color="#00FF00")
        self.txt_log.pack(fill="both", expand=True, padx=5, pady=5)

    # ==========================================================================
    # TAB 2: LONG TEXT
    # ==========================================================================
    def _setup_longtext_tab(self):
        tab = self.tab_longtext
        
        main_paned = ctk.CTkFrame(tab, fg_color="transparent")
        main_paned.pack(fill="both", expand=True)

        # Controls Top
        ctrl_frame = ctk.CTkFrame(main_paned)
        ctrl_frame.pack(fill="x", pady=5)

        # Voice & Speed specific for Long Text
        self.lt_combo_voice = ctk.CTkComboBox(ctrl_frame, values=VOICES, width=150)
        self.lt_combo_voice.set(self.voice_val)
        self.lt_combo_voice.pack(side="left", padx=10, pady=10)
        
        # File Select
        self.btn_lt_files = ctk.CTkButton(ctrl_frame, text="Select .txt Files", command=self._lt_browse_files)
        self.btn_lt_files.pack(side="left", padx=10)
        
        self.lbl_lt_files = ctk.CTkLabel(ctrl_frame, text="No files selected", text_color="gray")
        self.lbl_lt_files.pack(side="left", padx=5)

        # Main Split
        content_frame = ctk.CTkFrame(main_paned, fg_color="transparent")
        content_frame.pack(fill="both", expand=True, pady=5)
        content_frame.grid_columnconfigure(0, weight=1)
        content_frame.grid_columnconfigure(1, weight=1)

        # Left: Direct Text
        left_f = ctk.CTkFrame(content_frame)
        left_f.grid(row=0, column=0, sticky="nsew", padx=(0, 5))
        
        ctk.CTkLabel(left_f, text="DIRECT TEXT INPUT", font=("Roboto", 14, "bold")).pack(pady=10)
        self.lt_txt_input = ctk.CTkTextbox(left_f, wrap="word")
        self.lt_txt_input.pack(fill="both", expand=True, padx=10, pady=5)
        
        self.lt_lbl_chars = ctk.CTkLabel(left_f, text="Chars: 0")
        self.lt_lbl_chars.pack(pady=5)
        self.lt_txt_input.bind("<KeyRelease>", self._lt_update_char_count)

        self.btn_lt_direct = ctk.CTkButton(left_f, text="PROCESS THIS TEXT", fg_color="green", command=self._lt_process_direct_text)
        self.btn_lt_direct.pack(fill="x", padx=10, pady=10)

        # Right: Config & Logs
        right_f = ctk.CTkFrame(content_frame)
        right_f.grid(row=0, column=1, sticky="nsew", padx=(5, 0))
        
        # Configs
        cfg_box = ctk.CTkFrame(right_f)
        cfg_box.pack(fill="x", padx=10, pady=10)
        
        self.lt_entry_out = ctk.CTkEntry(cfg_box, placeholder_text="Output Dir")
        self.lt_entry_out.insert(0, "./long_text_output")
        self.lt_entry_out.pack(fill="x", padx=5, pady=5)
        
        # FFmpeg path - use from settings
        ffmpeg_frame = ctk.CTkFrame(cfg_box, fg_color="transparent")
        ffmpeg_frame.pack(fill="x", padx=5, pady=5)
        
        ctk.CTkLabel(ffmpeg_frame, text="FFmpeg:", width=60).pack(side="left")
        self.lt_entry_ffmpeg = ctk.CTkEntry(ffmpeg_frame, placeholder_text="Path to ffmpeg.exe")
        self.lt_entry_ffmpeg.pack(side="left", fill="x", expand=True, padx=(5, 0))
        self.lt_entry_ffmpeg.insert(0, self.ffmpeg_path)  # Use saved ffmpeg path

        # Chunk size - default 300 chars
        chunk_frame = ctk.CTkFrame(cfg_box, fg_color="transparent")
        chunk_frame.pack(fill="x", padx=5, pady=5)
        
        ctk.CTkLabel(chunk_frame, text="Chunk size:", width=80).pack(side="left")
        self.lt_chunk_size = ctk.CTkEntry(chunk_frame, placeholder_text="Chunk size (300)", width=80)
        self.lt_chunk_size.insert(0, "300")
        self.lt_chunk_size.pack(side="left", padx=(5, 10))
        
        # Ngắt dòng v2 checkbox
        self.lt_sw_chunk_v2 = ctk.CTkSwitch(chunk_frame, text="Ngắt dòng v2 (theo dấu câu)")
        self.lt_sw_chunk_v2.pack(side="left", padx=5)
        if self.lt_chunk_v2_enabled:
            self.lt_sw_chunk_v2.select()

        self.lt_sw_del = ctk.CTkSwitch(cfg_box, text="Delete temp chunks")
        self.lt_sw_del.select()
        self.lt_sw_del.pack(anchor="w", padx=5, pady=5)
        
        # Live Session Mode checkbox - phiên làm việc liên tục như cuộc gọi điện thoại
        self.lt_sw_live_session = ctk.CTkSwitch(cfg_box, text="Session Mode)")
        self.lt_sw_live_session.pack(anchor="w", padx=5, pady=5)
        
        # Keep Voice Beta Mode - giữ giọng ổn định bằng cách wrap text trong {content}
        self.lt_sw_keep_voice_beta = ctk.CTkSwitch(cfg_box, text="Giữ giọng beta")
        self.lt_sw_keep_voice_beta.pack(anchor="w", padx=5, pady=5)

        self.btn_lt_process_files = ctk.CTkButton(cfg_box, text="PROCESS SELECTED FILES", fg_color="#E09F3E", text_color="black", command=self._lt_process_files)
        self.btn_lt_process_files.pack(fill="x", padx=5, pady=10)
        
        self.btn_lt_stop = ctk.CTkButton(cfg_box, text="STOP", fg_color="red", state="disabled", command=self._lt_stop)
        self.btn_lt_stop.pack(fill="x", padx=5, pady=5)

        # Log
        ctk.CTkLabel(right_f, text="Processing Log").pack()
        self.lt_txt_log = ctk.CTkTextbox(right_f, state="disabled", text_color="#E09F3E", font=("Consolas", 10))
        self.lt_txt_log.pack(fill="both", expand=True, padx=10, pady=10)

        self.lt_progress = ctk.CTkProgressBar(right_f)
        self.lt_progress.set(0)
        self.lt_progress.pack(fill="x", padx=10, pady=10)

    # ==========================================================================
    # LOGIC IMPLEMENTATION
    # ==========================================================================
    # ==========================================================================
    # TAB 3: MULTI VOICE (UI ONLY)
    # ==========================================================================
    def _setup_multivoice_tab(self):
        tab = self.tab_multivoice
        
        # Grid Layout: 3 Cột
        # Cột 0: Cấu trúc thô (20%)
        # Cột 1: Script Builder (50%)
        # Cột 2: Voice Settings (30%)
        tab.grid_columnconfigure(0, weight=2)
        tab.grid_columnconfigure(1, weight=5)
        tab.grid_columnconfigure(2, weight=3)
        tab.grid_rowconfigure(0, weight=1)

        # --- CỘT 1: CẤU TRÚC THÔ (Raw structure) ---
        raw_frame = ctk.CTkFrame(tab, fg_color="#1e1e1e", corner_radius=0)
        raw_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 2), pady=0)
       
        
        raw_text_content = """Đang phát triển"""
        
        txt_raw = ctk.CTkTextbox(raw_frame, font=("Consolas", 11), fg_color="#111", text_color="#aaa")
        txt_raw.pack(fill="both", expand=True, padx=10, pady=10)
        txt_raw.insert("1.0", raw_text_content)
        txt_raw.configure(state="disabled")

        # --- CỘT 2: TRÌNH TẠO KỊCH BẢN (Script builder) ---
        builder_frame = ctk.CTkFrame(tab, fg_color="transparent")
        builder_frame.grid(row=0, column=1, sticky="nsew", padx=5, pady=0)
        
        ctk.CTkLabel(builder_frame, text="📝 Trình tạo kịch bản", font=("Roboto", 16, "bold")).pack(anchor="w", pady=(10, 5))

        # Style Instructions
        ctk.CTkLabel(builder_frame, text="Chỉ dẫn phong cách (Style instructions)").pack(anchor="w", pady=(5, 2))
        style_entry = ctk.CTkEntry(builder_frame, placeholder_text="Ví dụ: Đọc to với giọng ấm áp, chào đón", height=35)
        style_entry.insert(0, "Read aloud in a warm, welcoming tone")
        style_entry.pack(fill="x", pady=(0, 15))

        # Scrollable Area for Dialogs
        self.dialog_scroll = ctk.CTkScrollableFrame(builder_frame, label_text="Hội thoại (Dialogs)", fg_color="#2b2b2b")
        self.dialog_scroll.pack(fill="both", expand=True, pady=(0, 10))

        # --- Helper để tạo Blocks hội thoại giả lập ---
        def create_dialog_block(parent, speaker_idx, default_text=""):
            block = ctk.CTkFrame(parent, fg_color="transparent")
            block.pack(fill="x", pady=10)
            
            # Speaker Badge
            colors = {"Speaker 1": "#E67E22", "Speaker 2": "#9B59B6"} # Cam & Tím
            name = f"Speaker {speaker_idx}"
            color = colors.get(name, "gray")
            
            badge_frame = ctk.CTkFrame(block, fg_color="transparent")
            badge_frame.pack(anchor="w", pady=(0, 5))
            
            # Dot indicator
            dot = ctk.CTkLabel(badge_frame, text="●", font=("Arial", 16), text_color=color)
            dot.pack(side="left", padx=(0, 5))
            
            # Label name
            lbl = ctk.CTkLabel(badge_frame, text=f"Người nói {speaker_idx}", font=("Roboto", 12, "bold"), text_color="#ddd")
            lbl.pack(side="left")

            # Text Input
            inp = ctk.CTkTextbox(block, height=60, fg_color="#1a1a1a", border_width=1, border_color="#444")
            inp.pack(fill="x")
            if default_text:
                inp.insert("1.0", default_text)
            else:
                inp.insert("1.0", "Nhập nội dung hội thoại tại đây...")
                inp.configure(text_color="gray")

        # Tạo mẫu dữ liệu giống ảnh
        create_dialog_block(self.dialog_scroll, 1, "Hello! We're excited to show you our native speech capabilities")
        create_dialog_block(self.dialog_scroll, 2, "Where you can direct a voice, create realistic dialog, and so much more. Edit these placeholders to get started.")
        create_dialog_block(self.dialog_scroll, 1) # Empty placeholder
        create_dialog_block(self.dialog_scroll, 2) # Empty placeholder

        # Add Dialog Button
        btn_add = ctk.CTkButton(builder_frame, text="⊕ Thêm hội thoại", fg_color="#333", hover_color="#444", height=35)
        btn_add.pack(fill="x", pady=5)

        # --- CỘT 3: CÀI ĐẶT GIỌNG ĐỌC (Voice settings) ---
        settings_frame = ctk.CTkFrame(tab, fg_color="#1e1e1e", corner_radius=0)
        settings_frame.grid(row=0, column=2, sticky="nsew", padx=(2, 0), pady=0)

        ctk.CTkLabel(settings_frame, text="⚙️ Cài đặt giọng đọc", font=("Roboto", 14, "bold")).pack(anchor="w", padx=15, pady=(15, 10))

        # Scrollable Settings
        setting_scroll = ctk.CTkScrollableFrame(settings_frame, fg_color="transparent")
        setting_scroll.pack(fill="both", expand=True, padx=5)

        # --- Helper tạo block setting cho từng Speaker ---
        def create_speaker_setting(parent, speaker_idx, default_voice):
            colors = {1: "#E67E22", 2: "#9B59B6"} # Cam & Tím
            color = colors.get(speaker_idx, "gray")

            card = ctk.CTkFrame(parent, fg_color="#252525", border_width=1, border_color="#333")
            card.pack(fill="x", pady=10)

            # Header
            header = ctk.CTkFrame(card, fg_color="transparent")
            header.pack(fill="x", padx=10, pady=5)
            
            ctk.CTkLabel(header, text="●", text_color=color).pack(side="left")
            ctk.CTkLabel(header, text=f"Cài đặt Người nói {speaker_idx}", font=("Roboto", 12, "bold")).pack(side="left", padx=5)
            ctk.CTkLabel(header, text="^", text_color="gray").pack(side="right") # Fake collapse icon

            # Content
            content = ctk.CTkFrame(card, fg_color="transparent")
            content.pack(fill="x", padx=10, pady=(0, 10))

            # Name Input
            ctk.CTkLabel(content, text="Tên hiển thị", font=("Roboto", 11), text_color="gray").pack(anchor="w")
            entry_name = ctk.CTkEntry(content, height=30)
            entry_name.insert(0, f"Speaker {speaker_idx}")
            entry_name.pack(fill="x", pady=(2, 10))

            # Voice Select
            ctk.CTkLabel(content, text="Giọng đọc (Voice)", font=("Roboto", 11), text_color="gray").pack(anchor="w")
            combo = ctk.CTkComboBox(content, values=VOICES, height=30)
            combo.set(default_voice)
            combo.pack(fill="x", pady=(2, 5))

        # Tạo mẫu setting giống ảnh 2
        create_speaker_setting(setting_scroll, 1, "Zephyr")
        create_speaker_setting(setting_scroll, 2, "Puck")
        
        # Info note
        ctk.CTkLabel(settings_frame, text="*Tính năng UI Demo, chưa hoạt động.", text_color="gray", font=("Arial", 10)).pack(side="bottom", pady=10)

    # ==========================================================================
    # TAB: CAPCUT VOICE
    # ==========================================================================
    def _setup_capcut_tab(self):
        tab = self.tab_capcut
        tab.grid_columnconfigure(0, weight=3)
        tab.grid_columnconfigure(1, weight=7)
        tab.grid_rowconfigure(0, weight=1)

        # --- LEFT: Controls ---
        left_frame = ctk.CTkFrame(tab, fg_color="#1a1a2e")
        left_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 5), pady=0)

        # Header
        header = ctk.CTkFrame(left_frame, fg_color="#dc2626", height=45)
        header.pack(fill="x")
        ctk.CTkLabel(header, text="🎤 CAPCUT VOICE TTS", font=("Roboto", 14, "bold"), text_color="white").pack(pady=10)

        # Session ID display
        session_frame = ctk.CTkFrame(left_frame, fg_color="transparent")
        session_frame.pack(fill="x", padx=15, pady=10)
        
        ctk.CTkLabel(session_frame, text="Session ID:", font=("Roboto", 11, "bold"), text_color="#f87171").pack(anchor="w")
        self.capcut_session_display = ctk.CTkLabel(session_frame, text="Chưa cài đặt", text_color="gray", font=("Consolas", 10))
        self.capcut_session_display.pack(anchor="w")
        self._update_capcut_session_display()

        # Filter section
        ctk.CTkLabel(left_frame, text="BỘ LỌC GIỌNG", font=("Roboto", 12, "bold"), text_color="#f87171").pack(anchor="w", padx=15, pady=(20, 5))
        
        filter_frame = ctk.CTkFrame(left_frame, fg_color="transparent")
        filter_frame.pack(fill="x", padx=15, pady=5)

        # --- SỬA ĐỔI: Thay ComboBox Ngôn ngữ bằng Scrollable Frame ---
        ctk.CTkLabel(filter_frame, text="Ngôn ngữ:", font=("Roboto", 10)).pack(anchor="w")
        
        # Biến lưu giá trị ngôn ngữ được chọn
        self.capcut_lang_var = ctk.StringVar(value="Tất cả")
        
        # Tạo khung cuộn cho danh sách ngôn ngữ (Chiều cao cố định 120px)
        self.capcut_lang_scroll = ctk.CTkScrollableFrame(filter_frame, height=120, fg_color="#1f2937")
        self.capcut_lang_scroll.pack(fill="x", pady=5)
        
        # Tạo danh sách Radio Button
        for lang in CAPCUT_LANGUAGES:
            ctk.CTkRadioButton(
                self.capcut_lang_scroll, 
                text=lang, 
                variable=self.capcut_lang_var, 
                value=lang,
                command=self._filter_capcut_voices, # Gọi hàm lọc khi click
                font=("Roboto", 11)
            ).pack(anchor="w", pady=2)

        # Giữ nguyên phần lọc giới tính (vì ít option)
        ctk.CTkLabel(filter_frame, text="Giới tính:", font=("Roboto", 10)).pack(anchor="w", pady=(10, 0))
        self.capcut_gender_filter = ctk.CTkComboBox(filter_frame, values=CAPCUT_GENDERS, command=self._filter_capcut_voices)
        self.capcut_gender_filter.set("Tất cả")
        self.capcut_gender_filter.pack(fill="x", pady=5)
        # -----------------------------------------------------------

        # Voice list
        ctk.CTkLabel(left_frame, text="DANH SÁCH GIỌNG", font=("Roboto", 12, "bold"), text_color="#f87171").pack(anchor="w", padx=15, pady=(20, 5))
        
        self.capcut_voice_list = ctk.CTkScrollableFrame(left_frame, fg_color="#111827")
        self.capcut_voice_list.pack(fill="both", expand=True, padx=15, pady=5)
        
        self.capcut_selected_voice = tk.StringVar(value="BV074_streaming")
        self._populate_capcut_voice_list()

        # --- RIGHT: TTS Interface ---
        right_frame = ctk.CTkFrame(tab, fg_color="transparent")
        right_frame.grid(row=0, column=1, sticky="nsew", padx=(5, 0), pady=0)
        right_frame.grid_rowconfigure(1, weight=1)
        right_frame.grid_columnconfigure(0, weight=1)

        # Input section - Text Input
        input_frame = ctk.CTkFrame(right_frame, fg_color="#1a1a2e")
        input_frame.grid(row=0, column=0, sticky="nsew", pady=(0, 5))

        ctk.CTkLabel(input_frame, text="NHẬP VĂN BẢN", font=("Roboto", 14, "bold"), text_color="#f87171").pack(anchor="w", padx=15, pady=(15, 5))
        
        self.capcut_text_input = ctk.CTkTextbox(input_frame, height=80, font=("Roboto", 12))
        self.capcut_text_input.pack(fill="x", padx=15, pady=5)
        self.capcut_text_input.insert("1.0", "Nhập văn bản cần chuyển thành giọng nói...")

        # Control buttons for text
        btn_frame = ctk.CTkFrame(input_frame, fg_color="transparent")
        btn_frame.pack(fill="x", padx=15, pady=5)

        self.btn_capcut_generate = ctk.CTkButton(btn_frame, text="🎙️ TẠO AUDIO", fg_color="#22c55e", font=("Roboto", 12, "bold"), command=self._capcut_generate)
        self.btn_capcut_generate.pack(side="left", padx=5)

        self.btn_capcut_play = ctk.CTkButton(btn_frame, text="▶ PHÁT", fg_color="#3b82f6", state="disabled", command=self._capcut_play)
        self.btn_capcut_play.pack(side="left", padx=5)

        self.btn_capcut_save = ctk.CTkButton(btn_frame, text="💾 LƯU FILE", fg_color="#6366f1", state="disabled", command=self._capcut_save)
        self.btn_capcut_save.pack(side="left", padx=5)

        self.capcut_status_lbl = ctk.CTkLabel(btn_frame, text="Sẵn sàng", text_color="gray")
        self.capcut_status_lbl.pack(side="right", padx=10)

        # SRT/VTT Batch Processing Section
        srt_frame = ctk.CTkFrame(right_frame, fg_color="#1a1a2e")
        srt_frame.grid(row=1, column=0, sticky="nsew", pady=5)

        ctk.CTkLabel(srt_frame, text="📝 TẠO VOICE TỪ FILE SRT/VTT HOẶC THƯ MỤC", font=("Roboto", 14, "bold"), text_color="#f87171").pack(anchor="w", padx=15, pady=(15, 5))

        # File selection
        file_row = ctk.CTkFrame(srt_frame, fg_color="transparent")
        file_row.pack(fill="x", padx=15, pady=5)

        self.capcut_srt_file_entry = ctk.CTkEntry(file_row, placeholder_text="Chọn file SRT/VTT hoặc thư mục chứa txt/docx...", width=300)
        self.capcut_srt_file_entry.pack(side="left", fill="x", expand=True, padx=(0, 5))

        ctk.CTkButton(file_row, text="📂 File", width=60, command=self._capcut_browse_srt).pack(side="left", padx=2)
        ctk.CTkButton(file_row, text="📁 Thư mục", width=80, command=self._capcut_browse_folder).pack(side="left", padx=2)

        # Output folder
        out_row = ctk.CTkFrame(srt_frame, fg_color="transparent")
        out_row.pack(fill="x", padx=15, pady=5)

        self.capcut_srt_output_entry = ctk.CTkEntry(out_row, placeholder_text="Thư mục output...")
        self.capcut_srt_output_entry.insert(0, "./capcut_output")
        self.capcut_srt_output_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))

        ctk.CTkButton(out_row, text="📁 Chọn", width=100, command=self._capcut_browse_output).pack(side="left")

        # Options row - merge option
        opt_row = ctk.CTkFrame(srt_frame, fg_color="transparent")
        opt_row.pack(fill="x", padx=15, pady=5)
        
        self.capcut_merge_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(opt_row, text="Hợp nhất voice sau khi xong (Merge all)", 
                       variable=self.capcut_merge_var, 
                       font=("Roboto", 11)).pack(side="left", padx=5)

        # Process buttons
        proc_btn_row = ctk.CTkFrame(srt_frame, fg_color="transparent")
        proc_btn_row.pack(fill="x", padx=15, pady=10)

        self.btn_capcut_process_srt = ctk.CTkButton(
            proc_btn_row, text="🚀 XỬ LÝ FILE/THƯ MỤC", 
            fg_color="#dc2626", hover_color="#b91c1c",
            font=("Roboto", 12, "bold"), height=40,
            command=self._capcut_process_srt
        )
        self.btn_capcut_process_srt.pack(side="left", padx=5)

        self.btn_capcut_stop_srt = ctk.CTkButton(
            proc_btn_row, text="⏹ DỪNG", 
            fg_color="#64748b", state="disabled",
            command=self._capcut_stop_srt
        )
        self.btn_capcut_stop_srt.pack(side="left", padx=5)
        
        self.btn_capcut_preview = ctk.CTkButton(
            proc_btn_row, text="🔊 Nghe thử", 
            fg_color="#6366f1",
            command=self._capcut_preview_files
        )
        self.btn_capcut_preview.pack(side="left", padx=5)

        # Progress
        self.capcut_srt_progress = ctk.CTkProgressBar(srt_frame)
        self.capcut_srt_progress.set(0)
        self.capcut_srt_progress.pack(fill="x", padx=15, pady=5)

        self.capcut_srt_status = ctk.CTkLabel(srt_frame, text="Sẵn sàng xử lý", text_color="gray")
        self.capcut_srt_status.pack(anchor="w", padx=15, pady=(0, 10))

        # Log section
        log_frame = ctk.CTkFrame(right_frame, fg_color="#0f0f1a")
        log_frame.grid(row=2, column=0, sticky="nsew")

        ctk.CTkLabel(log_frame, text="LOG", font=("Roboto", 12, "bold"), text_color="#f87171").pack(anchor="w", padx=15, pady=(10, 5))
        self.capcut_log = ctk.CTkTextbox(log_frame, font=("Consolas", 10), text_color="#22c55e", state="disabled")
        self.capcut_log.pack(fill="both", expand=True, padx=15, pady=(0, 15))

        # Update row weights
        right_frame.grid_rowconfigure(2, weight=1)

        # Store temp audio path
        self.capcut_temp_audio = None
        self.capcut_srt_processing = False

    # ==========================================================================
    # TAB: EDGE TTS
    # ==========================================================================
    def _setup_edge_tab(self):
        tab = self.tab_edge
        tab.grid_columnconfigure(0, weight=3)
        tab.grid_columnconfigure(1, weight=7)
        tab.grid_rowconfigure(0, weight=1)

        # --- LEFT: Voice Selection ---
        left_frame = ctk.CTkFrame(tab, fg_color="#0f172a")
        left_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 5), pady=0)

        # Header
        header = ctk.CTkFrame(left_frame, fg_color="#2563eb", height=45)
        header.pack(fill="x")
        ctk.CTkLabel(header, text="🔊 EDGE TTS (Microsoft)", font=("Roboto", 14, "bold"), text_color="white").pack(pady=10)

        # Refresh button
        btn_refresh = ctk.CTkButton(left_frame, text="🔄 Tải Voice List", fg_color="#1d4ed8", command=self._load_edge_voices)
        btn_refresh.pack(fill="x", padx=15, pady=10)

        self.edge_voice_count_lbl = ctk.CTkLabel(left_frame, text="Voices: 0", text_color="gray")
        self.edge_voice_count_lbl.pack(anchor="w", padx=15)

        # Filter section
        ctk.CTkLabel(left_frame, text="BỘ LỌC", font=("Roboto", 12, "bold"), text_color="#60a5fa").pack(anchor="w", padx=15, pady=(20, 5))
        
        filter_frame = ctk.CTkFrame(left_frame, fg_color="transparent")
        filter_frame.pack(fill="x", padx=15, pady=5)

        # --- SỬA ĐỔI: Thay ComboBox Ngôn ngữ bằng Scrollable Frame ---
        ctk.CTkLabel(filter_frame, text="Ngôn ngữ:", font=("Roboto", 10)).pack(anchor="w")
        
        # Biến lưu giá trị ngôn ngữ Edge TTS
        self.edge_lang_var = ctk.StringVar(value="Tất cả")
        
        # Tạo khung cuộn cho danh sách ngôn ngữ (Chiều cao cố định 150px vì danh sách này dài)
        self.edge_lang_scroll = ctk.CTkScrollableFrame(filter_frame, height=150, fg_color="#1e293b")
        self.edge_lang_scroll.pack(fill="x", pady=5)
        
        # Tạo danh sách Radio Button cho Edge TTS
        for lang_name in EDGE_TTS_LANGUAGES:
            ctk.CTkRadioButton(
                self.edge_lang_scroll,
                text=lang_name,
                variable=self.edge_lang_var,
                value=lang_name,
                command=self._filter_edge_voices, # Gọi hàm lọc khi click
                font=("Roboto", 11)
            ).pack(anchor="w", pady=2)

        # Giữ nguyên phần lọc giới tính
        ctk.CTkLabel(filter_frame, text="Giới tính:", font=("Roboto", 10)).pack(anchor="w", pady=(10, 0))
        self.edge_gender_filter = ctk.CTkComboBox(filter_frame, values=EDGE_TTS_GENDERS, command=self._filter_edge_voices)
        self.edge_gender_filter.set("Tất cả")
        self.edge_gender_filter.pack(fill="x", pady=5)
        # -----------------------------------------------------------

        # Voice list
        ctk.CTkLabel(left_frame, text="DANH SÁCH GIỌNG", font=("Roboto", 12, "bold"), text_color="#60a5fa").pack(anchor="w", padx=15, pady=(20, 5))
        self.edge_voice_list = ctk.CTkScrollableFrame(left_frame, fg_color="#1e293b")
        self.edge_voice_list.pack(fill="both", expand=True, padx=15, pady=5)
        
        self.edge_selected_voice = tk.StringVar(value="en-US-EmmaMultilingualNeural")

        # --- RIGHT: TTS Interface ---
        right_frame = ctk.CTkFrame(tab, fg_color="transparent")
        right_frame.grid(row=0, column=1, sticky="nsew", padx=(5, 0), pady=0)
        right_frame.grid_rowconfigure(1, weight=1)
        right_frame.grid_columnconfigure(0, weight=1)

        # Input section - Text Input
        input_frame = ctk.CTkFrame(right_frame, fg_color="#0f172a")
        input_frame.grid(row=0, column=0, sticky="nsew", pady=(0, 5))

        ctk.CTkLabel(input_frame, text="NHẬP VĂN BẢN", font=("Roboto", 14, "bold"), text_color="#60a5fa").pack(anchor="w", padx=15, pady=(15, 5))
        
        self.edge_text_input = ctk.CTkTextbox(input_frame, height=80, font=("Roboto", 12))
        self.edge_text_input.pack(fill="x", padx=15, pady=5)
        self.edge_text_input.insert("1.0", "Enter text to convert to speech...")

        # Voice settings
        settings_row = ctk.CTkFrame(input_frame, fg_color="transparent")
        settings_row.pack(fill="x", padx=15, pady=5)

        ctk.CTkLabel(settings_row, text="Rate:").pack(side="left")
        self.edge_rate = ctk.CTkEntry(settings_row, width=70, placeholder_text="+0%")
        self.edge_rate.insert(0, "+0%")
        self.edge_rate.pack(side="left", padx=5)

        ctk.CTkLabel(settings_row, text="Volume:").pack(side="left", padx=(15, 0))
        self.edge_volume = ctk.CTkEntry(settings_row, width=70, placeholder_text="+0%")
        self.edge_volume.insert(0, "+0%")
        self.edge_volume.pack(side="left", padx=5)

        ctk.CTkLabel(settings_row, text="Pitch:").pack(side="left", padx=(15, 0))
        self.edge_pitch = ctk.CTkEntry(settings_row, width=70, placeholder_text="+0Hz")
        self.edge_pitch.insert(0, "+0Hz")
        self.edge_pitch.pack(side="left", padx=5)

        # Control buttons
        btn_frame = ctk.CTkFrame(input_frame, fg_color="transparent")
        btn_frame.pack(fill="x", padx=15, pady=5)

        self.btn_edge_generate = ctk.CTkButton(btn_frame, text="🎙️ TẠO AUDIO", fg_color="#22c55e", font=("Roboto", 12, "bold"), command=self._edge_generate)
        self.btn_edge_generate.pack(side="left", padx=5)

        self.btn_edge_play = ctk.CTkButton(btn_frame, text="▶ PHÁT", fg_color="#3b82f6", state="disabled", command=self._edge_play)
        self.btn_edge_play.pack(side="left", padx=5)

        self.btn_edge_save = ctk.CTkButton(btn_frame, text="💾 LƯU FILE", fg_color="#6366f1", state="disabled", command=self._edge_save)
        self.btn_edge_save.pack(side="left", padx=5)

        self.edge_status_lbl = ctk.CTkLabel(btn_frame, text="Sẵn sàng", text_color="gray")
        self.edge_status_lbl.pack(side="right", padx=10)

        # SRT/VTT Batch Processing Section
        srt_frame = ctk.CTkFrame(right_frame, fg_color="#0f172a")
        srt_frame.grid(row=1, column=0, sticky="nsew", pady=5)

        ctk.CTkLabel(srt_frame, text="📝 TẠO VOICE TỪ FILE SRT/VTT HOẶC THƯ MỤC", font=("Roboto", 14, "bold"), text_color="#60a5fa").pack(anchor="w", padx=15, pady=(15, 5))

        # File selection
        file_row = ctk.CTkFrame(srt_frame, fg_color="transparent")
        file_row.pack(fill="x", padx=15, pady=5)

        self.edge_srt_file_entry = ctk.CTkEntry(file_row, placeholder_text="Chọn file SRT/VTT hoặc thư mục...", width=300)
        self.edge_srt_file_entry.pack(side="left", fill="x", expand=True, padx=(0, 5))

        ctk.CTkButton(file_row, text="📂 File", width=60, command=self._edge_browse_srt).pack(side="left", padx=2)
        ctk.CTkButton(file_row, text="📁 Thư mục", width=80, command=self._edge_browse_folder).pack(side="left", padx=2)

        # Output folder
        out_row = ctk.CTkFrame(srt_frame, fg_color="transparent")
        out_row.pack(fill="x", padx=15, pady=5)

        self.edge_srt_output_entry = ctk.CTkEntry(out_row, placeholder_text="Thư mục output...")
        self.edge_srt_output_entry.insert(0, "./edge_output")
        self.edge_srt_output_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))

        ctk.CTkButton(out_row, text="📁 Chọn", width=100, command=self._edge_browse_output).pack(side="left")

        # Options row
        opt_row = ctk.CTkFrame(srt_frame, fg_color="transparent")
        opt_row.pack(fill="x", padx=15, pady=5)

        ctk.CTkLabel(opt_row, text="Workers:").pack(side="left")
        self.edge_workers_var = tk.StringVar(value="10")
        ctk.CTkEntry(opt_row, textvariable=self.edge_workers_var, width=60).pack(side="left", padx=5)
        
        self.edge_merge_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(opt_row, text="Hợp nhất voice sau khi xong", 
                       variable=self.edge_merge_var, 
                       font=("Roboto", 11)).pack(side="left", padx=15)

        # Process buttons
        proc_btn_row = ctk.CTkFrame(srt_frame, fg_color="transparent")
        proc_btn_row.pack(fill="x", padx=15, pady=10)

        self.btn_edge_process_srt = ctk.CTkButton(
            proc_btn_row, text="🚀 XỬ LÝ FILE/THƯ MỤC", 
            fg_color="#2563eb", hover_color="#1d4ed8",
            font=("Roboto", 12, "bold"), height=40,
            command=self._edge_process_srt
        )
        self.btn_edge_process_srt.pack(side="left", padx=5)

        self.btn_edge_stop_srt = ctk.CTkButton(
            proc_btn_row, text="⏹ DỪNG", 
            fg_color="#64748b", state="disabled",
            command=self._edge_stop_srt
        )
        self.btn_edge_stop_srt.pack(side="left", padx=5)
        
        self.btn_edge_preview = ctk.CTkButton(
            proc_btn_row, text="🔊 Nghe thử", 
            fg_color="#6366f1",
            command=self._edge_preview_files
        )
        self.btn_edge_preview.pack(side="left", padx=5)

        # Progress
        self.edge_srt_progress = ctk.CTkProgressBar(srt_frame)
        self.edge_srt_progress.set(0)
        self.edge_srt_progress.pack(fill="x", padx=15, pady=5)

        self.edge_srt_status = ctk.CTkLabel(srt_frame, text="Sẵn sàng xử lý", text_color="gray")
        self.edge_srt_status.pack(anchor="w", padx=15, pady=(0, 10))

        # Log section
        log_frame = ctk.CTkFrame(right_frame, fg_color="#020617")
        log_frame.grid(row=2, column=0, sticky="nsew")

        ctk.CTkLabel(log_frame, text="LOG", font=("Roboto", 12, "bold"), text_color="#60a5fa").pack(anchor="w", padx=15, pady=(10, 5))
        self.edge_log = ctk.CTkTextbox(log_frame, font=("Consolas", 10), text_color="#22c55e", state="disabled")
        self.edge_log.pack(fill="both", expand=True, padx=15, pady=(0, 15))

        # Update row weights
        right_frame.grid_rowconfigure(2, weight=1)
        
        # Store state
        self.edge_srt_processing = False

        # Store temp audio path
        self.edge_temp_audio = None
        
        # Auto-load voices
        self.after(500, self._load_edge_voices)

    # ==========================================================================
    # TAB: VIENEU-TTS (Vietnamese Neural TTS with Voice Cloning)
    # ==========================================================================
    def _setup_vieneu_tab(self):
        """Setup the VN TTS tab - Vietnamese TTS with voice cloning"""
        tab = self.tab_vieneu
        tab.grid_columnconfigure(0, weight=3)
        tab.grid_columnconfigure(1, weight=7)
        tab.grid_rowconfigure(0, weight=1)
        
        # Initialize VN TTS state variables
        self.vieneu_tts_instance = None
        self.vieneu_model_loaded = False
        self.vieneu_using_fast = False
        self.vieneu_ref_codes = None
        self.vieneu_ref_text = ""
        self.vieneu_temp_audio = None
        self.vieneu_processing = False
        self.vieneu_custom_ref_audio = None
        self.vieneu_custom_ref_text = ""

        # --- LEFT: Model & Voice Selection ---
        left_frame = ctk.CTkFrame(tab, fg_color="#0d1117")
        left_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 5), pady=0)

        # Header
        header = ctk.CTkFrame(left_frame, fg_color="#6366f1", height=45)
        header.pack(fill="x")
        ctk.CTkLabel(header, text="🇻🇳 VN TTS", font=("Roboto", 14, "bold"), text_color="white").pack(pady=10)
        
        # Scrollable content
        content_scroll = ctk.CTkScrollableFrame(left_frame, fg_color="transparent")
        content_scroll.pack(fill="both", expand=True, padx=5, pady=5)

        # ===== MODEL CONFIGURATION SECTION =====
        ctk.CTkLabel(content_scroll, text="⚙️ CẤU HÌNH MODEL", font=("Roboto", 12, "bold"), text_color="#818cf8").pack(anchor="w", padx=10, pady=(10, 5))
        
        model_frame = ctk.CTkFrame(content_scroll, fg_color="#1f2937")
        model_frame.pack(fill="x", padx=10, pady=5)
        
        # Backbone selection
        ctk.CTkLabel(model_frame, text="Backbone Model:", font=("Roboto", 10)).pack(anchor="w", padx=10, pady=(10, 2))
        self.vieneu_backbone_var = ctk.StringVar(value="VN TTS Q4 (Nhanh)")
        self.vieneu_backbone_combo = ctk.CTkComboBox(
            model_frame, 
            values=list(VIENEU_BACKBONE_CONFIGS.keys()),
            variable=self.vieneu_backbone_var,
            command=self._vieneu_on_backbone_change
        )
        self.vieneu_backbone_combo.pack(fill="x", padx=10, pady=2)
        
        # Backbone description
        self.vieneu_backbone_desc = ctk.CTkLabel(
            model_frame, 
            text=VIENEU_BACKBONE_CONFIGS["VN TTS Q4 (Nhanh)"]["description"],
            font=("Roboto", 9), text_color="gray"
        )
        self.vieneu_backbone_desc.pack(anchor="w", padx=10, pady=2)
        
        # Codec selection
        ctk.CTkLabel(model_frame, text="Audio Codec:", font=("Roboto", 10)).pack(anchor="w", padx=10, pady=(10, 2))
        self.vieneu_codec_var = ctk.StringVar(value="NeuCodec (Standard)")
        self.vieneu_codec_combo = ctk.CTkComboBox(
            model_frame, 
            values=list(VIENEU_CODEC_CONFIGS.keys()),
            variable=self.vieneu_codec_var
        )
        self.vieneu_codec_combo.pack(fill="x", padx=10, pady=2)
        
        # Device selection
        ctk.CTkLabel(model_frame, text="Device:", font=("Roboto", 10)).pack(anchor="w", padx=10, pady=(10, 2))
        self.vieneu_device_var = ctk.StringVar(value="Auto")
        device_frame = ctk.CTkFrame(model_frame, fg_color="transparent")
        device_frame.pack(fill="x", padx=10, pady=2)
        
        ctk.CTkRadioButton(device_frame, text="Auto", variable=self.vieneu_device_var, value="Auto").pack(side="left", padx=5)
        ctk.CTkRadioButton(device_frame, text="CPU", variable=self.vieneu_device_var, value="CPU").pack(side="left", padx=5)
        ctk.CTkRadioButton(device_frame, text="CUDA (GPU)", variable=self.vieneu_device_var, value="CUDA").pack(side="left", padx=5)
        
        # Advanced options
        adv_frame = ctk.CTkFrame(model_frame, fg_color="transparent")
        adv_frame.pack(fill="x", padx=10, pady=5)
        
        self.vieneu_triton_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(adv_frame, text="Enable Triton (GPU)", variable=self.vieneu_triton_var, font=("Roboto", 10)).pack(side="left", padx=5)
        
        ctk.CTkLabel(adv_frame, text="Max Batch:", font=("Roboto", 10)).pack(side="left", padx=(15, 5))
        self.vieneu_batch_var = ctk.StringVar(value="8")
        ctk.CTkEntry(adv_frame, textvariable=self.vieneu_batch_var, width=50).pack(side="left")
        
        # GPU Memory optimization slider
        gpu_opt_frame = ctk.CTkFrame(model_frame, fg_color="transparent")
        gpu_opt_frame.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkLabel(gpu_opt_frame, text="GPU Memory:", font=("Roboto", 10)).pack(side="left", padx=5)
        # Slider from 30% to 80% GPU memory, steps of 10% (30, 40, 50, 60, 70, 80)
        self.vieneu_memory_slider = ctk.CTkSlider(gpu_opt_frame, from_=0.3, to=0.8, number_of_steps=5, width=100)
        self.vieneu_memory_slider.set(0.5)  # Default to 50%
        self.vieneu_memory_slider.pack(side="left", padx=5)
        self.vieneu_memory_lbl = ctk.CTkLabel(gpu_opt_frame, text="50%", font=("Roboto", 9), width=35)
        self.vieneu_memory_lbl.pack(side="left")
        self.vieneu_memory_slider.configure(command=lambda v: self.vieneu_memory_lbl.configure(text=f"{int(round(v*100))}%"))
        
        # Load model button
        self.btn_vieneu_load = ctk.CTkButton(
            model_frame, 
            text="🔄 TẢI MODEL", 
            fg_color="#6366f1", 
            hover_color="#4f46e5",
            command=self._vieneu_load_model
        )
        self.btn_vieneu_load.pack(fill="x", padx=10, pady=10)
        
        # Model status
        self.vieneu_model_status = ctk.CTkLabel(
            model_frame, 
            text="⏳ Model chưa được tải", 
            font=("Roboto", 10), 
            text_color="#fbbf24",
            wraplength=250
        )
        self.vieneu_model_status.pack(anchor="w", padx=10, pady=(0, 10))

        # ===== VOICE SELECTION SECTION =====
        ctk.CTkLabel(content_scroll, text="🎤 CHỌN GIỌNG NÓI", font=("Roboto", 12, "bold"), text_color="#818cf8").pack(anchor="w", padx=10, pady=(15, 5))
        
        voice_frame = ctk.CTkFrame(content_scroll, fg_color="#1f2937")
        voice_frame.pack(fill="x", padx=10, pady=5)
        
        # Voice mode tabs
        self.vieneu_voice_mode = ctk.StringVar(value="preset")
        mode_frame = ctk.CTkFrame(voice_frame, fg_color="transparent")
        mode_frame.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkRadioButton(
            mode_frame, text="Giọng mẫu có sẵn", 
            variable=self.vieneu_voice_mode, value="preset",
            command=self._vieneu_on_voice_mode_change
        ).pack(side="left", padx=5)
        ctk.CTkRadioButton(
            mode_frame, text="Clone giọng mới", 
            variable=self.vieneu_voice_mode, value="custom",
            command=self._vieneu_on_voice_mode_change
        ).pack(side="left", padx=5)
        
        # Preset voice list
        self.vieneu_preset_frame = ctk.CTkFrame(voice_frame, fg_color="transparent")
        self.vieneu_preset_frame.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkLabel(self.vieneu_preset_frame, text="Chọn giọng:", font=("Roboto", 10)).pack(anchor="w")
        
        self.vieneu_voice_list = ctk.CTkScrollableFrame(self.vieneu_preset_frame, height=150, fg_color="#111827")
        self.vieneu_voice_list.pack(fill="x", pady=5)
        
        self.vieneu_selected_voice = ctk.StringVar(value="Vĩnh (nam miền Nam)")
        self._vieneu_populate_voice_list()
        
        # Preview preset voice
        self.btn_vieneu_preview_preset = ctk.CTkButton(
            self.vieneu_preset_frame,
            text="▶ Nghe thử giọng mẫu",
            fg_color="#3b82f6",
            command=self._vieneu_preview_preset_voice
        )
        self.btn_vieneu_preview_preset.pack(fill="x", pady=5)
        
        # Custom voice (voice cloning) frame
        self.vieneu_custom_frame = ctk.CTkFrame(voice_frame, fg_color="transparent")
        # Hidden by default
        
        ctk.CTkLabel(self.vieneu_custom_frame, text="📂 Upload file audio mẫu (.wav):", font=("Roboto", 10)).pack(anchor="w", pady=(5, 2))
        
        custom_audio_row = ctk.CTkFrame(self.vieneu_custom_frame, fg_color="transparent")
        custom_audio_row.pack(fill="x", pady=2)
        
        self.vieneu_custom_audio_entry = ctk.CTkEntry(custom_audio_row, placeholder_text="Chọn file audio...")
        self.vieneu_custom_audio_entry.pack(side="left", fill="x", expand=True, padx=(0, 5))
        
        ctk.CTkButton(custom_audio_row, text="📂", width=40, command=self._vieneu_browse_custom_audio).pack(side="left")
        
        ctk.CTkLabel(self.vieneu_custom_frame, text="📝 Nội dung lời thoại mẫu:", font=("Roboto", 10)).pack(anchor="w", pady=(10, 2))
        self.vieneu_custom_text_input = ctk.CTkTextbox(self.vieneu_custom_frame, height=80, font=("Roboto", 11))
        self.vieneu_custom_text_input.pack(fill="x", pady=2)
        self.vieneu_custom_text_input.insert("1.0", "Nhập nội dung lời thoại trong file audio mẫu...")
        
        self.btn_vieneu_encode_custom = ctk.CTkButton(
            self.vieneu_custom_frame,
            text="🔧 Mã hóa giọng mẫu",
            fg_color="#8b5cf6",
            command=self._vieneu_encode_custom_voice
        )
        self.btn_vieneu_encode_custom.pack(fill="x", pady=10)
        
        # Voice name entry for saving
        save_voice_frame = ctk.CTkFrame(self.vieneu_custom_frame, fg_color="transparent")
        save_voice_frame.pack(fill="x", pady=(5, 2))
        
        ctk.CTkLabel(save_voice_frame, text="💾 Lưu giọng với tên:", font=("Roboto", 10)).pack(side="left", padx=(0, 5))
        self.vieneu_save_voice_name = ctk.CTkEntry(save_voice_frame, placeholder_text="Tên giọng (VD: Hùng nam miền Bắc)", width=180)
        self.vieneu_save_voice_name.pack(side="left", fill="x", expand=True)
        
        self.btn_vieneu_save_voice = ctk.CTkButton(
            self.vieneu_custom_frame,
            text="💾 LƯU GIỌNG VÀO DANH SÁCH",
            fg_color="#f59e0b",
            hover_color="#d97706",
            state="disabled",
            command=self._vieneu_save_cloned_voice
        )
        self.btn_vieneu_save_voice.pack(fill="x", pady=5)
        
        self.vieneu_custom_status = ctk.CTkLabel(
            self.vieneu_custom_frame,
            text="",
            font=("Roboto", 9),
            text_color="gray"
        )
        self.vieneu_custom_status.pack(anchor="w")
        
        # Clone Voice button - appears after encoding
        self.btn_vieneu_clone_now = ctk.CTkButton(
            self.vieneu_custom_frame,
            text="🎙️ TẠO AUDIO VỚI GIỌNG ĐÃ CLONE",
            fg_color="#22c55e",
            hover_color="#16a34a",
            font=("Roboto", 12, "bold"),
            state="disabled",
            command=self._vieneu_generate
        )
        self.btn_vieneu_clone_now.pack(fill="x", pady=(10, 5))
        
        # Instruction label - initially hidden, shown after encoding
        self.vieneu_clone_instruction = ctk.CTkLabel(
            self.vieneu_custom_frame,
            text="📌 Bước tiếp theo: Nhập văn bản ở bên phải → Bấm nút trên để tạo audio",
            font=("Roboto", 9),
            text_color="#94a3b8",
            wraplength=280
        )
        # Don't pack yet - will be shown after encoding completes

        # --- RIGHT: TTS Interface ---
        right_frame = ctk.CTkFrame(tab, fg_color="transparent")
        right_frame.grid(row=0, column=1, sticky="nsew", padx=(5, 0), pady=0)
        right_frame.grid_rowconfigure(1, weight=1)
        right_frame.grid_columnconfigure(0, weight=1)

        # Text Input Section
        input_frame = ctk.CTkFrame(right_frame, fg_color="#0d1117")
        input_frame.grid(row=0, column=0, sticky="nsew", pady=(0, 5))

        ctk.CTkLabel(input_frame, text="📝 NHẬP VĂN BẢN CẦN ĐỌC", font=("Roboto", 14, "bold"), text_color="#818cf8").pack(anchor="w", padx=15, pady=(15, 5))
        
        self.vieneu_text_input = ctk.CTkTextbox(input_frame, height=120, font=("Roboto", 12))
        self.vieneu_text_input.pack(fill="x", padx=15, pady=5)
        self.vieneu_text_input.insert("1.0", "Hà Nội, trái tim của Việt Nam, là một thành phố ngàn năm văn hiến với bề dày lịch sử và văn hóa độc đáo. Bước chân trên những con phố cổ kính quanh Hồ Hoàn Kiếm, du khách như được du hành ngược thời gian.")
        
        # Character count
        char_frame = ctk.CTkFrame(input_frame, fg_color="transparent")
        char_frame.pack(fill="x", padx=15)
        self.vieneu_char_count = ctk.CTkLabel(char_frame, text="Ký tự: 0", text_color="gray", font=("Roboto", 10))
        self.vieneu_char_count.pack(side="right")
        self.vieneu_text_input.bind("<KeyRelease>", self._vieneu_update_char_count)
        self._vieneu_update_char_count()

        # Control buttons
        btn_frame = ctk.CTkFrame(input_frame, fg_color="transparent")
        btn_frame.pack(fill="x", padx=15, pady=10)

        self.btn_vieneu_generate = ctk.CTkButton(
            btn_frame, 
            text="🎙️ TẠO AUDIO", 
            fg_color="#22c55e", 
            hover_color="#16a34a",
            font=("Roboto", 12, "bold"), 
            state="disabled",
            command=self._vieneu_generate
        )
        self.btn_vieneu_generate.pack(side="left", padx=5)

        self.btn_vieneu_play = ctk.CTkButton(
            btn_frame, 
            text="▶ PHÁT", 
            fg_color="#3b82f6", 
            state="disabled", 
            command=self._vieneu_play
        )
        self.btn_vieneu_play.pack(side="left", padx=5)

        self.btn_vieneu_stop = ctk.CTkButton(
            btn_frame, 
            text="⏹ DỪNG", 
            fg_color="#ef4444", 
            command=self._vieneu_stop_playback
        )
        self.btn_vieneu_stop.pack(side="left", padx=5)

        self.btn_vieneu_save = ctk.CTkButton(
            btn_frame, 
            text="💾 LƯU FILE", 
            fg_color="#6366f1", 
            state="disabled", 
            command=self._vieneu_save
        )
        self.btn_vieneu_save.pack(side="left", padx=5)

        # Streaming option (GPU only) - disabled by default, enabled after GPU model loads
        self.vieneu_streaming_var = ctk.BooleanVar(value=False)
        self.vieneu_streaming_cb = ctk.CTkCheckBox(
            btn_frame, 
            text="⚡ Streaming (GPU)", 
            variable=self.vieneu_streaming_var,
            font=("Roboto", 10),
            state="disabled"  # Will be enabled when GPU model is loaded
        )
        self.vieneu_streaming_cb.pack(side="left", padx=10)

        self.vieneu_status_lbl = ctk.CTkLabel(btn_frame, text="Sẵn sàng", text_color="gray")
        self.vieneu_status_lbl.pack(side="right", padx=10)

        # File Processing Section
        file_frame = ctk.CTkFrame(right_frame, fg_color="#0d1117")
        file_frame.grid(row=1, column=0, sticky="nsew", pady=5)

        ctk.CTkLabel(file_frame, text="📁 XỬ LÝ FILE HÀNG LOẠT", font=("Roboto", 14, "bold"), text_color="#818cf8").pack(anchor="w", padx=15, pady=(15, 5))

        # File selection
        file_row = ctk.CTkFrame(file_frame, fg_color="transparent")
        file_row.pack(fill="x", padx=15, pady=5)

        self.vieneu_file_entry = ctk.CTkEntry(file_row, placeholder_text="Chọn file SRT/TXT/DOCX...")
        self.vieneu_file_entry.pack(side="left", fill="x", expand=True, padx=(0, 5))

        ctk.CTkButton(file_row, text="📂 Chọn file", width=100, command=self._vieneu_browse_file).pack(side="left", padx=2)
        ctk.CTkButton(file_row, text="📁 Thư mục", width=100, command=self._vieneu_browse_folder).pack(side="left", padx=2)

        # Output folder
        out_row = ctk.CTkFrame(file_frame, fg_color="transparent")
        out_row.pack(fill="x", padx=15, pady=5)

        self.vieneu_output_entry = ctk.CTkEntry(out_row, placeholder_text="Thư mục output...")
        self.vieneu_output_entry.insert(0, "./vieneu_output")
        self.vieneu_output_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))

        ctk.CTkButton(out_row, text="📁 Chọn", width=100, command=self._vieneu_browse_output).pack(side="left")

        # Options
        opt_row = ctk.CTkFrame(file_frame, fg_color="transparent")
        opt_row.pack(fill="x", padx=15, pady=5)
        
        self.vieneu_merge_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(opt_row, text="Hợp nhất voice", variable=self.vieneu_merge_var, font=("Roboto", 11)).pack(side="left", padx=5)
        
        self.vieneu_delete_chunks_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(opt_row, text="Xóa chunks sau khi ghép", variable=self.vieneu_delete_chunks_var, font=("Roboto", 11)).pack(side="left", padx=15)

        # Process buttons
        proc_btn_row = ctk.CTkFrame(file_frame, fg_color="transparent")
        proc_btn_row.pack(fill="x", padx=15, pady=10)

        self.btn_vieneu_process = ctk.CTkButton(
            proc_btn_row, 
            text="🚀 XỬ LÝ FILE", 
            fg_color="#6366f1", 
            hover_color="#4f46e5",
            font=("Roboto", 12, "bold"), 
            height=40,
            state="disabled",
            command=self._vieneu_process_file
        )
        self.btn_vieneu_process.pack(side="left", padx=5)

        self.btn_vieneu_stop_process = ctk.CTkButton(
            proc_btn_row, 
            text="⏹ DỪNG", 
            fg_color="#64748b", 
            state="disabled",
            command=self._vieneu_stop_processing
        )
        self.btn_vieneu_stop_process.pack(side="left", padx=5)

        # Progress
        self.vieneu_progress = ctk.CTkProgressBar(file_frame)
        self.vieneu_progress.set(0)
        self.vieneu_progress.pack(fill="x", padx=15, pady=5)

        self.vieneu_file_status = ctk.CTkLabel(file_frame, text="Sẵn sàng xử lý", text_color="gray")
        self.vieneu_file_status.pack(anchor="w", padx=15, pady=(0, 10))

        # Log section
        log_frame = ctk.CTkFrame(right_frame, fg_color="#020617")
        log_frame.grid(row=2, column=0, sticky="nsew")

        ctk.CTkLabel(log_frame, text="LOG", font=("Roboto", 12, "bold"), text_color="#818cf8").pack(anchor="w", padx=15, pady=(10, 5))
        self.vieneu_log = ctk.CTkTextbox(log_frame, font=("Consolas", 10), text_color="#22c55e", state="disabled")
        self.vieneu_log.pack(fill="both", expand=True, padx=15, pady=(0, 15))

        # Update row weights
        right_frame.grid_rowconfigure(2, weight=1)

    # ==========================================================================
    # VIENEU-TTS HELPER METHODS
    # ==========================================================================
    def _vieneu_log(self, msg):
        """Add message to VN TTS log"""
        self.vieneu_log.configure(state="normal")
        self.vieneu_log.insert("end", f"[{time.strftime('%H:%M:%S')}] {msg}\n")
        self.vieneu_log.see("end")
        self.vieneu_log.configure(state="disabled")

    def _vieneu_progress_log(self, percent: int, note: str = ""):
        """Log VN TTS loading progress to stdout and UI as percentage."""
        safe_percent = max(0, min(100, percent))
        message = f"VN TTS {safe_percent}%"
        if note:
            message = f"{message} - {note}"
        def _apply():
            print(message, flush=True)
            self.vieneu_progress.set(safe_percent / 100)
            self._vieneu_log(message)
        self.after(0, _apply)

    @classmethod
    def _sanitize_error_message(cls, message: str) -> str:
        """Hide external links and paths from error output."""
        clean = cls.SANITIZE_URL_PATTERN.sub(" ", message or "")
        clean = " ".join(clean.split())
        return clean or cls.SANITIZED_ERROR_FALLBACK

    def _vieneu_on_backbone_change(self, value):
        """Handle backbone model selection change"""
        config = VIENEU_BACKBONE_CONFIGS.get(value, {})
        self.vieneu_backbone_desc.configure(text=config.get("description", ""))
        
        # Update voice list for GGUF models (limited voices)
        self._vieneu_populate_voice_list()
        
    def _vieneu_on_voice_mode_change(self):
        """Handle voice mode change (preset vs custom)"""
        mode = self.vieneu_voice_mode.get()
        if mode == "preset":
            self.vieneu_preset_frame.pack(fill="x", padx=10, pady=5)
            self.vieneu_custom_frame.pack_forget()
        else:
            self.vieneu_preset_frame.pack_forget()
            self.vieneu_custom_frame.pack(fill="x", padx=10, pady=5)
            # Reset clone button state if voice was not encoded yet
            if self.vieneu_ref_codes is None:
                self.btn_vieneu_clone_now.configure(state="disabled")
                # Hide instruction if visible
                try:
                    self.vieneu_clone_instruction.pack_forget()
                except Exception:
                    pass  # Ignore if not packed

    def _vieneu_populate_voice_list(self):
        """Populate the voice list based on selected backbone"""
        # Clear existing
        for widget in self.vieneu_voice_list.winfo_children():
            widget.destroy()
        
        backbone = self.vieneu_backbone_var.get()
        
        # GGUF models only support 4 voices
        if "gguf" in backbone.lower():
            available_voices = [v for v in VIENEU_GGUF_ALLOWED_VOICES if v in VIENEU_VOICE_SAMPLES]
        else:
            available_voices = list(VIENEU_VOICE_SAMPLES.keys())
        
        for voice_name in available_voices:
            voice_info = VIENEU_VOICE_SAMPLES.get(voice_name, {})
            gender = voice_info.get("gender", "")
            accent = voice_info.get("accent", "")
            display = f"{voice_name}"
            
            rb = ctk.CTkRadioButton(
                self.vieneu_voice_list,
                text=display,
                variable=self.vieneu_selected_voice,
                value=voice_name,
                font=("Roboto", 10)
            )
            rb.pack(anchor="w", pady=2, padx=5)

    def _vieneu_update_char_count(self, event=None):
        """Update character count for VN TTS text input"""
        text = self.vieneu_text_input.get("1.0", "end").strip()
        count = len(text)
        self.vieneu_char_count.configure(text=f"Ký tự: {count}")

    def _vieneu_validate_voice_settings(self):
        """
        Validate voice settings before generating.
        Returns (success, voice_mode, voice_name, error_message) tuple.
        If success is False, error_message contains the error to show.
        """
        voice_mode = self.vieneu_voice_mode.get()
        self._vieneu_log(f"📋 Chế độ giọng: {voice_mode}")
        
        if voice_mode == "preset":
            voice_name = self.vieneu_selected_voice.get()
            voice_info = VIENEU_VOICE_SAMPLES.get(voice_name, {})
            audio_path = voice_info.get("audio", "")
            
            self._vieneu_log(f"📁 Đang tìm file mẫu: {voice_name}")
            
            if not os.path.exists(audio_path):
                self._vieneu_log(f"❌ Không tìm thấy: {audio_path}")
                sample_dir = os.path.join(VIENEU_TTS_DIR, "sample")
                error_msg = f"Không tìm thấy file audio mẫu cho giọng '{voice_name}'.\n\nĐường dẫn: {audio_path}\n\n💡 Hãy kiểm tra:\n1. Thư mục {sample_dir} có tồn tại không\n2. File audio mẫu có đúng tên không"
                return (False, voice_mode, voice_name, error_msg)
            
            return (True, voice_mode, voice_name, None)
        else:
            # Custom voice - validate ref_codes
            if self.vieneu_ref_codes is None or (hasattr(self.vieneu_ref_codes, '__len__') and len(self.vieneu_ref_codes) == 0):
                self._vieneu_log("❌ Chế độ Clone giọng mới được chọn nhưng chưa mã hóa giọng mẫu")
                error_msg = "Bạn đang ở chế độ 'Clone giọng mới'.\n\nVui lòng:\n1. Chọn file audio mẫu (.wav)\n2. Nhập nội dung lời thoại mẫu\n3. Bấm nút Mã hóa giọng mẫu\n\nHoặc chuyển sang chế độ 'Giọng mẫu có sẵn' nếu muốn dùng giọng preset."
                return (False, voice_mode, "Custom", error_msg)
            
            return (True, voice_mode, "Custom", None)

    def _vieneu_browse_custom_audio(self):
        """Browse for custom voice audio file"""
        file_path = filedialog.askopenfilename(
            filetypes=[("Audio files", "*.wav *.mp3"), ("WAV files", "*.wav"), ("All files", "*.*")]
        )
        if file_path:
            self.vieneu_custom_audio_entry.delete(0, "end")
            self.vieneu_custom_audio_entry.insert(0, file_path)
            self._vieneu_log(f"📂 Đã chọn file audio mẫu: {os.path.basename(file_path)}")

    def _vieneu_browse_file(self):
        """Browse for input file"""
        file_path = filedialog.askopenfilename(
            filetypes=[("Text files", "*.txt"), ("Subtitle files", "*.srt *.vtt"), ("Word files", "*.docx"), ("All files", "*.*")]
        )
        if file_path:
            self.vieneu_file_entry.delete(0, "end")
            self.vieneu_file_entry.insert(0, file_path)
            self._vieneu_log(f"📂 Đã chọn file: {os.path.basename(file_path)}")

    def _vieneu_browse_folder(self):
        """Browse for input folder"""
        dir_path = filedialog.askdirectory(title="Chọn thư mục chứa file")
        if dir_path:
            self.vieneu_file_entry.delete(0, "end")
            self.vieneu_file_entry.insert(0, dir_path)
            # Count files
            txt_files = glob.glob(os.path.join(dir_path, "*.txt"))
            srt_files = glob.glob(os.path.join(dir_path, "*.srt"))
            self._vieneu_log(f"📁 Đã chọn thư mục: {dir_path} ({len(txt_files)} txt, {len(srt_files)} srt)")

    def _vieneu_browse_output(self):
        """Browse for output directory"""
        dir_path = filedialog.askdirectory()
        if dir_path:
            self.vieneu_output_entry.delete(0, "end")
            self.vieneu_output_entry.insert(0, dir_path)

    def _vieneu_preview_preset_voice(self):
        """Preview/play the selected preset voice sample"""
        voice_name = self.vieneu_selected_voice.get()
        voice_info = VIENEU_VOICE_SAMPLES.get(voice_name, {})
        audio_path = voice_info.get("audio", "")
        
        if audio_path and os.path.exists(audio_path):
            self.player.play(audio_path)
            self._vieneu_log(f"▶ Đang phát mẫu: {voice_name}")
        else:
            self._vieneu_log(f"❌ Không tìm thấy file mẫu cho giọng: {voice_name}")
            messagebox.showwarning("Cảnh báo", f"Không tìm thấy file audio mẫu.\nĐường dẫn: {audio_path}")

    def _vieneu_load_model(self):
        """Load VN TTS model"""
        self._vieneu_progress_log(5, "Bắt đầu tải")
        self.btn_vieneu_load.configure(state="disabled")
        self.vieneu_model_status.configure(text="⏳ VN TTS đang tải...", text_color="#fbbf24")
        
        def load_thread():
            try:
                backbone_name = self.vieneu_backbone_var.get()
                codec_name = self.vieneu_codec_var.get()
                device = self.vieneu_device_var.get()
                enable_triton = self.vieneu_triton_var.get()
                try:
                    max_batch = int(self.vieneu_batch_var.get() or "8")
                except ValueError:
                    max_batch = 8
                
                backbone_config = VIENEU_BACKBONE_CONFIGS.get(backbone_name, {})
                codec_config = VIENEU_CODEC_CONFIGS.get(codec_name, {})
                
                backbone_repo = backbone_config.get("repo", "pnnbao-ump/VieNeu-TTS-q4-gguf")
                codec_repo = codec_config.get("repo", "neuphonic/neucodec")
                
                # Get GPU optimization settings from UI slider (initialized in _setup_vieneu_tab)
                memory_util = self.vieneu_memory_slider.get()
                enable_prefix_caching = backbone_config.get("enable_prefix_caching", True)
                quant_policy = backbone_config.get("quant_policy", 0)
                self._vieneu_progress_log(10, "Chuẩn bị cấu hình")
                
                # Add VN TTS to path
                vieneu_path = VIENEU_TTS_DIR
                if vieneu_path not in sys.path:
                    sys.path.insert(0, vieneu_path)
                
                # Determine actual device - Fix GPU detection
                # Import torch and check CUDA availability with detailed debugging
                import torch
                
                # Debug: Log PyTorch build info with safe defaults
                torch_version = getattr(torch, '__version__', 'Unknown')
                torch_cuda_version = getattr(torch.version, 'cuda', None) or "Không có CUDA"
                
                # Check if PyTorch was built with CUDA support
                # Use torch.cuda.is_built() if available, otherwise check torch.version.cuda
                if hasattr(torch.cuda, 'is_built'):
                    torch_cuda_built = torch.cuda.is_built()
                else:
                    # Fallback: check if CUDA version string exists and is not empty
                    torch_cuda_built = bool(getattr(torch.version, 'cuda', None))
                
                self._vieneu_progress_log(25, "Kiểm tra thiết bị")

                # Determine if PyTorch was built with CUDA support and check GPU availability
                if not torch_cuda_built:
                    has_cuda = False
                else:
                    # PyTorch has CUDA support, now check if GPU is actually available
                    has_cuda = torch.cuda.is_available()
                
                # Determine device based on selection and CUDA availability
                if device == "Auto":
                    if has_cuda:
                        if "gguf" in backbone_name.lower():
                            backbone_device = "gpu"
                        else:
                            backbone_device = "cuda"
                        codec_device = "cuda"
                    else:
                        backbone_device = "cpu"
                        codec_device = "cpu"
                elif device == "CPU":
                    backbone_device = "cpu"
                    codec_device = "cpu"
                else:  # CUDA (GPU) selected
                    if has_cuda:
                        if "gguf" in backbone_name.lower():
                            backbone_device = "gpu"
                        else:
                            backbone_device = "cuda"
                        codec_device = "cuda"
                    else:
                        self.after(0, lambda: self._vieneu_log("⚠️ GPU không khả dụng, chuyển sang CPU"))
                        backbone_device = "cpu"
                        codec_device = "cpu"
                
                # ONNX codec only runs on CPU
                if "onnx" in codec_repo.lower():
                    codec_device = "cpu"
                
                device_display = backbone_device.upper()
                self._vieneu_progress_log(45, f"Đang sử dụng {device_display}")
                
                # Check if we should use FastVieNeuTTS (LMDeploy)
                use_fast = (
                    has_cuda and 
                    device != "CPU" and 
                    "gguf" not in backbone_name.lower()
                )
                
                # Import and create TTS instance
                from vieneu_tts import VieNeuTTS, FastVieNeuTTS
                
                if use_fast:
                    self._vieneu_progress_log(60, "Tối ưu GPU")
                    try:
                        self.vieneu_tts_instance = FastVieNeuTTS(
                            backbone_repo=backbone_repo,
                            backbone_device=backbone_device,
                            codec_repo=codec_repo,
                            codec_device=codec_device,
                            memory_util=memory_util,
                            tp=1,
                            enable_prefix_caching=enable_prefix_caching,
                            quant_policy=quant_policy,
                            enable_triton=enable_triton,
                            max_batch_size=max_batch,
                        )
                        self.vieneu_using_fast = True
                    except Exception as e:
                        clean_err = self._sanitize_error_message(str(e))
                        self._vieneu_progress_log(65, "Chuyển sang cấu hình thường")
                        self.after(0, lambda err=clean_err: self._vieneu_log(f"⚠️ Tối ưu GPU không khả dụng: {err}"))
                        self.vieneu_tts_instance = VieNeuTTS(
                            backbone_repo=backbone_repo,
                            backbone_device=backbone_device,
                            codec_repo=codec_repo,
                            codec_device=codec_device
                        )
                        self.vieneu_using_fast = False
                else:
                    self._vieneu_progress_log(70, "Đang tải backend chuẩn")
                    self.vieneu_tts_instance = VieNeuTTS(
                        backbone_repo=backbone_repo,
                        backbone_device=backbone_device,
                        codec_repo=codec_repo,
                        codec_device=codec_device
                    )
                    self.vieneu_using_fast = False
                
                self._vieneu_progress_log(90, "Hoàn tất khởi tạo")
                self.vieneu_model_loaded = True
                
                # Update UI
                backend_name = "🚀 LMDeploy" if self.vieneu_using_fast else "📦 Standard"
                status_msg = f"✅ Model đã tải!\n{backend_name} | {backbone_device.upper()}"
                
                self.after(0, lambda: self.vieneu_model_status.configure(text=status_msg, text_color="#22c55e"))
                self.after(0, lambda: self._vieneu_log(f"✅ Model tải thành công!"))
                self.after(0, lambda: self.btn_vieneu_generate.configure(state="normal"))
                self.after(0, lambda: self.btn_vieneu_process.configure(state="normal"))
                
                # Enable streaming checkbox if streaming is supported
                # Streaming is supported by: FastVieNeuTTS (GPU+LMDeploy) and GGUF models
                supports_streaming = backbone_config.get("supports_streaming", False)
                if self.vieneu_using_fast or supports_streaming:
                    self.after(0, lambda: self.vieneu_streaming_cb.configure(state="normal"))
                    self.after(0, lambda: self._vieneu_log("⚡ Streaming khả dụng"))
                else:
                    self.after(0, lambda: self.vieneu_streaming_cb.configure(state="disabled"))
                    self.after(0, lambda: self.vieneu_streaming_var.set(False))
                
            except ImportError as e:
                err_msg = self._sanitize_error_message(str(e))
                self.after(0, lambda: self._vieneu_log(f"❌ Lỗi thư viện: {err_msg}"))
                self.after(0, lambda: self.vieneu_model_status.configure(text=f"❌ Lỗi import: {err_msg[:50]}", text_color="#ef4444"))
                self._vieneu_progress_log(0, "Lỗi tải")
            except Exception as e:
                err_msg = self._sanitize_error_message(str(e))
                self.after(0, lambda: self._vieneu_log(f"❌ Lỗi: {err_msg}"))
                self.after(0, lambda: self.vieneu_model_status.configure(text=f"❌ Lỗi: {err_msg[:50]}", text_color="#ef4444"))
                self._vieneu_progress_log(0, "Lỗi tải")
            finally:
                self.after(0, lambda: self.btn_vieneu_load.configure(state="normal"))
                if self.vieneu_model_loaded:
                    self._vieneu_progress_log(100, "Hoàn thành")
                else:
                    self._vieneu_progress_log(0, "Chưa hoàn thành")
        
        threading.Thread(target=load_thread, daemon=True).start()

    def _vieneu_encode_custom_voice(self):
        """Encode custom voice for voice cloning"""
        if not self.vieneu_model_loaded or self.vieneu_tts_instance is None:
            messagebox.showerror("Lỗi", "Vui lòng tải model trước!")
            return
        
        audio_path = self.vieneu_custom_audio_entry.get().strip()
        ref_text = self.vieneu_custom_text_input.get("1.0", "end").strip()
        
        if not audio_path or not os.path.exists(audio_path):
            messagebox.showerror("Lỗi", "Vui lòng chọn file audio mẫu!")
            return
        
        if not ref_text or ref_text == "Nhập nội dung lời thoại trong file audio mẫu...":
            messagebox.showerror("Lỗi", "Vui lòng nhập nội dung lời thoại mẫu!")
            return
        
        self._vieneu_log(f"🔧 Đang mã hóa giọng mẫu: {os.path.basename(audio_path)}")
        self.vieneu_custom_status.configure(text="⏳ Đang xử lý...", text_color="#fbbf24")
        
        def encode_thread():
            try:
                import torch
                ref_codes = self.vieneu_tts_instance.encode_reference(audio_path)
                
                if isinstance(ref_codes, torch.Tensor):
                    ref_codes = ref_codes.cpu().numpy()
                
                self.vieneu_ref_codes = ref_codes
                self.vieneu_ref_text = ref_text
                self.vieneu_custom_ref_audio = audio_path
                self.vieneu_custom_ref_text = ref_text
                
                self.after(0, lambda: self._vieneu_log("✅ Đã mã hóa giọng mẫu thành công!"))
                self.after(0, lambda: self._vieneu_log("📌 Bước tiếp: Nhập văn bản → Bấm 'TẠO AUDIO VỚI GIỌNG ĐÃ CLONE'"))
                self.after(0, lambda: self._vieneu_log("💾 Hoặc bấm 'LƯU GIỌNG' để sử dụng lại lần sau"))
                self.after(0, lambda: self.vieneu_custom_status.configure(text="✅ Sẵn sàng! Nhập văn bản và bấm nút bên dưới để tạo audio", text_color="#22c55e"))
                # Enable the clone button, save button and show instructions
                self.after(0, lambda: self.btn_vieneu_clone_now.configure(state="normal"))
                self.after(0, lambda: self.btn_vieneu_save_voice.configure(state="normal"))
                self.after(0, lambda: self.vieneu_clone_instruction.pack(anchor="w"))
                
            except Exception as e:
                self.after(0, lambda: self._vieneu_log(f"❌ Lỗi mã hóa: {str(e)}"))
                self.after(0, lambda: self.vieneu_custom_status.configure(text=f"❌ Lỗi: {str(e)[:30]}", text_color="#ef4444"))
        
        threading.Thread(target=encode_thread, daemon=True).start()

    def _vieneu_save_cloned_voice(self):
        """Save cloned voice to sample directory for reuse"""
        # Validate voice has been encoded
        if self.vieneu_ref_codes is None:
            messagebox.showerror("Lỗi", "Vui lòng mã hóa giọng mẫu trước!")
            return
        
        if self.vieneu_custom_ref_audio is None or not os.path.exists(self.vieneu_custom_ref_audio):
            messagebox.showerror("Lỗi", "Không tìm thấy file audio mẫu!")
            return
        
        # Get voice name from entry
        voice_name = self.vieneu_save_voice_name.get().strip()
        if not voice_name:
            messagebox.showerror("Lỗi", "Vui lòng nhập tên cho giọng nói!")
            return
        
        # Check if voice name already exists
        if voice_name in VIENEU_VOICE_SAMPLES:
            result = messagebox.askyesno("Xác nhận", f"Giọng '{voice_name}' đã tồn tại. Ghi đè?")
            if not result:
                return
        
        self._vieneu_log(f"💾 Đang lưu giọng: {voice_name}")
        self.btn_vieneu_save_voice.configure(state="disabled")
        
        def save_thread():
            try:
                import torch
                import numpy as np
                
                # Create sample directory if not exists
                sample_dir = os.path.join(VIENEU_TTS_DIR, "sample")
                os.makedirs(sample_dir, exist_ok=True)
                
                # Copy audio file
                audio_dest = os.path.join(sample_dir, f"{voice_name}.wav")
                shutil.copy(self.vieneu_custom_ref_audio, audio_dest)
                
                # Save text file
                text_dest = os.path.join(sample_dir, f"{voice_name}.txt")
                with open(text_dest, "w", encoding="utf-8") as f:
                    f.write(self.vieneu_custom_ref_text)
                
                # Save codes file
                codes_dest = os.path.join(sample_dir, f"{voice_name}.pt")
                ref_codes = self.vieneu_ref_codes
                if isinstance(ref_codes, np.ndarray):
                    ref_codes = torch.from_numpy(ref_codes)
                torch.save(ref_codes, codes_dest)
                
                # Add to VIENEU_VOICE_SAMPLES dictionary (runtime)
                VIENEU_VOICE_SAMPLES[voice_name] = {
                    "audio": audio_dest,
                    "text": text_dest,
                    "codes": codes_dest,
                    "gender": "Custom",
                    "accent": "Custom"
                }
                
                self.after(0, lambda: self._vieneu_log(f"✅ Đã lưu giọng '{voice_name}' thành công!"))
                self.after(0, lambda: self._vieneu_log(f"📁 Vị trí: {sample_dir}"))
                
                # Refresh voice list
                self.after(0, self._vieneu_populate_voice_list)
                
                # Clear save name entry
                self.after(0, lambda: self.vieneu_save_voice_name.delete(0, "end"))
                
                # Show success message
                self.after(0, lambda: messagebox.showinfo("Thành công", f"Đã lưu giọng '{voice_name}'!\n\nGiọng sẽ xuất hiện trong danh sách 'Giọng mẫu có sẵn'."))
                
            except Exception as e:
                self.after(0, lambda err=str(e): self._vieneu_log(f"❌ Lỗi lưu giọng: {err}"))
                self.after(0, lambda: messagebox.showerror("Lỗi", f"Không thể lưu giọng: {str(e)}"))
            finally:
                self.after(0, lambda: self.btn_vieneu_save_voice.configure(state="normal"))
        
        threading.Thread(target=save_thread, daemon=True).start()

    def _vieneu_generate(self):
        """Generate audio using VN TTS"""
        if not self.vieneu_model_loaded or self.vieneu_tts_instance is None:
            messagebox.showerror("Lỗi", "Vui lòng tải model trước!")
            return
        
        text = self.vieneu_text_input.get("1.0", "end").strip()
        if not text:
            messagebox.showerror("Lỗi", "Vui lòng nhập văn bản!")
            return
        
        # Validate voice settings
        success, voice_mode, voice_name, error_msg = self._vieneu_validate_voice_settings()
        if not success:
            messagebox.showerror("Lỗi", error_msg)
            return
        
        self._vieneu_log(f"🎙️ Đang tạo audio với giọng: {voice_name}")
        self._vieneu_log(f"📝 Text length: {len(text)} chars")
        
        # Check if streaming is enabled and supported
        # Use backbone configuration to determine streaming support
        backbone_name = self.vieneu_backbone_var.get()
        backbone_config = VIENEU_BACKBONE_CONFIGS.get(backbone_name, {})
        streaming_supported = backbone_config.get("supports_streaming", False) or self.vieneu_using_fast
        use_streaming = self.vieneu_streaming_var.get() and streaming_supported
        if use_streaming:
            self._vieneu_log("⚡ Streaming mode enabled")
        
        self.btn_vieneu_generate.configure(state="disabled")
        self.vieneu_status_lbl.configure(text="Đang xử lý...")
        
        def generate_thread():
            try:
                import torch
                import numpy as np
                import soundfile as sf
                import tempfile
                
                # Get reference
                if voice_mode == "preset":
                    voice_info = VIENEU_VOICE_SAMPLES.get(self.vieneu_selected_voice.get(), {})
                    audio_path = voice_info.get("audio", "")
                    text_path = voice_info.get("text", "")
                    codes_path = voice_info.get("codes", "")
                    
                    # Load reference text
                    if os.path.exists(text_path):
                        with open(text_path, "r", encoding="utf-8") as f:
                            ref_text = f.read().strip()
                    else:
                        ref_text = ""
                    
                    # Load or encode reference codes
                    codec_name = self.vieneu_codec_var.get()
                    if "ONNX" in codec_name and os.path.exists(codes_path):
                        self.after(0, lambda: self._vieneu_log("📦 Đang tải mã giọng..."))
                        try:
                            ref_codes = torch.load(codes_path, map_location="cpu", weights_only=True)
                        except (RuntimeError, EOFError, FileNotFoundError) as e:
                            self.after(0, lambda err=str(e): self._vieneu_log(f"⚠️ Không thể load codes file, encoding thay thế: {err}"))
                            ref_codes = self.vieneu_tts_instance.encode_reference(audio_path)
                    else:
                        self.after(0, lambda: self._vieneu_log("🔧 Đang mã hóa giọng tham chiếu..."))
                        ref_codes = self.vieneu_tts_instance.encode_reference(audio_path)
                else:
                    ref_codes = self.vieneu_ref_codes
                    ref_text = self.vieneu_ref_text
                
                if isinstance(ref_codes, torch.Tensor):
                    ref_codes = ref_codes.cpu().numpy()
                
                sr = VIENEU_SAMPLE_RATE
                start_time = time.time()
                all_audio = []
                
                # Use streaming if enabled and available
                if use_streaming:
                    self.after(0, lambda: self._vieneu_log("⚡ Bắt đầu streaming..."))
                    self.after(0, lambda: self.vieneu_status_lbl.configure(text="Streaming..."))
                    
                    # For streaming, we process text as a whole or in larger chunks
                    # Split into chunks if text is very long
                    chunks = split_text_into_chunks(text, chunk_size=VIENEU_MAX_CHARS_PER_CHUNK)
                    total_chunks = len(chunks)
                    
                    silence_pad = np.zeros(int(sr * 0.15), dtype=np.float32)
                    
                    for chunk_idx, chunk in enumerate(chunks):
                        chunk_text = chunk.text if hasattr(chunk, 'text') else str(chunk)
                        self.after(0, lambda idx=chunk_idx+1, total=total_chunks: self._vieneu_log(f"⚡ Streaming đoạn {idx}/{total}..."))
                        
                        chunk_audio = []
                        try:
                            # Check if infer_stream method exists before calling
                            if not hasattr(self.vieneu_tts_instance, 'infer_stream'):
                                raise AttributeError("infer_stream method not available")
                            
                            for audio_chunk in self.vieneu_tts_instance.infer_stream(chunk_text, ref_codes, ref_text):
                                if audio_chunk is not None and len(audio_chunk) > 0:
                                    chunk_audio.append(audio_chunk)
                        except (AttributeError, NotImplementedError, Exception) as stream_err:
                            # Log appropriate message based on error type
                            if isinstance(stream_err, (AttributeError, NotImplementedError)):
                                self.after(0, lambda err=str(stream_err): self._vieneu_log(f"⚠️ Streaming không khả dụng, dùng chế độ thường"))
                            else:
                                self.after(0, lambda err=str(stream_err): self._vieneu_log(f"⚠️ Streaming lỗi, thử non-streaming: {err}"))
                            # Fallback to non-streaming
                            wav = self.vieneu_tts_instance.infer(chunk_text, ref_codes, ref_text)
                            if wav is not None and len(wav) > 0:
                                chunk_audio = [wav]
                        
                        # Filter out empty arrays and concatenate
                        chunk_audio = [arr for arr in chunk_audio if arr is not None and len(arr) > 0]
                        if chunk_audio:
                            combined = np.concatenate(chunk_audio)
                            all_audio.append(combined)
                            if chunk_idx < total_chunks - 1:
                                all_audio.append(silence_pad)
                else:
                    # Split long text into chunks using local function
                    chunks = split_text_into_chunks(text, chunk_size=VIENEU_MAX_CHARS_PER_CHUNK)
                    total_chunks = len(chunks)
                    
                    self.after(0, lambda: self._vieneu_log(f"📝 Chia thành {total_chunks} đoạn"))
                    
                    silence_pad = np.zeros(int(sr * 0.15), dtype=np.float32)
                    
                    # Process chunks - chunks are TextChunk objects with .text attribute
                    for i, chunk in enumerate(chunks):
                        self.after(0, lambda idx=i+1, total=total_chunks: self._vieneu_log(f"⏳ Đang xử lý đoạn {idx}/{total}..."))
                        self.after(0, lambda idx=i+1, total=total_chunks: self.vieneu_status_lbl.configure(text=f"Đoạn {idx}/{total}"))
                        
                        # TextChunk has .text attribute
                        chunk_text = chunk.text if hasattr(chunk, 'text') else str(chunk)
                        wav = self.vieneu_tts_instance.infer(chunk_text, ref_codes, ref_text)
                        
                        if wav is not None and len(wav) > 0:
                            all_audio.append(wav)
                            if i < total_chunks - 1:
                                all_audio.append(silence_pad)
                
                if not all_audio:
                    self.after(0, lambda: self._vieneu_log("❌ Không tạo được audio!"))
                    self.after(0, lambda: self.vieneu_status_lbl.configure(text="Lỗi!"))
                    return
                
                # Concatenate all audio
                final_wav = np.concatenate(all_audio)
                
                # Save to temp file
                with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
                    sf.write(tmp.name, final_wav, sr)
                    self.vieneu_temp_audio = tmp.name
                
                process_time = time.time() - start_time
                duration = len(final_wav) / sr
                speed = duration / process_time if process_time > 0 else 0
                
                self.after(0, lambda: self._vieneu_log(f"✅ Hoàn tất! ({process_time:.2f}s, {speed:.2f}x realtime)"))
                self.after(0, lambda: self.vieneu_status_lbl.configure(text="Hoàn thành!"))
                self.after(0, lambda: self.btn_vieneu_play.configure(state="normal"))
                self.after(0, lambda: self.btn_vieneu_save.configure(state="normal"))
                
            except Exception as e:
                import traceback
                traceback.print_exc()
                self.after(0, lambda: self._vieneu_log(f"❌ Lỗi: {str(e)}"))
                self.after(0, lambda: self.vieneu_status_lbl.configure(text="Lỗi!"))
            finally:
                self.after(0, lambda: self.btn_vieneu_generate.configure(state="normal"))
        
        threading.Thread(target=generate_thread, daemon=True).start()

    def _vieneu_play(self):
        """Play the generated VN TTS audio"""
        if self.vieneu_temp_audio and os.path.exists(self.vieneu_temp_audio):
            self.player.play(self.vieneu_temp_audio)
            self._vieneu_log("▶ Đang phát audio...")

    def _vieneu_stop_playback(self):
        """Stop audio playback"""
        self.player.stop()
        self._vieneu_log("⏹ Đã dừng phát")

    def _vieneu_save(self):
        """Save the generated audio to file"""
        if not self.vieneu_temp_audio or not os.path.exists(self.vieneu_temp_audio):
            return
        
        file_path = filedialog.asksaveasfilename(
            defaultextension=".wav",
            filetypes=[("WAV files", "*.wav"), ("All files", "*.*")]
        )
        if file_path:
            shutil.copy(self.vieneu_temp_audio, file_path)
            self._vieneu_log(f"💾 Đã lưu: {file_path}")

    def _vieneu_process_file(self):
        """Process file/folder with VN TTS"""
        if not self.vieneu_model_loaded or self.vieneu_tts_instance is None:
            messagebox.showerror("Lỗi", "Vui lòng tải model trước!")
            return
        
        input_path = self.vieneu_file_entry.get().strip()
        output_dir = self.vieneu_output_entry.get().strip()
        
        if not input_path or not os.path.exists(input_path):
            messagebox.showerror("Lỗi", "Vui lòng chọn file hoặc thư mục!")
            return
        
        if not output_dir:
            messagebox.showerror("Lỗi", "Vui lòng chọn thư mục output!")
            return
        
        os.makedirs(output_dir, exist_ok=True)
        
        # Validate voice settings before starting
        success, voice_mode, voice_name, error_msg = self._vieneu_validate_voice_settings()
        if not success:
            messagebox.showerror("Lỗi", error_msg)
            return
        
        merge_after = self.vieneu_merge_var.get()
        delete_chunks = self.vieneu_delete_chunks_var.get()
        
        self.vieneu_processing = True
        self.btn_vieneu_process.configure(state="disabled")
        self.btn_vieneu_stop_process.configure(state="normal")
        self.vieneu_progress.set(0)
        
        threading.Thread(
            target=self._vieneu_file_worker,
            args=(input_path, output_dir, voice_mode, merge_after, delete_chunks),
            daemon=True
        ).start()

    def _vieneu_file_worker(self, input_path, output_dir, voice_mode, merge_after, delete_chunks):
        """Worker thread for file processing"""
        try:
            import torch
            import numpy as np
            import soundfile as sf
            
            # Get reference voice (validation done via _vieneu_validate_voice_settings in _vieneu_process_file)
            if voice_mode == "preset":
                voice_name = self.vieneu_selected_voice.get()
                voice_info = VIENEU_VOICE_SAMPLES.get(voice_name, {})
                audio_path = voice_info.get("audio", "")
                text_path = voice_info.get("text", "")
                codes_path = voice_info.get("codes", "")
                
                if os.path.exists(text_path):
                    with open(text_path, "r", encoding="utf-8") as f:
                        ref_text = f.read().strip()
                else:
                    ref_text = ""
                
                codec_name = self.vieneu_codec_var.get()
                if "ONNX" in codec_name and os.path.exists(codes_path):
                    try:
                        ref_codes = torch.load(codes_path, map_location="cpu", weights_only=True)
                    except (RuntimeError, EOFError, FileNotFoundError) as e:
                        self.after(0, lambda err=str(e): self._vieneu_log(f"⚠️ Không thể load codes file: {err}"))
                        ref_codes = self.vieneu_tts_instance.encode_reference(audio_path)
                else:
                    ref_codes = self.vieneu_tts_instance.encode_reference(audio_path)
            else:
                # Custom voice (already validated)
                ref_codes = self.vieneu_ref_codes
                ref_text = self.vieneu_ref_text
            
            if isinstance(ref_codes, torch.Tensor):
                ref_codes = ref_codes.cpu().numpy()
            
            # Determine files to process
            if os.path.isdir(input_path):
                txt_files = glob.glob(os.path.join(input_path, "*.txt"))
                srt_files = glob.glob(os.path.join(input_path, "*.srt"))
                all_files = sorted(txt_files + srt_files)
            else:
                all_files = [input_path]
            
            total_files = len(all_files)
            if total_files == 0:
                self.after(0, lambda: self._vieneu_log("❌ Không tìm thấy file nào!"))
                return
            
            self.after(0, lambda: self._vieneu_log(f"🚀 Bắt đầu xử lý {total_files} file..."))
            
            sr = VIENEU_SAMPLE_RATE
            silence_pad = np.zeros(int(sr * 0.15), dtype=np.float32)
            ffmpeg_path = getattr(self, 'ffmpeg_path', get_default_ffmpeg_path())
            
            for file_idx, file_path in enumerate(all_files):
                if not self.vieneu_processing:
                    self.after(0, lambda: self._vieneu_log("⏹ Đã dừng bởi người dùng"))
                    break
                
                file_name = os.path.basename(file_path)
                base_name = os.path.splitext(file_name)[0]
                
                self.after(0, lambda f=file_name, i=file_idx+1, t=total_files: 
                          self._vieneu_log(f"\n📄 [{i}/{t}] Xử lý: {f}"))
                
                try:
                    # Read file content
                    ext = os.path.splitext(file_path)[1].lower()
                    if ext == '.srt':
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                        subs = parse_srt(content)
                        # SRT subtitles are strings, create list of strings
                        text_items = [sub.text for sub in subs]
                        is_text_chunk = False
                    else:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                        # Clean and split using local function - returns TextChunk objects
                        cleaned = clean_text_for_tts(content)
                        text_items = split_text_into_chunks(cleaned, chunk_size=VIENEU_MAX_CHARS_PER_CHUNK)
                        is_text_chunk = True
                    
                    if not text_items:
                        self.after(0, lambda: self._vieneu_log("  ⚠️ File trống, bỏ qua"))
                        continue
                    
                    self.after(0, lambda c=len(text_items): self._vieneu_log(f"  📝 {c} đoạn"))
                    
                    # Process chunks
                    all_audio = []
                    chunk_files = []
                    temp_dir = os.path.join(output_dir, f"_temp_{base_name}")
                    os.makedirs(temp_dir, exist_ok=True)
                    
                    for i, chunk_item in enumerate(text_items):
                        if not self.vieneu_processing:
                            break
                        
                        # Handle both TextChunk objects and plain strings
                        if is_text_chunk and hasattr(chunk_item, 'text'):
                            chunk_text = chunk_item.text
                        else:
                            chunk_text = str(chunk_item)
                        
                        try:
                            wav = self.vieneu_tts_instance.infer(chunk_text, ref_codes, ref_text)
                            
                            if wav is not None and len(wav) > 0:
                                # Save chunk
                                chunk_file = os.path.join(temp_dir, f"chunk_{i:04d}.wav")
                                sf.write(chunk_file, wav, sr)
                                chunk_files.append(chunk_file)
                                all_audio.append(wav)
                                if i < len(text_items) - 1:
                                    all_audio.append(silence_pad)
                        except Exception as e:
                            self.after(0, lambda err=str(e), idx=i: self._vieneu_log(f"  ⚠️ Chunk [{idx}] lỗi: {err}"))
                    
                    # Merge if requested
                    if merge_after and all_audio:
                        output_file = os.path.join(output_dir, f"{base_name}.wav")
                        final_wav = np.concatenate(all_audio)
                        sf.write(output_file, final_wav, sr)
                        self.after(0, lambda f=output_file: self._vieneu_log(f"  ✅ Đã tạo: {os.path.basename(f)}"))
                        
                        # Clean up chunks
                        if delete_chunks:
                            for cf in chunk_files:
                                try:
                                    os.remove(cf)
                                except OSError:
                                    pass
                            try:
                                os.rmdir(temp_dir)
                            except OSError:
                                pass
                    elif chunk_files:
                        self.after(0, lambda n=len(chunk_files): self._vieneu_log(f"  ✅ Đã tạo {n} chunks"))
                    
                except Exception as e:
                    self.after(0, lambda err=str(e): self._vieneu_log(f"  ❌ Lỗi: {err}"))
                
                # Update progress
                progress = (file_idx + 1) / total_files
                self.after(0, lambda p=progress: self.vieneu_progress.set(p))
                self.after(0, lambda i=file_idx+1, t=total_files: 
                          self.vieneu_file_status.configure(text=f"File {i}/{t}"))
            
            self.after(0, lambda: self._vieneu_log(f"\n{'='*40}"))
            self.after(0, lambda: self._vieneu_log(f"✅ Hoàn thành!"))
            self.after(0, lambda: self._vieneu_log(f"📁 Output: {output_dir}"))
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            self.after(0, lambda: self._vieneu_log(f"❌ Lỗi: {str(e)}"))
        finally:
            self.vieneu_processing = False
            self.after(0, lambda: self.btn_vieneu_process.configure(state="normal"))
            self.after(0, lambda: self.btn_vieneu_stop_process.configure(state="disabled"))
            self.after(0, lambda: self.vieneu_file_status.configure(text="Hoàn thành!"))

    def _vieneu_stop_processing(self):
        """Stop file processing"""
        self.vieneu_processing = False
        self._vieneu_log("⏹ Đang dừng...")

    # ==========================================================================
    # TAB: ĐỌC VOICE KỊCH BẢN (Script Reader)
    # ==========================================================================
    def _setup_script_tab(self):
        """Setup the Script Voice Reading tab - combines Google TTS, Capcut, and Edge TTS"""
        tab = self.tab_script
        tab.grid_columnconfigure(0, weight=3)
        tab.grid_columnconfigure(1, weight=7)
        tab.grid_rowconfigure(0, weight=1)

        # --- LEFT: Engine & Voice Selection ---
        left_frame = ctk.CTkFrame(tab, fg_color="#1a1a2e")
        left_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 5), pady=0)

        # Header
        header = ctk.CTkFrame(left_frame, fg_color="#7c3aed", height=45)
        header.pack(fill="x")
        ctk.CTkLabel(header, text="📖 ĐỌC VOICE KỊCH BẢN", font=("Roboto", 14, "bold"), text_color="white").pack(pady=10)

        # TTS Engine Selection
        ctk.CTkLabel(left_frame, text="CHỌN ENGINE TTS", font=("Roboto", 12, "bold"), text_color="#a78bfa").pack(anchor="w", padx=15, pady=(20, 5))
        
        self.script_engine_var = ctk.StringVar(value="edge")
        
        engine_frame = ctk.CTkFrame(left_frame, fg_color="#1f2937")
        engine_frame.pack(fill="x", padx=15, pady=5)
        
        ctk.CTkRadioButton(engine_frame, text="Edge TTS (Microsoft)", 
                          variable=self.script_engine_var, value="edge",
                          command=self._script_on_engine_change).pack(anchor="w", pady=5, padx=10)
        ctk.CTkRadioButton(engine_frame, text="Capcut Voice (TikTok)", 
                          variable=self.script_engine_var, value="capcut",
                          command=self._script_on_engine_change).pack(anchor="w", pady=5, padx=10)
        ctk.CTkRadioButton(engine_frame, text="Google Gemini TTS", 
                          variable=self.script_engine_var, value="google",
                          command=self._script_on_engine_change).pack(anchor="w", pady=5, padx=10)

        # Language and Gender Filters for Script Tab
        ctk.CTkLabel(left_frame, text="BỘ LỌC GIỌNG", font=("Roboto", 12, "bold"), text_color="#a78bfa").pack(anchor="w", padx=15, pady=(15, 5))
        
        filter_frame = ctk.CTkFrame(left_frame, fg_color="#1f2937")
        filter_frame.pack(fill="x", padx=15, pady=5)
        
        # Language filter
        ctk.CTkLabel(filter_frame, text="Ngôn ngữ:", font=("Roboto", 10)).pack(anchor="w", padx=10, pady=(10, 0))
        self.script_lang_var = ctk.StringVar(value="Tất cả")
        
        # Create scrollable frame for language options
        self.script_lang_scroll = ctk.CTkScrollableFrame(filter_frame, height=80, fg_color="#1f2937")
        self.script_lang_scroll.pack(fill="x", padx=10, pady=5)
        
        # Language radio buttons - will be populated based on engine
        self._script_populate_lang_filters()
        
        # Gender filter
        ctk.CTkLabel(filter_frame, text="Giới tính:", font=("Roboto", 10)).pack(anchor="w", padx=10, pady=(10, 0))
        self.script_gender_var = ctk.StringVar(value="Tất cả")
        self.script_gender_filter = ctk.CTkComboBox(
            filter_frame, 
            values=["Tất cả", "Male", "Female", "Nam", "Nữ", "Khác"],
            variable=self.script_gender_var,
            command=self._script_filter_voices
        )
        self.script_gender_filter.pack(fill="x", padx=10, pady=(5, 10))

        # Voice Selection
        ctk.CTkLabel(left_frame, text="CHỌN GIỌNG ĐỌC", font=("Roboto", 12, "bold"), text_color="#a78bfa").pack(anchor="w", padx=15, pady=(15, 5))
        
        self.script_voice_list = ctk.CTkScrollableFrame(left_frame, fg_color="#1f2937", height=200)
        self.script_voice_list.pack(fill="both", expand=True, padx=15, pady=5)
        
        self.script_selected_voice = ctk.StringVar(value="en-US-EmmaMultilingualNeural")
        self._script_update_voice_list(update_lang_filters=False)

        # Processing Options
        ctk.CTkLabel(left_frame, text="TÙY CHỌN XỬ LÝ", font=("Roboto", 12, "bold"), text_color="#a78bfa").pack(anchor="w", padx=15, pady=(15, 5))
        
        options_frame = ctk.CTkFrame(left_frame, fg_color="transparent")
        options_frame.pack(fill="x", padx=15, pady=5)
        
        self.script_line_mode_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(options_frame, text="Mỗi dòng = 1 voice riêng", 
                       variable=self.script_line_mode_var,
                       font=("Roboto", 11)).pack(anchor="w", pady=2)
        
        self.script_merge_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(options_frame, text="Hợp nhất tất cả thành 1 file", 
                       variable=self.script_merge_var,
                       font=("Roboto", 11)).pack(anchor="w", pady=2)

        # Workers setting
        workers_row = ctk.CTkFrame(options_frame, fg_color="transparent")
        workers_row.pack(fill="x", pady=5)
        ctk.CTkLabel(workers_row, text="Workers:", font=("Roboto", 11)).pack(side="left")
        self.script_workers_var = ctk.StringVar(value="5")
        ctk.CTkEntry(workers_row, textvariable=self.script_workers_var, width=60).pack(side="left", padx=5)
        
        # Live Session Mode checkbox - chỉ hiển thị khi chọn Google Gemini
        self.script_live_session_var = ctk.BooleanVar(value=False)
        self.script_live_session_chk = ctk.CTkCheckBox(
            options_frame, text="Live Session", 
            variable=self.script_live_session_var,
            font=("Roboto", 11))
        self.script_live_session_chk.pack(anchor="w", pady=2)

        # --- RIGHT: Input & Processing ---
        right_frame = ctk.CTkFrame(tab, fg_color="transparent")
        right_frame.grid(row=0, column=1, sticky="nsew", padx=(5, 0), pady=0)
        right_frame.grid_rowconfigure(2, weight=1)
        right_frame.grid_columnconfigure(0, weight=1)

        # Input Methods Section
        input_frame = ctk.CTkFrame(right_frame, fg_color="#1a1a2e")
        input_frame.grid(row=0, column=0, sticky="nsew", pady=(0, 5))

        ctk.CTkLabel(input_frame, text="📝 NHẬP VĂN BẢN KỊCH BẢN", font=("Roboto", 14, "bold"), text_color="#a78bfa").pack(anchor="w", padx=15, pady=(15, 5))
        ctk.CTkLabel(input_frame, text="Mỗi dòng văn bản sẽ tạo thành 1 file voice riêng biệt", font=("Roboto", 11), text_color="gray").pack(anchor="w", padx=15)

        # Text input area
        self.script_text_input = ctk.CTkTextbox(input_frame, height=100, font=("Roboto", 12))
        self.script_text_input.pack(fill="x", padx=15, pady=10)
        self.script_text_input.insert("1.0", "Dòng 1: Xin chào các bạn.\nDòng 2: Đây là video giới thiệu.\nDòng 3: Cảm ơn đã theo dõi.")

        # File/Folder selection
        file_row = ctk.CTkFrame(input_frame, fg_color="transparent")
        file_row.pack(fill="x", padx=15, pady=5)

        self.script_file_entry = ctk.CTkEntry(file_row, placeholder_text="Hoặc chọn file txt/docx hoặc thư mục...", width=300)
        self.script_file_entry.pack(side="left", fill="x", expand=True, padx=(0, 5))

        ctk.CTkButton(file_row, text="📂 File", width=60, command=self._script_browse_file).pack(side="left", padx=2)
        ctk.CTkButton(file_row, text="📁 Thư mục", width=80, command=self._script_browse_folder).pack(side="left", padx=2)

        # Output folder
        out_row = ctk.CTkFrame(input_frame, fg_color="transparent")
        out_row.pack(fill="x", padx=15, pady=5)

        self.script_output_entry = ctk.CTkEntry(out_row, placeholder_text="Thư mục output...")
        self.script_output_entry.insert(0, "./script_output")
        self.script_output_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))

        ctk.CTkButton(out_row, text="📁 Chọn", width=100, command=self._script_browse_output).pack(side="left")

        # Process buttons
        proc_btn_row = ctk.CTkFrame(input_frame, fg_color="transparent")
        proc_btn_row.pack(fill="x", padx=15, pady=10)

        self.btn_script_process = ctk.CTkButton(
            proc_btn_row, text="🚀 TẠO VOICE TỪ KỊCH BẢN", 
            fg_color="#7c3aed", hover_color="#6d28d9",
            font=("Roboto", 12, "bold"), height=40,
            command=self._script_process
        )
        self.btn_script_process.pack(side="left", padx=5)

        self.btn_script_stop = ctk.CTkButton(
            proc_btn_row, text="⏹ DỪNG", 
            fg_color="#64748b", state="disabled",
            command=self._script_stop
        )
        self.btn_script_stop.pack(side="left", padx=5)
        
        # Nút ghép all voice
        self.btn_script_merge_all = ctk.CTkButton(
            proc_btn_row, text="🔗 GHÉP ALL VOICE", 
            fg_color="#059669", hover_color="#047857",
            font=("Roboto", 11), height=40,
            command=self._script_merge_all_voices
        )
        self.btn_script_merge_all.pack(side="left", padx=15)

        # Progress
        self.script_progress = ctk.CTkProgressBar(input_frame)
        self.script_progress.set(0)
        self.script_progress.pack(fill="x", padx=15, pady=5)

        self.script_status = ctk.CTkLabel(input_frame, text="Sẵn sàng xử lý", text_color="gray")
        self.script_status.pack(anchor="w", padx=15, pady=(0, 10))

        # Generated Voice Preview Section
        preview_frame = ctk.CTkFrame(right_frame, fg_color="#1a1a2e")
        preview_frame.grid(row=1, column=0, sticky="nsew", pady=5)

        header_preview = ctk.CTkFrame(preview_frame, fg_color="#334155")
        header_preview.pack(fill="x")
        ctk.CTkLabel(header_preview, text="🔊 VOICE ĐÃ TẠO - NGHE THỬ", font=("Roboto", 12, "bold")).pack(side="left", padx=15, pady=8)
        
        ctk.CTkButton(header_preview, text="🔄 Làm mới", width=80, height=28, 
                     command=self._script_refresh_preview).pack(side="right", padx=5, pady=5)
        ctk.CTkButton(header_preview, text="⏹ Dừng phát", width=80, height=28, fg_color="#dc2626",
                     command=self.player.stop).pack(side="right", padx=5, pady=5)

        self.script_preview_list = ctk.CTkScrollableFrame(preview_frame, fg_color="#1f2937", height=150)
        self.script_preview_list.pack(fill="both", expand=True, padx=10, pady=10)

        # Log Section
        log_frame = ctk.CTkFrame(right_frame, fg_color="#0f0f1a")
        log_frame.grid(row=2, column=0, sticky="nsew")

        ctk.CTkLabel(log_frame, text="LOG", font=("Roboto", 12, "bold"), text_color="#a78bfa").pack(anchor="w", padx=15, pady=(10, 5))
        self.script_log = ctk.CTkTextbox(log_frame, font=("Consolas", 10), text_color="#22c55e", state="disabled")
        self.script_log.pack(fill="both", expand=True, padx=15, pady=(0, 15))

        # Store state
        self.script_processing = False
        self.script_generated_files = []

    def _script_log_msg(self, msg):
        """Add message to Script log"""
        self.script_log.configure(state="normal")
        self.script_log.insert("end", f"[{time.strftime('%H:%M:%S')}] {msg}\n")
        self.script_log.see("end")
        self.script_log.configure(state="disabled")

    def _script_populate_lang_filters(self):
        """Populate language filter options based on selected engine"""
        # Clear existing
        for widget in self.script_lang_scroll.winfo_children():
            widget.destroy()
        
        engine = self.script_engine_var.get()
        
        if engine == "edge":
            # Use Edge TTS language list
            languages = list(EDGE_TTS_LANGUAGE_MAP.keys())
        elif engine == "capcut":
            # Use Capcut language list
            languages = CAPCUT_LANGUAGES
        else:
            # Google Gemini doesn't have language filters
            languages = ["Tất cả"]
        
        # Reset to "Tất cả" when engine changes
        self.script_lang_var.set("Tất cả")
        
        for lang in languages:
            ctk.CTkRadioButton(
                self.script_lang_scroll,
                text=lang,
                variable=self.script_lang_var,
                value=lang,
                command=self._script_filter_voices,
                font=("Roboto", 10)
            ).pack(anchor="w", pady=2)

    def _script_filter_voices(self, _=None):
        """Filter voice list based on language and gender (called when filter value changes)"""
        self._script_update_voice_list(update_lang_filters=False)

    def _script_on_engine_change(self):
        """Called when the TTS engine is changed - updates both filters and voice list"""
        self._script_populate_lang_filters()
        self.script_gender_var.set("Tất cả")
        self._script_update_voice_list(update_lang_filters=False)

    def _script_update_voice_list(self, update_lang_filters=False):
        """Update voice list based on selected engine and filters"""
        # Clear existing
        for widget in self.script_voice_list.winfo_children():
            widget.destroy()
        
        engine = self.script_engine_var.get()
        lang_filter = self.script_lang_var.get()
        gender_filter = self.script_gender_var.get()
        
        # Update language filters only when explicitly requested (engine change)
        if update_lang_filters:
            self._script_populate_lang_filters()
        
        if engine == "edge":
            # Use Edge TTS voices with filtering
            voices = self.edge_voices_cache if self.edge_voices_cache else []
            if not voices:
                ctk.CTkLabel(self.script_voice_list, text="Đang tải voice list...", text_color="gray").pack(pady=10)
                # Trigger load if not loaded
                if not self.edge_voices_cache:
                    self.after(100, self._load_edge_voices)
                return
            
            # Get language code from display name
            lang_code = EDGE_TTS_LANGUAGE_MAP.get(lang_filter, "") if lang_filter != "Tất cả" else ""
            
            # Filter voices
            filtered_voices = []
            for voice in voices:
                voice_lang = voice.get('Language', '')
                voice_gender = voice.get('Gender', '')
                
                # Language filter
                if lang_code and voice_lang != lang_code:
                    continue
                
                # Gender filter (Edge uses "Male"/"Female")
                if gender_filter not in ["Tất cả", ""] and voice_gender != gender_filter:
                    continue
                
                filtered_voices.append(voice)
            
            # Limit to 100 for performance (increased from 50 because filtering reduces total count)
            for voice in filtered_voices[:100]:
                short_name = voice.get('ShortName', '')
                gender = voice.get('Gender', '')
                display = f"{short_name} ({gender})"
                
                rb = ctk.CTkRadioButton(
                    self.script_voice_list, 
                    text=display, 
                    variable=self.script_selected_voice, 
                    value=short_name,
                    font=("Roboto", 10)
                )
                rb.pack(anchor="w", pady=2)
                
        elif engine == "capcut":
            # Use Capcut voices with filtering
            voices = DEFAULT_CAPCUT_VOICES + self.capcut_custom_voices
            
            # Filter voices
            filtered_voices = []
            for voice in voices:
                voice_lang = voice.get('language', '')
                voice_gender = voice.get('gender', '')
                
                # Language filter
                if lang_filter != "Tất cả" and voice_lang != lang_filter:
                    continue
                
                # Gender filter (Capcut uses "Nam"/"Nữ"/"Khác")
                if gender_filter not in ["Tất cả", ""]:
                    # Map Male/Female to Nam/Nữ for consistency
                    mapped_filter = gender_filter
                    if gender_filter == "Male":
                        mapped_filter = "Nam"
                    elif gender_filter == "Female":
                        mapped_filter = "Nữ"
                    
                    if voice_gender != mapped_filter:
                        continue
                
                filtered_voices.append(voice)
            
            for voice in filtered_voices:
                voice_id = voice.get('voice_id', '')
                display = f"{voice.get('display_name', voice_id)} ({voice.get('gender', '?')})"
                
                rb = ctk.CTkRadioButton(
                    self.script_voice_list, 
                    text=display, 
                    variable=self.script_selected_voice, 
                    value=voice_id,
                    font=("Roboto", 10)
                )
                rb.pack(anchor="w", pady=2)
            
            # Set default Capcut voice
            if filtered_voices:
                self.script_selected_voice.set(filtered_voices[0].get('voice_id', 'BV074_streaming'))
                
        elif engine == "google":
            # Use Google Gemini voices (no filtering available)
            for voice in VOICES:
                rb = ctk.CTkRadioButton(
                    self.script_voice_list, 
                    text=voice, 
                    variable=self.script_selected_voice, 
                    value=voice,
                    font=("Roboto", 10)
                )
                rb.pack(anchor="w", pady=2)
            
            # Set default Google voice
            self.script_selected_voice.set("Kore")

    def _script_browse_file(self):
        """Browse for input file"""
        file_path = filedialog.askopenfilename(
            filetypes=[("Text files", "*.txt"), ("Word files", "*.docx"), ("All files", "*.*")]
        )
        if file_path:
            self.script_file_entry.delete(0, "end")
            self.script_file_entry.insert(0, file_path)
            try:
                content = read_document_file(file_path)
                lines = [l for l in content.strip().split('\n') if l.strip()]
                self._script_log_msg(f"📂 Đã chọn file: {os.path.basename(file_path)} ({len(lines)} dòng)")
            except Exception as e:
                self._script_log_msg(f"❌ Lỗi đọc file: {str(e)}")

    def _script_browse_folder(self):
        """Browse for folder containing txt/docx files"""
        dir_path = filedialog.askdirectory(title="Chọn thư mục chứa file txt/docx")
        if dir_path:
            self.script_file_entry.delete(0, "end")
            self.script_file_entry.insert(0, dir_path)
            # Count files
            txt_files = glob.glob(os.path.join(dir_path, "*.txt"))
            docx_files = glob.glob(os.path.join(dir_path, "*.docx"))
            total = len(txt_files) + len(docx_files)
            self._script_log_msg(f"📁 Đã chọn thư mục: {dir_path} ({total} file)")

    def _script_browse_output(self):
        """Browse for output directory"""
        dir_path = filedialog.askdirectory()
        if dir_path:
            self.script_output_entry.delete(0, "end")
            self.script_output_entry.insert(0, dir_path)

    def _script_refresh_preview(self):
        """Refresh the preview list with generated audio files"""
        # Clear existing
        for widget in self.script_preview_list.winfo_children():
            widget.destroy()
        
        output_dir = self.script_output_entry.get().strip()
        if not output_dir or not os.path.isdir(output_dir):
            ctk.CTkLabel(self.script_preview_list, text="Chưa có file audio", text_color="gray").pack(pady=10)
            return
        
        # Find all audio files (mp3 and wav)
        mp3_files = glob.glob(os.path.join(output_dir, "*.mp3"))
        wav_files = glob.glob(os.path.join(output_dir, "*.wav"))
        audio_files = sorted(mp3_files + wav_files)
        
        if not audio_files:
            ctk.CTkLabel(self.script_preview_list, text="Chưa có file audio", text_color="gray").pack(pady=10)
            return
        
        for audio_file in audio_files:
            file_name = os.path.basename(audio_file)
            file_size = os.path.getsize(audio_file) // 1024  # KB
            
            row = ctk.CTkFrame(self.script_preview_list, fg_color="#334155")
            row.pack(fill="x", pady=2, padx=5)
            
            ctk.CTkLabel(row, text=f"🎵 {file_name}", font=("Roboto", 10)).pack(side="left", padx=10, pady=5)
            ctk.CTkLabel(row, text=f"{file_size} KB", text_color="gray", font=("Roboto", 9)).pack(side="left", padx=5)
            
            ctk.CTkButton(
                row, text="▶", width=35, height=25, fg_color="#22c55e",
                command=lambda f=audio_file: self.player.play(f)
            ).pack(side="right", padx=5, pady=3)

    def _script_process(self):
        """Process script text/file to voice"""
        engine = self.script_engine_var.get()
        voice = self.script_selected_voice.get()
        output_dir = self.script_output_entry.get().strip()
        line_mode = self.script_line_mode_var.get()
        merge_after = self.script_merge_var.get()
        
        if not output_dir:
            messagebox.showerror("Lỗi", "Vui lòng chọn thư mục output!")
            return
        
        os.makedirs(output_dir, exist_ok=True)
        
        # Get text content
        input_path = self.script_file_entry.get().strip()
        if input_path and os.path.exists(input_path):
            if os.path.isdir(input_path):
                # Process folder
                self._script_process_folder(input_path, output_dir, engine, voice, line_mode, merge_after)
                return
            else:
                # Read from file
                try:
                    text_content = read_document_file(input_path)
                except Exception as e:
                    messagebox.showerror("Lỗi", f"Không thể đọc file: {e}")
                    return
        else:
            # Get from text area
            text_content = self.script_text_input.get("1.0", "end").strip()
        
        if not text_content:
            messagebox.showerror("Lỗi", "Vui lòng nhập văn bản hoặc chọn file!")
            return
        
        # Split by lines if line_mode is enabled
        if line_mode:
            # Clean each line and filter empty lines
            lines = [clean_text_for_tts(l) for l in text_content.split('\n') if l.strip()]
        else:
            # Clean full text
            lines = [clean_text_for_tts(text_content)]
        
        if not lines:
            messagebox.showerror("Lỗi", "Không có nội dung để xử lý!")
            return
        
        # Validate engine-specific requirements
        if engine == "capcut":
            session_id = self.entry_capcut_session.get().strip() if hasattr(self, 'entry_capcut_session') else self.capcut_session_id
            if not session_id:
                messagebox.showerror("Lỗi", "Vui lòng nhập Capcut Session ID trong tab Cài đặt!")
                self.tabview.set("⚙️ Configuration")
                return
        elif engine == "google":
            api_keys = self._get_api_keys()
            if not api_keys:
                messagebox.showerror("Lỗi", "Vui lòng nhập API key trong tab Cài đặt!")
                self.tabview.set("⚙️ Configuration")
                return
        
        # Start processing
        self.script_processing = True
        self.btn_script_process.configure(state="disabled")
        self.btn_script_stop.configure(state="normal")
        self.script_progress.set(0)
        self.script_generated_files = []
        
        threading.Thread(
            target=self._script_worker,
            args=(lines, output_dir, engine, voice, merge_after),
            daemon=True
        ).start()

    def _script_process_folder(self, folder_path, output_dir, engine, voice, line_mode, merge_after):
        """Process a folder of files"""
        # Find all supported files
        txt_files = glob.glob(os.path.join(folder_path, "*.txt"))
        docx_files = glob.glob(os.path.join(folder_path, "*.docx"))
        all_files = sorted(txt_files + docx_files)
        
        if not all_files:
            messagebox.showerror("Lỗi", "Không tìm thấy file txt/docx trong thư mục!")
            return
        
        # Validate engine-specific requirements
        if engine == "capcut":
            session_id = self.entry_capcut_session.get().strip() if hasattr(self, 'entry_capcut_session') else self.capcut_session_id
            if not session_id:
                messagebox.showerror("Lỗi", "Vui lòng nhập Capcut Session ID trong tab Cài đặt!")
                self.tabview.set("⚙️ Configuration")
                return
        elif engine == "google":
            api_keys = self._get_api_keys()
            if not api_keys:
                messagebox.showerror("Lỗi", "Vui lòng nhập API key trong tab Cài đặt!")
                self.tabview.set("⚙️ Configuration")
                return
        
        # Start processing
        self.script_processing = True
        self.btn_script_process.configure(state="disabled")
        self.btn_script_stop.configure(state="normal")
        self.script_progress.set(0)
        self.script_generated_files = []
        
        threading.Thread(
            target=self._script_folder_worker,
            args=(all_files, output_dir, engine, voice, line_mode, merge_after),
            daemon=True
        ).start()

    def _script_worker(self, lines, output_dir, engine, voice, merge_after):
        """Worker thread for processing script lines"""
        try:
            total = len(lines)
            self.after(0, lambda: self._script_log_msg(f"🚀 Bắt đầu xử lý {total} dòng với engine: {engine}"))
            self.after(0, lambda: self.script_status.configure(text=f"Đang xử lý 0/{total}"))
            
            success_count = 0
            failed_count = 0
            result_files = []
            ffmpeg_path = self.ffmpeg_path if hasattr(self, 'ffmpeg_path') else get_default_ffmpeg_path()
            
            for idx, line in enumerate(lines):
                if not self.script_processing:
                    self.after(0, lambda: self._script_log_msg("⏹ Đã dừng bởi người dùng"))
                    break
                
                self.after(0, lambda i=idx+1, t=line[:30]: self._script_log_msg(f"📝 [{i}] Đang xử lý: {t}..."))
                
                # Determine output file extension based on engine
                ext = ".wav" if engine == "google" else ".mp3"
                output_file = os.path.join(output_dir, f"{idx+1:04d}{ext}")
                
                try:
                    if engine == "edge":
                        success = self._script_generate_edge(line, voice, output_file, ffmpeg_path)
                    elif engine == "capcut":
                        success = self._script_generate_capcut(line, voice, output_file, ffmpeg_path)
                    elif engine == "google":
                        success = self._script_generate_google(line, voice, output_file)
                    else:
                        success = False
                    
                    if success:
                        success_count += 1
                        result_files.append(output_file)
                        self.after(0, lambda i=idx+1: self._script_log_msg(f"✅ [{i}] Thành công"))
                    else:
                        failed_count += 1
                        self.after(0, lambda i=idx+1: self._script_log_msg(f"❌ [{i}] Thất bại"))
                        
                except Exception as e:
                    failed_count += 1
                    self.after(0, lambda i=idx+1, err=str(e): self._script_log_msg(f"❌ [{i}] Lỗi: {err}"))
                
                # Update progress
                progress = (idx + 1) / total
                self.after(0, lambda p=progress: self.script_progress.set(p))
                self.after(0, lambda c=idx+1, t=total: self.script_status.configure(text=f"Đang xử lý {c}/{t}"))
            
            # Merge if requested
            if merge_after and result_files:
                merged_file = os.path.join(output_dir, "_merged" + ext)
                self.after(0, lambda: self._script_log_msg(f"🔧 Đang hợp nhất {len(result_files)} file..."))
                
                if ext == ".mp3":
                    merge_success = merge_mp3_files_ffmpeg(result_files, merged_file, ffmpeg_path)
                else:
                    merge_success = merge_wav_files_ffmpeg(result_files, merged_file, ffmpeg_path)
                
                if merge_success:
                    self.after(0, lambda: self._script_log_msg(f"✅ Đã hợp nhất: {merged_file}"))
                else:
                    self.after(0, lambda: self._script_log_msg(f"❌ Lỗi hợp nhất file!"))
            
            self.script_generated_files = result_files
            
            self.after(0, lambda: self._script_log_msg(f"\n{'='*40}"))
            self.after(0, lambda s=success_count, t=total, f=failed_count: 
                      self._script_log_msg(f"✅ Hoàn thành! Thành công: {s}/{t}, Thất bại: {f}"))
            self.after(0, lambda: self._script_log_msg(f"📁 Files đã lưu tại: {output_dir}"))
            
            # Refresh preview
            self.after(100, self._script_refresh_preview)
            
        except Exception as e:
            import traceback
            self.after(0, lambda: self._script_log_msg(f"❌ Lỗi: {str(e)}"))
            self.after(0, lambda tb=traceback.format_exc(): self._script_log_msg(f"[DEBUG] Traceback:\n{tb}"))
        finally:
            self.script_processing = False
            self.after(0, lambda: self.btn_script_process.configure(state="normal"))
            self.after(0, lambda: self.btn_script_stop.configure(state="disabled"))
            self.after(0, lambda: self.script_status.configure(text="Hoàn thành!"))

    def _script_folder_worker(self, all_files, output_dir, engine, voice, line_mode, merge_after):
        """Worker thread for processing folder of files"""
        try:
            total_files = len(all_files)
            self.after(0, lambda: self._script_log_msg(f"🚀 Bắt đầu xử lý {total_files} file với engine: {engine}"))
            
            all_output_files = []
            ffmpeg_path = self.ffmpeg_path if hasattr(self, 'ffmpeg_path') else get_default_ffmpeg_path()
            
            for file_idx, file_path in enumerate(all_files):
                if not self.script_processing:
                    self.after(0, lambda: self._script_log_msg("⏹ Đã dừng bởi người dùng"))
                    break
                
                file_name = os.path.basename(file_path)
                base_name = os.path.splitext(file_name)[0]
                
                self.after(0, lambda f=file_name, i=file_idx+1, t=total_files: 
                          self._script_log_msg(f"\n📄 [{i}/{t}] Đang xử lý: {f}"))
                
                try:
                    content = read_document_file(file_path)
                    if not content.strip():
                        self.after(0, lambda: self._script_log_msg(f"  ⚠️ File trống, bỏ qua"))
                        continue
                    
                    # Split by lines if line_mode is enabled, and clean each line
                    if line_mode:
                        lines = [clean_text_for_tts(l) for l in content.split('\n') if l.strip()]
                    else:
                        lines = [clean_text_for_tts(content)]
                    
                    self.after(0, lambda n=len(lines): self._script_log_msg(f"  📝 Tìm thấy {n} dòng"))
                    
                    # Create subfolder for this file
                    file_output_dir = os.path.join(output_dir, base_name)
                    os.makedirs(file_output_dir, exist_ok=True)
                    
                    file_results = []
                    ext = ".wav" if engine == "google" else ".mp3"
                    
                    for idx, line in enumerate(lines):
                        if not self.script_processing:
                            break
                        
                        output_file = os.path.join(file_output_dir, f"{idx+1:04d}{ext}")
                        
                        try:
                            if engine == "edge":
                                success = self._script_generate_edge(line, voice, output_file, ffmpeg_path)
                            elif engine == "capcut":
                                success = self._script_generate_capcut(line, voice, output_file, ffmpeg_path)
                            elif engine == "google":
                                success = self._script_generate_google(line, voice, output_file)
                            else:
                                success = False
                            
                            if success:
                                file_results.append(output_file)
                        except Exception as e:
                            self.after(0, lambda err=str(e), i=idx+1: self._script_log_msg(f"  ❌ Dòng [{i}] lỗi: {err}"))
                    
                    # Merge for this file if requested
                    if merge_after and file_results:
                        merged_file = os.path.join(output_dir, f"{base_name}{ext}")
                        if ext == ".mp3":
                            merge_success = merge_mp3_files_ffmpeg(file_results, merged_file, ffmpeg_path)
                        else:
                            merge_success = merge_wav_files_ffmpeg(file_results, merged_file, ffmpeg_path)
                        
                        if merge_success:
                            self.after(0, lambda f=merged_file: self._script_log_msg(f"  ✅ Đã tạo: {os.path.basename(f)}"))
                            all_output_files.append(merged_file)
                    else:
                        all_output_files.extend(file_results)
                    
                except Exception as e:
                    self.after(0, lambda err=str(e): self._script_log_msg(f"  ❌ Lỗi: {err}"))
                
                # Update progress
                progress = (file_idx + 1) / total_files
                self.after(0, lambda p=progress: self.script_progress.set(p))
                self.after(0, lambda i=file_idx+1, t=total_files: 
                          self.script_status.configure(text=f"Đang xử lý file {i}/{t}"))
            
            self.script_generated_files = all_output_files
            
            self.after(0, lambda: self._script_log_msg(f"\n{'='*40}"))
            self.after(0, lambda n=len(all_output_files), t=total_files: 
                      self._script_log_msg(f"✅ Hoàn thành! Đã tạo {n} file từ {t} file gốc"))
            self.after(0, lambda: self._script_log_msg(f"📁 Files đã lưu tại: {output_dir}"))
            
            # Refresh preview
            self.after(100, self._script_refresh_preview)
            
        except Exception as e:
            import traceback
            self.after(0, lambda: self._script_log_msg(f"❌ Lỗi: {str(e)}"))
            self.after(0, lambda tb=traceback.format_exc(): self._script_log_msg(f"[DEBUG] Traceback:\n{tb}"))
        finally:
            self.script_processing = False
            self.after(0, lambda: self.btn_script_process.configure(state="normal"))
            self.after(0, lambda: self.btn_script_stop.configure(state="disabled"))
            self.after(0, lambda: self.script_status.configure(text="Hoàn thành!"))

    def _script_generate_edge(self, text, voice, output_file, ffmpeg_path):
        """Generate voice using Edge TTS - với retry logic"""
        from edge.communicate import Communicate
        
        # RETRY LOGIC - tự động retry khi có lỗi bất kỳ
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                # Check if text is long - need chunking
                if len(text) > EDGE_LONG_TEXT_THRESHOLD:
                    chunks = split_text_smart(text, max_chars=EDGE_MAX_CHUNK_SIZE)
                    temp_dir = os.path.join(os.path.dirname(output_file), "_temp_edge_chunks")
                    os.makedirs(temp_dir, exist_ok=True)
                    
                    chunk_files = []
                    for chunk in chunks:
                        chunk_file = os.path.join(temp_dir, f"chunk_{chunk.index:04d}.mp3")
                        
                        # Retry cho mỗi chunk
                        chunk_success = False
                        for chunk_attempt in range(1, MAX_RETRIES + 1):
                            try:
                                communicate = Communicate(chunk.text, voice)
                                loop = asyncio.new_event_loop()
                                asyncio.set_event_loop(loop)
                                try:
                                    loop.run_until_complete(communicate.save(chunk_file))
                                finally:
                                    cleanup_event_loop(loop)
                                
                                if os.path.exists(chunk_file) and os.path.getsize(chunk_file) > MIN_AUDIO_FILE_SIZE:
                                    chunk_files.append(chunk_file)
                                    chunk_success = True
                                    break
                            except Exception as chunk_e:
                                if chunk_attempt < MAX_RETRIES:
                                    delay = calculate_retry_delay(chunk_attempt, is_connection_error(str(chunk_e)))
                                    time.sleep(delay)
                        
                        if not chunk_success:
                            raise ValueError(f"Chunk {chunk.index} failed after {MAX_RETRIES} attempts")
                    
                    if chunk_files:
                        merge_success = merge_mp3_files_ffmpeg(chunk_files, output_file, ffmpeg_path)
                        # Cleanup
                        for cf in chunk_files:
                            try:
                                os.remove(cf)
                            except:
                                pass
                        try:
                            os.rmdir(temp_dir)
                        except:
                            pass
                        
                        if merge_success and os.path.exists(output_file) and os.path.getsize(output_file) > MIN_AUDIO_FILE_SIZE:
                            return True
                        raise ValueError("Merge failed or output file invalid")
                    raise ValueError("No chunk files generated")
                else:
                    communicate = Communicate(text, voice)
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    try:
                        loop.run_until_complete(communicate.save(output_file))
                    finally:
                        cleanup_event_loop(loop)
                    
                    if os.path.exists(output_file) and os.path.getsize(output_file) > MIN_AUDIO_FILE_SIZE:
                        return True
                    raise ValueError("Output file empty or not created")
                    
            except Exception as e:
                if attempt < MAX_RETRIES:
                    delay = calculate_retry_delay(attempt, is_connection_error(str(e)))
                    print(f"Edge TTS attempt {attempt}/{MAX_RETRIES} failed: {e}, retrying in {delay:.1f}s...")
                    time.sleep(delay)
                else:
                    print(f"Edge TTS error after {MAX_RETRIES} attempts: {e}")
                    return False
        return False

    def _script_generate_capcut(self, text, voice, output_file, ffmpeg_path):
        """Generate voice using Capcut TTS - với retry logic"""
        session_id = self.entry_capcut_session.get().strip() if hasattr(self, 'entry_capcut_session') else self.capcut_session_id
        
        # RETRY LOGIC - tự động retry khi có lỗi bất kỳ
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                # Check if text is long - need chunking
                if len(text) > CAPCUT_LONG_TEXT_THRESHOLD:
                    chunks = split_text_smart(text, max_chars=CAPCUT_MAX_CHUNK_SIZE)
                    temp_dir = os.path.join(os.path.dirname(output_file), "_temp_capcut_chunks")
                    os.makedirs(temp_dir, exist_ok=True)
                    
                    chunk_files = []
                    for chunk in chunks:
                        chunk_file = os.path.join(temp_dir, f"chunk_{chunk.index:04d}.mp3")
                        
                        # Retry cho mỗi chunk
                        chunk_success = False
                        for chunk_attempt in range(1, MAX_RETRIES + 1):
                            success, error = capcut_create_tts(chunk.text, voice, session_id, chunk_file, debug=False)
                            
                            if success and os.path.exists(chunk_file) and os.path.getsize(chunk_file) > MIN_AUDIO_FILE_SIZE:
                                chunk_files.append(chunk_file)
                                chunk_success = True
                                break
                            else:
                                if chunk_attempt < MAX_RETRIES:
                                    err_msg = error.get('error', 'Unknown') if error else 'Unknown'
                                    delay = calculate_retry_delay(chunk_attempt, is_connection_error(err_msg))
                                    time.sleep(delay)
                        
                        if not chunk_success:
                            raise ValueError(f"Chunk {chunk.index} failed after {MAX_RETRIES} attempts")
                        
                        time.sleep(CAPCUT_RATE_LIMIT_DELAY)
                    
                    if chunk_files:
                        merge_success = merge_mp3_files_ffmpeg(chunk_files, output_file, ffmpeg_path)
                        # Cleanup
                        for cf in chunk_files:
                            try:
                                os.remove(cf)
                            except:
                                pass
                        try:
                            os.rmdir(temp_dir)
                        except:
                            pass
                        
                        if merge_success and os.path.exists(output_file) and os.path.getsize(output_file) > MIN_AUDIO_FILE_SIZE:
                            return True
                        raise ValueError("Merge failed or output file invalid")
                    raise ValueError("No chunk files generated")
                else:
                    success, error = capcut_create_tts(text, voice, session_id, output_file, debug=False)
                    
                    if success and os.path.exists(output_file) and os.path.getsize(output_file) > MIN_AUDIO_FILE_SIZE:
                        return True
                    
                    err_msg = error.get('error', 'Unknown') if error else 'Unknown'
                    raise ValueError(f"Capcut TTS failed: {err_msg}")
                    
            except Exception as e:
                if attempt < MAX_RETRIES:
                    delay = calculate_retry_delay(attempt, is_connection_error(str(e)))
                    print(f"Capcut TTS attempt {attempt}/{MAX_RETRIES} failed: {e}, retrying in {delay:.1f}s...")
                    time.sleep(delay)
                else:
                    print(f"Capcut TTS error after {MAX_RETRIES} attempts: {e}")
                    return False
        return False

    def _script_generate_google(self, text, voice, output_file):
        """Generate voice using Google Gemini TTS - với retry logic và hỗ trợ Live Session"""
        api_keys = self._get_api_keys()
        if not api_keys:
            return False
        
        # Get live_session_enabled from checkbox
        live_session_enabled = self.script_live_session_var.get() if hasattr(self, 'script_live_session_var') else False
        
        config = TTSConfig(
            voice=voice,
            media_resolution="MEDIA_RESOLUTION_MEDIUM",
            speed=1.0,
            system_instruction=self.txt_sys_instr.get("1.0", "end").strip(),
            live_session_enabled=live_session_enabled
        )
        
        # RETRY LOGIC - tự động retry khi có lỗi bất kỳ
        for attempt in range(1, MAX_RETRIES + 1):
            loop = None
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                # Sử dụng LiveSessionWorkerEngine nếu live_session_enabled
                if live_session_enabled:
                    async def generate_with_live_session():
                        engine = LiveSessionWorkerEngine(0, api_keys[0], config, log_callback=print)
                        await engine.connect()
                        audio_data = await engine.generate_audio(text)
                        await engine.disconnect()
                        return audio_data
                    audio_data = loop.run_until_complete(generate_with_live_session())
                else:
                    engine = WorkerEngine(0, api_keys[0], config)
                    audio_data = loop.run_until_complete(engine.generate_audio(text))
                
                # Check for None first to avoid AttributeError on len()
                if audio_data is None:
                    raise ValueError("No audio data received (None)")
                
                if len(audio_data) > MIN_AUDIO_FILE_SIZE:
                    final_rate = int(RECEIVE_SAMPLE_RATE * config.speed)
                    save_wave_file(output_file, audio_data, rate=final_rate)
                    
                    if os.path.exists(output_file) and os.path.getsize(output_file) > MIN_AUDIO_FILE_SIZE:
                        return True
                    raise ValueError("Output file empty or not created")
                raise ValueError(f"Received insufficient audio data: {len(audio_data)} bytes")
                
            except Exception as e:
                if attempt < MAX_RETRIES:
                    delay = calculate_retry_delay(attempt, is_connection_error(str(e)))
                    print(f"Google TTS attempt {attempt}/{MAX_RETRIES} failed: {e}, retrying in {delay:.1f}s...")
                    time.sleep(delay)
                else:
                    print(f"Google TTS error after {MAX_RETRIES} attempts: {e}")
                    return False
            finally:
                if loop:
                    cleanup_event_loop(loop)
        return False

    def _script_stop(self):
        """Stop script processing"""
        self.script_processing = False
        self._script_log_msg("⏹ Đang dừng...")

    def _script_merge_all_voices(self):
        """
        Ghép tất cả voice trong thư mục output theo thứ tự đúng.
        - Nếu có nhiều thư mục con (từ xử lý folder), ghép mỗi thư mục riêng
        - Đặt tên theo tệp input gốc
        """
        output_dir = self.script_output_entry.get().strip()
        if not output_dir or not os.path.isdir(output_dir):
            messagebox.showerror("Lỗi", "Thư mục output không tồn tại!")
            return
        
        ffmpeg_path = self.ffmpeg_path if hasattr(self, 'ffmpeg_path') else get_default_ffmpeg_path()
        
        self._script_log_msg("🔗 Bắt đầu ghép all voice...")
        
        def merge_worker():
            try:
                # Tìm tất cả thư mục con (nếu có)
                subdirs = [d for d in os.listdir(output_dir) 
                          if os.path.isdir(os.path.join(output_dir, d)) and not d.startswith('_temp')]
                
                merged_files = []
                
                if subdirs:
                    # Có thư mục con -> xử lý từng thư mục con (từ folder input)
                    self.after(0, lambda: self._script_log_msg(f"📁 Tìm thấy {len(subdirs)} thư mục con"))
                    
                    for subdir in sorted(subdirs):
                        subdir_path = os.path.join(output_dir, subdir)
                        
                        # Tìm audio files trong thư mục con
                        mp3_files = sorted(glob.glob(os.path.join(subdir_path, "*.mp3")))
                        wav_files = sorted(glob.glob(os.path.join(subdir_path, "*.wav")))
                        
                        audio_files = mp3_files if mp3_files else wav_files
                        
                        if not audio_files:
                            self.after(0, lambda s=subdir: self._script_log_msg(f"  ⚠️ {s}: Không có audio file"))
                            continue
                        
                        # Ghép thành 1 file với tên thư mục
                        ext = ".mp3" if mp3_files else ".wav"
                        merged_file = os.path.join(output_dir, f"{subdir}{ext}")
                        
                        self.after(0, lambda s=subdir, n=len(audio_files): 
                                  self._script_log_msg(f"  🔧 {s}: Đang ghép {n} file..."))
                        
                        if ext == ".mp3":
                            success = merge_mp3_files_ffmpeg(audio_files, merged_file, ffmpeg_path)
                        else:
                            success = merge_wav_files_ffmpeg(audio_files, merged_file, ffmpeg_path)
                        
                        if success:
                            merged_files.append(merged_file)
                            self.after(0, lambda s=subdir: self._script_log_msg(f"  ✅ {s}: Đã ghép"))
                        else:
                            self.after(0, lambda s=subdir: self._script_log_msg(f"  ❌ {s}: Lỗi ghép"))
                else:
                    # Không có thư mục con -> ghép tất cả audio trong output_dir
                    mp3_files = sorted(glob.glob(os.path.join(output_dir, "*.mp3")))
                    wav_files = sorted(glob.glob(os.path.join(output_dir, "*.wav")))
                    
                    # Loại bỏ các file đã merge trước đó (bắt đầu bằng _ và chứa merged)
                    # Sử dụng pattern chặt chẽ hơn: file bắt đầu bằng _ được coi là file merged
                    def is_merged_file(f):
                        basename = os.path.basename(f)
                        # File merged bắt đầu bằng _ (ví dụ: _all_merged.mp3, _merged.wav)
                        return basename.startswith('_')
                    
                    audio_files = [f for f in (mp3_files if mp3_files else wav_files) 
                                  if not is_merged_file(f)]
                    
                    if not audio_files:
                        self.after(0, lambda: self._script_log_msg("⚠️ Không có audio file để ghép!"))
                        return
                    
                    ext = ".mp3" if mp3_files else ".wav"
                    merged_file = os.path.join(output_dir, f"_all_merged{ext}")
                    
                    self.after(0, lambda n=len(audio_files): self._script_log_msg(f"🔧 Đang ghép {n} file..."))
                    
                    if ext == ".mp3":
                        success = merge_mp3_files_ffmpeg(audio_files, merged_file, ffmpeg_path)
                    else:
                        success = merge_wav_files_ffmpeg(audio_files, merged_file, ffmpeg_path)
                    
                    if success:
                        merged_files.append(merged_file)
                        self.after(0, lambda f=merged_file: self._script_log_msg(f"✅ Đã ghép: {os.path.basename(f)}"))
                    else:
                        self.after(0, lambda: self._script_log_msg("❌ Lỗi ghép file!"))
                
                # Summary
                self.after(0, lambda: self._script_log_msg(f"\n{'='*40}"))
                self.after(0, lambda n=len(merged_files): self._script_log_msg(f"✅ Hoàn thành! Đã tạo {n} file merged"))
                
                # Refresh preview
                self.after(100, self._script_refresh_preview)
                
            except Exception as e:
                import traceback
                self.after(0, lambda err=str(e): self._script_log_msg(f"❌ Lỗi: {err}"))
                self.after(0, lambda tb=traceback.format_exc(): print(f"[DEBUG] Traceback:\n{tb}"))
        
        threading.Thread(target=merge_worker, daemon=True).start()

    # ==========================================================================
    # CAPCUT VOICE HELPER METHODS
    # ==========================================================================
    def _update_capcut_session_display(self):
        """Update the session ID display"""
        if hasattr(self, 'capcut_session_display'):
            session = self.capcut_session_id if self.capcut_session_id else "Chưa cài đặt"
            if len(session) > 20:
                session = session[:10] + "..." + session[-10:]
            self.capcut_session_display.configure(text=session)

    def _populate_capcut_voice_list(self, voices=None):
        """Populate the Capcut voice list with radio buttons"""
        # Clear existing
        for widget in self.capcut_voice_list.winfo_children():
            widget.destroy()
        
        # Get voices
        if voices is None:
            voices = DEFAULT_CAPCUT_VOICES + self.capcut_custom_voices
        
        for voice in voices:
            voice_id = voice.get('voice_id', '')
            display = f"{voice.get('display_name', voice_id)} ({voice.get('gender', '?')})"
            
            rb = ctk.CTkRadioButton(
                self.capcut_voice_list, 
                text=display, 
                variable=self.capcut_selected_voice, 
                value=voice_id,
                font=("Roboto", 10)
            )
            rb.pack(anchor="w", pady=2)

    def _filter_capcut_voices(self, _=None):
        """Filter Capcut voices based on language and gender"""
        # SỬA: Lấy giá trị từ biến StringVar thay vì ComboBox.get()
        lang = self.capcut_lang_var.get() 
        gender = self.capcut_gender_filter.get()
        
        all_voices = DEFAULT_CAPCUT_VOICES + self.capcut_custom_voices
        filtered = []
        
        for voice in all_voices:
            if lang != "Tất cả" and voice.get('language', '') != lang:
                continue
            if gender != "Tất cả" and voice.get('gender', '') != gender:
                continue
            filtered.append(voice)
        
        self._populate_capcut_voice_list(filtered)

    def _capcut_log(self, msg):
        """Add message to Capcut log"""
        self.capcut_log.configure(state="normal")
        self.capcut_log.insert("end", f"[{time.strftime('%H:%M:%S')}] {msg}\n")
        self.capcut_log.see("end")
        self.capcut_log.configure(state="disabled")

    def _capcut_generate(self):
        """Generate audio using Capcut TTS - supports long text with chunking"""
        # Get session ID from settings
        session_id = self.entry_capcut_session.get().strip() if hasattr(self, 'entry_capcut_session') else self.capcut_session_id
        
        # Debug logging - mask session ID for security
        self._capcut_log(f"[DEBUG] Starting single text TTS generation...")
        masked_session = f"{session_id[:4]}****({len(session_id)} chars)" if session_id and len(session_id) > 4 else "****" if session_id else "No"
        self._capcut_log(f"[DEBUG] Session ID loaded: {masked_session}")
        
        if not session_id:
            messagebox.showerror("Lỗi", "Vui lòng nhập Session ID trong tab Cài đặt!")
            self.tabview.set("⚙️ Configuration")
            return
        
        raw_text = self.capcut_text_input.get("1.0", "end").strip()
        if not raw_text:
            messagebox.showerror("Lỗi", "Vui lòng nhập văn bản!")
            return
        
        # Clean text: remove extra whitespace and newlines
        text = clean_text_for_tts(raw_text)
        
        voice_id = self.capcut_selected_voice.get()
        self._capcut_log(f"[DEBUG] Voice ID: {voice_id}")
        self._capcut_log(f"[DEBUG] Text length: {len(text)} chars (cleaned from {len(raw_text)})")
        self._capcut_log(f"Đang tạo audio với voice: {voice_id}")
        self.capcut_status_lbl.configure(text="Đang xử lý...")
        self.btn_capcut_generate.configure(state="disabled")
        
        # Get ffmpeg path from settings
        ffmpeg_path = getattr(self, 'ffmpeg_path', get_default_ffmpeg_path())
        
        def generate_thread():
            try:
                app_dir = os.path.dirname(os.path.abspath(__file__))
                
                # Check if text is long - need chunking
                if len(text) > CAPCUT_LONG_TEXT_THRESHOLD:
                    self.after(0, lambda: self._capcut_log(f"📝 Văn bản dài ({len(text)} chars) - Đang chia thành chunks..."))
                    
                    # Split into chunks
                    chunks = split_text_smart(text, max_chars=CAPCUT_MAX_CHUNK_SIZE)
                    self.after(0, lambda c=len(chunks): self._capcut_log(f"📝 Chia thành {c} chunks"))
                    
                    # Create temp directory
                    temp_dir = os.path.join(app_dir, "_temp_capcut_chunks")
                    os.makedirs(temp_dir, exist_ok=True)
                    
                    chunk_files = []
                    success_count = 0
                    
                    for chunk in chunks:
                        chunk_file = os.path.join(temp_dir, f"chunk_{chunk.index:04d}.mp3")
                        self.after(0, lambda i=chunk.index, t=chunk.text[:30]: self._capcut_log(f"  [{i}] {t}..."))
                        
                        success, error = capcut_create_tts(chunk.text, voice_id, session_id, chunk_file, debug=False)
                        
                        if success:
                            chunk_files.append(chunk_file)
                            success_count += 1
                        else:
                            err_msg = error.get('error', 'Unknown') if error else 'Unknown'
                            self.after(0, lambda e=err_msg, i=chunk.index: self._capcut_log(f"  ❌ Chunk [{i}] lỗi: {e}"))
                        
                        time.sleep(CAPCUT_RATE_LIMIT_DELAY)
                    
                    if chunk_files:
                        # Merge all chunks
                        output_file = os.path.join(app_dir, "_temp_capcut.mp3")
                        self.after(0, lambda: self._capcut_log(f"🔧 Đang ghép {len(chunk_files)} chunks..."))
                        
                        merge_success = merge_mp3_files_ffmpeg(chunk_files, output_file, ffmpeg_path)
                        
                        if merge_success:
                            self.capcut_temp_audio = output_file
                            self.after(0, lambda: self._capcut_log(f"✅ Tạo audio thành công! ({success_count} chunks)"))
                            self.after(0, lambda: self.capcut_status_lbl.configure(text="Hoàn thành!"))
                            self.after(0, lambda: self.btn_capcut_play.configure(state="normal"))
                            self.after(0, lambda: self.btn_capcut_save.configure(state="normal"))
                            
                            # Cleanup temp chunks
                            for f in chunk_files:
                                try:
                                    os.remove(f)
                                except:
                                    pass
                            try:
                                os.rmdir(temp_dir)
                            except:
                                pass
                        else:
                            self.after(0, lambda: self._capcut_log(f"❌ Lỗi ghép file! Kiểm tra đường dẫn ffmpeg."))
                            self.after(0, lambda: self.capcut_status_lbl.configure(text="Lỗi ghép file!"))
                    else:
                        self.after(0, lambda: self._capcut_log(f"❌ Không có chunk nào thành công!"))
                        self.after(0, lambda: self.capcut_status_lbl.configure(text="Lỗi!"))
                else:
                    # Short text - process directly
                    output_file = os.path.join(app_dir, "_temp_capcut.mp3")
                    self.after(0, lambda: self._capcut_log(f"[DEBUG] Output file: {output_file}"))
                    
                    success, error = capcut_create_tts(text, voice_id, session_id, output_file, debug=True)
                    
                    if success:
                        self.capcut_temp_audio = output_file
                        self.after(0, lambda: self._capcut_log(f"✅ Tạo audio thành công!"))
                        self.after(0, lambda: self.capcut_status_lbl.configure(text="Hoàn thành!"))
                        self.after(0, lambda: self.btn_capcut_play.configure(state="normal"))
                        self.after(0, lambda: self.btn_capcut_save.configure(state="normal"))
                    else:
                        err_msg = error.get('error', 'Unknown') if error else 'Unknown error'
                        self.after(0, lambda e=err_msg: self._capcut_log(f"❌ Lỗi: {e}"))
                        self.after(0, lambda: self.capcut_status_lbl.configure(text="Lỗi!"))
                        
            except Exception as e:
                import traceback
                self.after(0, lambda: self._capcut_log(f"❌ Exception: {str(e)}"))
                self.after(0, lambda tb=traceback.format_exc(): self._capcut_log(f"[DEBUG] Traceback:\n{tb}"))
            finally:
                self.after(0, lambda: self.btn_capcut_generate.configure(state="normal"))
        
        threading.Thread(target=generate_thread, daemon=True).start()

    def _capcut_play(self):
        """Play the generated Capcut audio"""
        if self.capcut_temp_audio and os.path.exists(self.capcut_temp_audio):
            self.player.play(self.capcut_temp_audio)
            self._capcut_log("▶ Đang phát audio...")

    def _capcut_save(self):
        """Save the Capcut audio to a file"""
        if not self.capcut_temp_audio or not os.path.exists(self.capcut_temp_audio):
            return
        
        file_path = filedialog.asksaveasfilename(
            defaultextension=".mp3",
            filetypes=[("MP3 files", "*.mp3"), ("All files", "*.*")]
        )
        if file_path:
            shutil.copy(self.capcut_temp_audio, file_path)
            self._capcut_log(f"💾 Đã lưu: {file_path}")

    # ==========================================================================
    # CAPCUT SRT/VTT PROCESSING METHODS
    # ==========================================================================
    def _capcut_browse_srt(self):
        """Browse for SRT/VTT file"""
        file_path = filedialog.askopenfilename(
            filetypes=[("Subtitle files", "*.srt *.vtt"), ("Text files", "*.txt"), ("Word files", "*.docx"), ("SRT files", "*.srt"), ("VTT files", "*.vtt"), ("All files", "*.*")]
        )
        if file_path:
            self.capcut_srt_file_entry.delete(0, "end")
            self.capcut_srt_file_entry.insert(0, file_path)
            # Parse and show count
            try:
                ext = os.path.splitext(file_path)[1].lower()
                if ext in ['.srt', '.vtt']:
                    subs = parse_subtitle_file(file_path)
                    self._capcut_log(f"📂 Đã chọn file: {os.path.basename(file_path)} ({len(subs)} dòng)")
                else:
                    content = read_document_file(file_path)
                    self._capcut_log(f"📂 Đã chọn file: {os.path.basename(file_path)} ({len(content)} ký tự)")
            except Exception as e:
                self._capcut_log(f"❌ Lỗi đọc file: {str(e)}")

    def _capcut_browse_folder(self):
        """Browse for folder containing txt/docx files"""
        dir_path = filedialog.askdirectory(title="Chọn thư mục chứa file txt/docx")
        if dir_path:
            self.capcut_srt_file_entry.delete(0, "end")
            self.capcut_srt_file_entry.insert(0, dir_path)
            # Count files
            txt_files = glob.glob(os.path.join(dir_path, "*.txt"))
            docx_files = glob.glob(os.path.join(dir_path, "*.docx"))
            doc_files = glob.glob(os.path.join(dir_path, "*.doc"))
            total = len(txt_files) + len(docx_files) + len(doc_files)
            self._capcut_log(f"📁 Đã chọn thư mục: {dir_path} ({total} file)")

    def _capcut_browse_output(self):
        """Browse for output directory"""
        dir_path = filedialog.askdirectory()
        if dir_path:
            self.capcut_srt_output_entry.delete(0, "end")
            self.capcut_srt_output_entry.insert(0, dir_path)

    def _capcut_preview_files(self):
        """Preview/list all generated audio files in output directory"""
        output_dir = self.capcut_srt_output_entry.get().strip()
        if not output_dir or not os.path.isdir(output_dir):
            messagebox.showinfo("Thông báo", "Thư mục output không tồn tại!")
            return
        
        # Find all mp3 files
        mp3_files = sorted(glob.glob(os.path.join(output_dir, "*.mp3")))
        
        if not mp3_files:
            messagebox.showinfo("Thông báo", "Không có file audio nào trong thư mục!")
            return
        
        # Create preview dialog
        preview_win = ctk.CTkToplevel(self)
        preview_win.title("🔊 Nghe thử Voice đã tạo")
        preview_win.geometry("600x500")
        preview_win.attributes('-topmost', True)
        
        ctk.CTkLabel(preview_win, text=f"📁 {output_dir}", font=("Roboto", 12), text_color="gray").pack(pady=5)
        ctk.CTkLabel(preview_win, text=f"Tìm thấy {len(mp3_files)} file audio", font=("Roboto", 14, "bold")).pack(pady=5)
        
        scroll_frame = ctk.CTkScrollableFrame(preview_win, fg_color="#1e293b")
        scroll_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        for mp3_file in mp3_files:
            file_name = os.path.basename(mp3_file)
            file_size = os.path.getsize(mp3_file) // 1024  # KB
            
            row = ctk.CTkFrame(scroll_frame, fg_color="#334155")
            row.pack(fill="x", pady=2, padx=5)
            
            ctk.CTkLabel(row, text=f"🎵 {file_name}", font=("Roboto", 11)).pack(side="left", padx=10, pady=8)
            ctk.CTkLabel(row, text=f"{file_size} KB", text_color="gray", font=("Roboto", 10)).pack(side="left", padx=5)
            
            ctk.CTkButton(
                row, text="▶", width=40, fg_color="#22c55e",
                command=lambda f=mp3_file: self.player.play(f)
            ).pack(side="right", padx=5, pady=5)
        
        # Stop button
        ctk.CTkButton(preview_win, text="⏹ Dừng phát", fg_color="#dc2626", 
                     command=self.player.stop).pack(pady=10)

    def _capcut_process_srt(self):
        """Process SRT/VTT file or folder with Capcut TTS"""
        input_path = self.capcut_srt_file_entry.get().strip()
        output_dir = self.capcut_srt_output_entry.get().strip()
        session_id = self.entry_capcut_session.get().strip() if hasattr(self, 'entry_capcut_session') else self.capcut_session_id
        merge_after = self.capcut_merge_var.get() if hasattr(self, 'capcut_merge_var') else False
        
        # Debug log
        self._capcut_log(f"[DEBUG] Processing input...")
        self._capcut_log(f"[DEBUG] Input: {input_path}")
        self._capcut_log(f"[DEBUG] Output: {output_dir}")
        self._capcut_log(f"[DEBUG] Merge after: {merge_after}")
        self._capcut_log(f"[DEBUG] Session ID loaded: {'Yes' if session_id else 'No'}")
        
        if not session_id:
            messagebox.showerror("Lỗi", "Vui lòng nhập Session ID trong tab Cài đặt!")
            self.tabview.set("⚙️ Configuration")
            return
        
        if not input_path or not os.path.exists(input_path):
            messagebox.showerror("Lỗi", "Vui lòng chọn file hoặc thư mục!")
            return
        
        if not output_dir:
            messagebox.showerror("Lỗi", "Vui lòng chọn thư mục output!")
            return
        
        os.makedirs(output_dir, exist_ok=True)
        
        voice_id = self.capcut_selected_voice.get()
        ffmpeg_path = getattr(self, 'ffmpeg_path', get_default_ffmpeg_path())
        
        self._capcut_log(f"[DEBUG] Voice ID: {voice_id}")
        
        self.capcut_srt_processing = True
        self.btn_capcut_process_srt.configure(state="disabled")
        self.btn_capcut_stop_srt.configure(state="normal")
        self.capcut_srt_progress.set(0)
        
        # Check if input is directory or file
        if os.path.isdir(input_path):
            threading.Thread(
                target=self._capcut_folder_worker,
                args=(input_path, output_dir, voice_id, session_id, ffmpeg_path, merge_after),
                daemon=True
            ).start()
        else:
            threading.Thread(
                target=self._capcut_srt_worker,
                args=(input_path, output_dir, voice_id, session_id, ffmpeg_path, merge_after),
                daemon=True
            ).start()

    def _capcut_srt_worker(self, file_path, output_dir, voice_id, session_id, ffmpeg_path="ffmpeg.exe", merge_after=False):
        """Worker thread for Capcut SRT/text file processing with chunking support"""
        try:
            ext = os.path.splitext(file_path)[1].lower()
            base_name = os.path.splitext(os.path.basename(file_path))[0]
            
            # Check if it's subtitle file or text document
            if ext in ['.srt', '.vtt']:
                # Parse subtitle file
                subtitles = parse_subtitle_file(file_path)
                is_subtitle = True
            else:
                # Read as text file and create chunks
                content = read_document_file(file_path)
                # For Capcut: max 450 chars per chunk
                chunks = split_text_smart(content, max_chars=CAPCUT_MAX_CHUNK_SIZE)
                subtitles = [Subtitle(c.index, "", "", c.text) for c in chunks]
                is_subtitle = False
            
            total = len(subtitles)
            
            if total == 0:
                self.after(0, lambda: self._capcut_log("❌ Không có nội dung nào trong file!"))
                return
            
            self.after(0, lambda: self._capcut_log(f"🚀 Bắt đầu xử lý {total} {'dòng' if is_subtitle else 'chunks'} (tuần tự)..."))
            masked_session = f"{session_id[:4]}****({len(session_id)} chars)" if len(session_id) > 4 else "****"
            self.after(0, lambda m=masked_session: self._capcut_log(f"[DEBUG] Session ID: {m}"))
            self.after(0, lambda: self._capcut_log(f"[DEBUG] Voice ID: {voice_id}"))
            self.after(0, lambda: self.capcut_srt_status.configure(text=f"Đang xử lý 0/{total}"))
            
            completed = 0
            success_count = 0
            failed_count = 0
            results = []
            
            # Process sequentially
            for sub in subtitles:
                if not self.capcut_srt_processing:
                    self.after(0, lambda: self._capcut_log("⏹ Đã dừng bởi người dùng"))
                    break
                
                # For long text in each subtitle line, apply chunking
                text = sub.text
                if len(text) > CAPCUT_LONG_TEXT_THRESHOLD:
                    # Need to chunk this line
                    line_chunks = split_text_smart(text, max_chars=CAPCUT_MAX_CHUNK_SIZE)
                    chunk_files = []
                    
                    for chunk in line_chunks:
                        if not self.capcut_srt_processing:
                            break
                        chunk_file = os.path.join(output_dir, f"{sub.index:04d}_chunk{chunk.index:02d}.mp3")
                        
                        # Retry logic for each chunk
                        for attempt in range(1, MAX_RETRIES + 1):
                            success, error = capcut_create_tts(chunk.text, voice_id, session_id, chunk_file, debug=False)
                            if success and os.path.exists(chunk_file) and os.path.getsize(chunk_file) > 0:
                                chunk_files.append(chunk_file)
                                break
                            elif attempt < MAX_RETRIES:
                                delay = calculate_retry_delay(attempt, is_connection_error(str(error)))
                                time.sleep(delay)
                        
                        time.sleep(CAPCUT_RATE_LIMIT_DELAY)
                    
                    # Merge chunks for this line
                    if chunk_files:
                        output_file = os.path.join(output_dir, f"{sub.index:04d}.mp3")
                        merge_success = merge_mp3_files_ffmpeg(chunk_files, output_file, ffmpeg_path)
                        if merge_success:
                            results.append((sub.index, output_file))
                            success_count += 1
                            # Clean up chunk files
                            for cf in chunk_files:
                                try:
                                    os.remove(cf)
                                except:
                                    pass
                        else:
                            failed_count += 1
                    else:
                        failed_count += 1
                else:
                    output_file = os.path.join(output_dir, f"{sub.index:04d}.mp3")
                    self.after(0, lambda i=sub.index, t=text[:30]: self._capcut_log(f"📝 [{i}] Đang xử lý: {t}..."))
                    
                    # Retry logic for Capcut voice creation
                    item_success = False
                    last_error = None
                    for attempt in range(1, MAX_RETRIES + 1):
                        if not self.capcut_srt_processing:
                            break
                        
                        success, error = capcut_create_tts(text, voice_id, session_id, output_file, debug=False)
                        
                        if success:
                            # Verify file was created
                            if os.path.exists(output_file) and os.path.getsize(output_file) > 0:
                                success_count += 1
                                results.append((sub.index, output_file))
                                item_success = True
                                if attempt > 1:
                                    self.after(0, lambda i=sub.index, a=attempt-1: self._capcut_log(f"✅ [{i}] Thành công sau {a} lần thử lại"))
                                else:
                                    self.after(0, lambda i=sub.index: self._capcut_log(f"✅ [{i}] Thành công"))
                                break
                            else:
                                last_error = {"error": "Audio file empty or not created"}
                        else:
                            last_error = error
                        
                        # Retry if not last attempt
                        if attempt < MAX_RETRIES:
                            err_msg = last_error.get('error', 'Unknown') if last_error else 'Unknown error'
                            delay = calculate_retry_delay(attempt, is_connection_error(err_msg))
                            self.after(0, lambda i=sub.index, a=attempt, e=err_msg[:ERROR_MSG_MAX_LENGTH]: self._capcut_log(f"⚠️ [{i}] Lần thử {a} thất bại: {e}... Đang thử lại"))
                            time.sleep(delay)
                    
                    if not item_success:
                        failed_count += 1
                        err_msg = last_error.get('error', 'Unknown') if last_error else 'Unknown error'
                        self.after(0, lambda i=sub.index, e=err_msg: self._capcut_log(f"❌ [{i}] Thất bại sau {MAX_RETRIES} lần thử: {e}"))
                    
                    time.sleep(CAPCUT_RATE_LIMIT_DELAY)
                
                completed += 1
                progress = completed / total
                self.after(0, lambda p=progress: self.capcut_srt_progress.set(p))
                self.after(0, lambda c=completed, t=total: self.capcut_srt_status.configure(text=f"Đang xử lý {c}/{t}"))
            
            # Sort results by index
            results.sort(key=lambda x: x[0])
            
            # Merge all files if requested
            if merge_after and results and not is_subtitle:
                merged_file = os.path.join(output_dir, f"{base_name}_merged.mp3")
                self.after(0, lambda: self._capcut_log(f"🔧 Đang hợp nhất {len(results)} file..."))
                
                result_files = [r[1] for r in results]
                merge_success = merge_mp3_files_ffmpeg(result_files, merged_file, ffmpeg_path)
                
                if merge_success:
                    self.after(0, lambda f=merged_file: self._capcut_log(f"✅ Đã hợp nhất: {f}"))
                else:
                    self.after(0, lambda: self._capcut_log(f"❌ Lỗi hợp nhất file!"))
            
            self.after(0, lambda: self._capcut_log(f"\n{'='*40}"))
            self.after(0, lambda s=success_count, t=total, f=failed_count: self._capcut_log(f"✅ Hoàn thành! Thành công: {s}/{t}, Thất bại: {f}"))
            
            if results:
                self.after(0, lambda: self._capcut_log(f"📁 Files đã lưu tại: {output_dir}"))
            
        except Exception as e:
            import traceback
            self.after(0, lambda: self._capcut_log(f"❌ Lỗi: {str(e)}"))
            self.after(0, lambda tb=traceback.format_exc(): self._capcut_log(f"[DEBUG] Traceback:\n{tb}"))
        finally:
            self.capcut_srt_processing = False
            self.after(0, lambda: self.btn_capcut_process_srt.configure(state="normal"))
            self.after(0, lambda: self.btn_capcut_stop_srt.configure(state="disabled"))
            self.after(0, lambda: self.capcut_srt_status.configure(text="Hoàn thành!"))

    def _capcut_folder_worker(self, folder_path, output_dir, voice_id, session_id, ffmpeg_path="ffmpeg.exe", merge_after=False):
        """Worker thread for processing folder of txt/docx files"""
        try:
            # Find all supported files
            txt_files = glob.glob(os.path.join(folder_path, "*.txt"))
            docx_files = glob.glob(os.path.join(folder_path, "*.docx"))
            doc_files = glob.glob(os.path.join(folder_path, "*.doc"))
            
            all_files = sorted(txt_files + docx_files + doc_files)
            total_files = len(all_files)
            
            if total_files == 0:
                self.after(0, lambda: self._capcut_log("❌ Không tìm thấy file txt/docx nào trong thư mục!"))
                return
            
            self.after(0, lambda: self._capcut_log(f"🚀 Bắt đầu xử lý {total_files} file từ thư mục..."))
            
            all_output_files = []
            
            for file_idx, file_path in enumerate(all_files):
                if not self.capcut_srt_processing:
                    self.after(0, lambda: self._capcut_log("⏹ Đã dừng bởi người dùng"))
                    break
                
                file_name = os.path.basename(file_path)
                base_name = os.path.splitext(file_name)[0]
                
                self.after(0, lambda f=file_name, i=file_idx+1, t=total_files: 
                          self._capcut_log(f"\n📄 [{i}/{t}] Đang xử lý: {f}"))
                
                try:
                    # Read file content
                    content = read_document_file(file_path)
                    
                    if not content.strip():
                        self.after(0, lambda: self._capcut_log(f"  ⚠️ File trống, bỏ qua"))
                        continue
                    
                    # Split into chunks (450 chars for Capcut)
                    chunks = split_text_smart(content, max_chars=CAPCUT_MAX_CHUNK_SIZE)
                    self.after(0, lambda c=len(chunks): self._capcut_log(f"  📝 Chia thành {c} chunks"))
                    
                    # Create temp directory for this file's chunks
                    file_temp_dir = os.path.join(output_dir, f"_temp_{base_name}")
                    os.makedirs(file_temp_dir, exist_ok=True)
                    
                    chunk_files = []
                    
                    for chunk in chunks:
                        if not self.capcut_srt_processing:
                            break
                        
                        chunk_file = os.path.join(file_temp_dir, f"chunk_{chunk.index:04d}.mp3")
                        
                        # Retry logic for each chunk
                        chunk_success = False
                        for attempt in range(1, MAX_RETRIES + 1):
                            success, error = capcut_create_tts(chunk.text, voice_id, session_id, chunk_file, debug=False)
                            
                            if success and os.path.exists(chunk_file) and os.path.getsize(chunk_file) > 0:
                                chunk_files.append(chunk_file)
                                chunk_success = True
                                break
                            elif attempt < MAX_RETRIES:
                                err_msg = error.get('error', 'Unknown') if error else 'Unknown'
                                delay = calculate_retry_delay(attempt, is_connection_error(err_msg))
                                time.sleep(delay)
                        
                        if not chunk_success:
                            err_msg = error.get('error', 'Unknown') if error else 'Unknown'
                            self.after(0, lambda e=err_msg, i=chunk.index: self._capcut_log(f"  ❌ Chunk [{i}] lỗi sau {MAX_RETRIES} lần thử: {e}"))
                        
                        time.sleep(CAPCUT_RATE_LIMIT_DELAY)
                    
                    # Merge chunks into single file
                    if chunk_files:
                        output_file = os.path.join(output_dir, f"{base_name}.mp3")
                        merge_success = merge_mp3_files_ffmpeg(chunk_files, output_file, ffmpeg_path)
                        
                        if merge_success:
                            self.after(0, lambda f=output_file: self._capcut_log(f"  ✅ Đã tạo: {os.path.basename(f)}"))
                            all_output_files.append(output_file)
                            
                            # Clean up chunks
                            for cf in chunk_files:
                                try:
                                    os.remove(cf)
                                except:
                                    pass
                            try:
                                os.rmdir(file_temp_dir)
                            except:
                                pass
                        else:
                            self.after(0, lambda: self._capcut_log(f"  ❌ Lỗi ghép file!"))
                    
                except Exception as e:
                    self.after(0, lambda err=str(e): self._capcut_log(f"  ❌ Lỗi: {err}"))
                
                # Update progress
                progress = (file_idx + 1) / total_files
                self.after(0, lambda p=progress: self.capcut_srt_progress.set(p))
                self.after(0, lambda i=file_idx+1, t=total_files: 
                          self.capcut_srt_status.configure(text=f"Đang xử lý file {i}/{t}"))
            
            # Merge all output files if requested
            if merge_after and all_output_files:
                merged_file = os.path.join(output_dir, "_all_merged.mp3")
                self.after(0, lambda: self._capcut_log(f"\n🔧 Đang hợp nhất tất cả {len(all_output_files)} file..."))
                
                merge_success = merge_mp3_files_ffmpeg(all_output_files, merged_file, ffmpeg_path)
                
                if merge_success:
                    self.after(0, lambda f=merged_file: self._capcut_log(f"✅ Đã hợp nhất tất cả: {f}"))
                else:
                    self.after(0, lambda: self._capcut_log(f"❌ Lỗi hợp nhất!"))
            
            self.after(0, lambda: self._capcut_log(f"\n{'='*40}"))
            self.after(0, lambda n=len(all_output_files), t=total_files: 
                      self._capcut_log(f"✅ Hoàn thành! Đã tạo {n}/{t} file"))
            self.after(0, lambda: self._capcut_log(f"📁 Files đã lưu tại: {output_dir}"))
            
        except Exception as e:
            import traceback
            self.after(0, lambda: self._capcut_log(f"❌ Lỗi: {str(e)}"))
            self.after(0, lambda tb=traceback.format_exc(): self._capcut_log(f"[DEBUG] Traceback:\n{tb}"))
        finally:
            self.capcut_srt_processing = False
            self.after(0, lambda: self.btn_capcut_process_srt.configure(state="normal"))
            self.after(0, lambda: self.btn_capcut_stop_srt.configure(state="disabled"))
            self.after(0, lambda: self.capcut_srt_status.configure(text="Hoàn thành!"))

    def _capcut_stop_srt(self):
        """Stop SRT processing"""
        self.capcut_srt_processing = False
        self._capcut_log("⏹ Đang dừng...")

    # ==========================================================================
    # EDGE TTS HELPER METHODS
    # ==========================================================================
    def _load_edge_voices(self):
        """Load voices from Edge TTS API"""
        self._edge_log("Đang tải danh sách voice từ Microsoft...")
        self.edge_voice_count_lbl.configure(text="Đang tải...")
        
        def load_thread():
            voices = fetch_edge_voices()
            if voices:
                self.edge_voices_cache = voices
                self.edge_last_fetch = time.time()
                self.after(0, lambda: self._edge_log(f"✅ Đã tải {len(voices)} voices"))
                self.after(0, lambda: self.edge_voice_count_lbl.configure(text=f"Voices: {len(voices)}"))
                self.after(0, lambda: self._populate_edge_voice_list())
                # Update settings cache label
                if hasattr(self, 'lbl_edge_cache'):
                    self.after(0, lambda: self.lbl_edge_cache.configure(text=f"Voice cache: {len(voices)} voices"))
            else:
                self.after(0, lambda: self._edge_log("❌ Không thể tải voice list"))
                self.after(0, lambda: self.edge_voice_count_lbl.configure(text="Lỗi!"))
        
        threading.Thread(target=load_thread, daemon=True).start()

    def _populate_edge_voice_list(self, voices=None):
        """Populate the Edge voice list"""
        for widget in self.edge_voice_list.winfo_children():
            widget.destroy()
        
        if voices is None:
            voices = self.edge_voices_cache
        
        for voice in voices:
            short_name = voice.get('ShortName', '')
            gender = voice.get('Gender', '')
            locale = voice.get('Locale', '')
            display = f"{short_name} ({gender})"
            
            rb = ctk.CTkRadioButton(
                self.edge_voice_list, 
                text=display, 
                variable=self.edge_selected_voice, 
                value=short_name,
                font=("Roboto", 10)
            )
            rb.pack(anchor="w", pady=2)

    def _filter_edge_voices(self, _=None):
        """Filter Edge voices based on language and gender"""
        # SỬA: Lấy giá trị từ biến StringVar thay vì ComboBox.get()
        lang_display = self.edge_lang_var.get()
        gender = self.edge_gender_filter.get()
        
        # Convert display name to language code
        lang_code = EDGE_TTS_LANGUAGE_MAP.get(lang_display, "")
        
        filtered = []
        for voice in self.edge_voices_cache:
            voice_lang = voice.get('Language', '')
            voice_gender = voice.get('Gender', '')
            
            if lang_code and voice_lang != lang_code:
                continue
            if gender != "Tất cả" and voice_gender != gender:
                continue
            filtered.append(voice)
        
        self._populate_edge_voice_list(filtered)

    def _edge_log(self, msg):
        """Add message to Edge log"""
        self.edge_log.configure(state="normal")
        self.edge_log.insert("end", f"[{time.strftime('%H:%M:%S')}] {msg}\n")
        self.edge_log.see("end")
        self.edge_log.configure(state="disabled")

    def _edge_generate(self):
        """Generate audio using Edge TTS - supports long text with chunking"""
        raw_text = self.edge_text_input.get("1.0", "end").strip()
        if not raw_text:
            messagebox.showerror("Lỗi", "Vui lòng nhập văn bản!")
            return
        
        # Clean text: remove extra whitespace and newlines
        text = clean_text_for_tts(raw_text)
        
        voice = self.edge_selected_voice.get()
        rate = self.edge_rate.get().strip() or "+0%"
        volume = self.edge_volume.get().strip() or "+0%"
        pitch = self.edge_pitch.get().strip() or "+0Hz"
        
        # Get ffmpeg path from settings
        ffmpeg_path = getattr(self, 'ffmpeg_path', get_default_ffmpeg_path())
        
        self._edge_log(f"Đang tạo audio với voice: {voice}")
        self._edge_log(f"[DEBUG] Text length: {len(text)} chars (cleaned from {len(raw_text)})")
        self.edge_status_lbl.configure(text="Đang xử lý...")
        self.btn_edge_generate.configure(state="disabled")
        
        def generate_thread():
            try:
                from edge.communicate import Communicate
                
                app_dir = os.path.dirname(os.path.abspath(__file__))
                
                # Check if text is long - need chunking
                if len(text) > EDGE_LONG_TEXT_THRESHOLD:
                    self.after(0, lambda: self._edge_log(f"📝 Văn bản dài ({len(text)} chars) - Đang chia thành chunks..."))
                    
                    # Split into chunks (Edge TTS handles more than Capcut)
                    chunks = split_text_smart(text, max_chars=EDGE_MAX_CHUNK_SIZE)
                    self.after(0, lambda c=len(chunks): self._edge_log(f"📝 Chia thành {c} chunks"))
                    
                    # Create temp directory
                    temp_dir = os.path.join(app_dir, "_temp_edge_chunks")
                    os.makedirs(temp_dir, exist_ok=True)
                    
                    chunk_files = []
                    
                    for chunk in chunks:
                        chunk_file = os.path.join(temp_dir, f"chunk_{chunk.index:04d}.mp3")
                        self.after(0, lambda i=chunk.index, t=chunk.text[:30]: self._edge_log(f"  [{i}] {t}..."))
                        
                        # Retry logic for each chunk
                        chunk_success = False
                        for attempt in range(1, MAX_RETRIES + 1):
                            loop = None
                            try:
                                communicate = Communicate(chunk.text, voice, rate=rate, volume=volume, pitch=pitch)
                                loop = asyncio.new_event_loop()
                                asyncio.set_event_loop(loop)
                                loop.run_until_complete(communicate.save(chunk_file))
                                
                                # Verify file was created
                                if os.path.exists(chunk_file) and os.path.getsize(chunk_file) > 0:
                                    chunk_files.append(chunk_file)
                                    chunk_success = True
                                    if attempt > 1:
                                        self.after(0, lambda i=chunk.index, a=attempt-1: self._edge_log(f"  ✅ [{i}] Thành công sau {a} lần thử lại"))
                                    break
                                else:
                                    raise ValueError("Audio file empty or not created")
                            except Exception as e:
                                if attempt < MAX_RETRIES:
                                    delay = calculate_retry_delay(attempt, is_connection_error(str(e)))
                                    self.after(0, lambda i=chunk.index, a=attempt: self._edge_log(f"  ⚠️ [{i}] Lần thử {a} thất bại, đang thử lại..."))
                                    time.sleep(delay)
                                else:
                                    self.after(0, lambda err=str(e), i=chunk.index: self._edge_log(f"  ❌ Chunk [{i}] lỗi sau {MAX_RETRIES} lần thử: {err}"))
                            finally:
                                # CRITICAL: Properly close event loop to prevent CPU leak
                                cleanup_event_loop(loop)
                    
                    if chunk_files:
                        # Merge all chunks
                        output_file = os.path.join(app_dir, "_temp_edge.mp3")
                        self.after(0, lambda: self._edge_log(f"🔧 Đang ghép {len(chunk_files)} chunks..."))
                        
                        merge_success = merge_mp3_files_ffmpeg(chunk_files, output_file, ffmpeg_path)
                        
                        if merge_success:
                            self.edge_temp_audio = output_file
                            self.after(0, lambda: self._edge_log(f"✅ Tạo audio thành công!"))
                            self.after(0, lambda: self.edge_status_lbl.configure(text="Hoàn thành!"))
                            self.after(0, lambda: self.btn_edge_play.configure(state="normal"))
                            self.after(0, lambda: self.btn_edge_save.configure(state="normal"))
                            
                            # Cleanup temp chunks
                            for f in chunk_files:
                                try:
                                    os.remove(f)
                                except:
                                    pass
                            try:
                                os.rmdir(temp_dir)
                            except:
                                pass
                        else:
                            self.after(0, lambda: self._edge_log(f"❌ Lỗi ghép file! Kiểm tra đường dẫn ffmpeg."))
                            self.after(0, lambda: self.edge_status_lbl.configure(text="Lỗi ghép file!"))
                    else:
                        self.after(0, lambda: self._edge_log(f"❌ Không có chunk nào thành công!"))
                        self.after(0, lambda: self.edge_status_lbl.configure(text="Lỗi!"))
                else:
                    # Short text - process directly with retry logic
                    output_file = os.path.join(app_dir, "_temp_edge.mp3")
                    success = False
                    
                    for attempt in range(1, MAX_RETRIES + 1):
                        loop = None
                        try:
                            communicate = Communicate(text, voice, rate=rate, volume=volume, pitch=pitch)
                            
                            loop = asyncio.new_event_loop()
                            asyncio.set_event_loop(loop)
                            loop.run_until_complete(communicate.save(output_file))
                            
                            # Verify file was created
                            if os.path.exists(output_file) and os.path.getsize(output_file) > 0:
                                self.edge_temp_audio = output_file
                                self.after(0, lambda: self._edge_log(f"✅ Tạo audio thành công!"))
                                self.after(0, lambda: self.edge_status_lbl.configure(text="Hoàn thành!"))
                                self.after(0, lambda: self.btn_edge_play.configure(state="normal"))
                                self.after(0, lambda: self.btn_edge_save.configure(state="normal"))
                                success = True
                                break
                            else:
                                raise ValueError("Audio file empty or not created")
                        except Exception as e:
                            if attempt < MAX_RETRIES:
                                delay = calculate_retry_delay(attempt, is_connection_error(str(e)))
                                self.after(0, lambda a=attempt, err=str(e)[:50]: self._edge_log(f"⚠️ Lần thử {a} thất bại: {err}... Đang thử lại"))
                                time.sleep(delay)
                            else:
                                self.after(0, lambda err=str(e): self._edge_log(f"❌ Thất bại sau {MAX_RETRIES} lần thử: {err}"))
                                self.after(0, lambda: self.edge_status_lbl.configure(text="Lỗi!"))
                        finally:
                            # CRITICAL: Properly close event loop to prevent CPU leak
                            cleanup_event_loop(loop)
                
            except Exception as e:
                self.after(0, lambda: self._edge_log(f"❌ Lỗi: {str(e)}"))
                self.after(0, lambda: self.edge_status_lbl.configure(text="Lỗi!"))
            finally:
                self.after(0, lambda: self.btn_edge_generate.configure(state="normal"))
        
        threading.Thread(target=generate_thread, daemon=True).start()

    def _edge_play(self):
        """Play the generated Edge audio"""
        if self.edge_temp_audio and os.path.exists(self.edge_temp_audio):
            self.player.play(self.edge_temp_audio)
            self._edge_log("▶ Đang phát audio...")

    def _edge_save(self):
        """Save the Edge audio to a file"""
        if not self.edge_temp_audio or not os.path.exists(self.edge_temp_audio):
            return
        
        file_path = filedialog.asksaveasfilename(
            defaultextension=".mp3",
            filetypes=[("MP3 files", "*.mp3"), ("All files", "*.*")]
        )
        if file_path:
            shutil.copy(self.edge_temp_audio, file_path)
            self._edge_log(f"💾 Đã lưu: {file_path}")

    # ==========================================================================
    # EDGE TTS SRT/VTT PROCESSING METHODS
    # ==========================================================================
    def _edge_browse_srt(self):
        """Browse for SRT/VTT file"""
        file_path = filedialog.askopenfilename(
            filetypes=[("Subtitle files", "*.srt *.vtt"), ("Text files", "*.txt"), ("Word files", "*.docx"), ("SRT files", "*.srt"), ("VTT files", "*.vtt"), ("All files", "*.*")]
        )
        if file_path:
            self.edge_srt_file_entry.delete(0, "end")
            self.edge_srt_file_entry.insert(0, file_path)
            try:
                ext = os.path.splitext(file_path)[1].lower()
                if ext in ['.srt', '.vtt']:
                    subs = parse_subtitle_file(file_path)
                    self._edge_log(f"📂 Đã chọn file: {os.path.basename(file_path)} ({len(subs)} dòng)")
                else:
                    content = read_document_file(file_path)
                    self._edge_log(f"📂 Đã chọn file: {os.path.basename(file_path)} ({len(content)} ký tự)")
            except Exception as e:
                self._edge_log(f"❌ Lỗi đọc file: {str(e)}")

    def _edge_browse_folder(self):
        """Browse for folder containing txt/docx files"""
        dir_path = filedialog.askdirectory(title="Chọn thư mục chứa file txt/docx")
        if dir_path:
            self.edge_srt_file_entry.delete(0, "end")
            self.edge_srt_file_entry.insert(0, dir_path)
            # Count files
            txt_files = glob.glob(os.path.join(dir_path, "*.txt"))
            docx_files = glob.glob(os.path.join(dir_path, "*.docx"))
            doc_files = glob.glob(os.path.join(dir_path, "*.doc"))
            total = len(txt_files) + len(docx_files) + len(doc_files)
            self._edge_log(f"📁 Đã chọn thư mục: {dir_path} ({total} file)")

    def _edge_browse_output(self):
        """Browse for output directory"""
        dir_path = filedialog.askdirectory()
        if dir_path:
            self.edge_srt_output_entry.delete(0, "end")
            self.edge_srt_output_entry.insert(0, dir_path)

    def _edge_preview_files(self):
        """Preview/list all generated audio files in output directory"""
        output_dir = self.edge_srt_output_entry.get().strip()
        if not output_dir or not os.path.isdir(output_dir):
            messagebox.showinfo("Thông báo", "Thư mục output không tồn tại!")
            return
        
        # Find all mp3 files
        mp3_files = sorted(glob.glob(os.path.join(output_dir, "*.mp3")))
        
        if not mp3_files:
            messagebox.showinfo("Thông báo", "Không có file audio nào trong thư mục!")
            return
        
        # Create preview dialog
        preview_win = ctk.CTkToplevel(self)
        preview_win.title("🔊 Nghe thử Voice đã tạo")
        preview_win.geometry("600x500")
        preview_win.attributes('-topmost', True)
        
        ctk.CTkLabel(preview_win, text=f"📁 {output_dir}", font=("Roboto", 12), text_color="gray").pack(pady=5)
        ctk.CTkLabel(preview_win, text=f"Tìm thấy {len(mp3_files)} file audio", font=("Roboto", 14, "bold")).pack(pady=5)
        
        scroll_frame = ctk.CTkScrollableFrame(preview_win, fg_color="#1e293b")
        scroll_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        for mp3_file in mp3_files:
            file_name = os.path.basename(mp3_file)
            file_size = os.path.getsize(mp3_file) // 1024  # KB
            
            row = ctk.CTkFrame(scroll_frame, fg_color="#334155")
            row.pack(fill="x", pady=2, padx=5)
            
            ctk.CTkLabel(row, text=f"🎵 {file_name}", font=("Roboto", 11)).pack(side="left", padx=10, pady=8)
            ctk.CTkLabel(row, text=f"{file_size} KB", text_color="gray", font=("Roboto", 10)).pack(side="left", padx=5)
            
            ctk.CTkButton(
                row, text="▶", width=40, fg_color="#22c55e",
                command=lambda f=mp3_file: self.player.play(f)
            ).pack(side="right", padx=5, pady=5)
        
        # Stop button
        ctk.CTkButton(preview_win, text="⏹ Dừng phát", fg_color="#dc2626", 
                     command=self.player.stop).pack(pady=10)

    def _edge_process_srt(self):
        """Process SRT/VTT file or folder with Edge TTS"""
        input_path = self.edge_srt_file_entry.get().strip()
        output_dir = self.edge_srt_output_entry.get().strip()
        merge_after = self.edge_merge_var.get() if hasattr(self, 'edge_merge_var') else False
        
        if not input_path or not os.path.exists(input_path):
            messagebox.showerror("Lỗi", "Vui lòng chọn file hoặc thư mục!")
            return
        
        if not output_dir:
            messagebox.showerror("Lỗi", "Vui lòng chọn thư mục output!")
            return
        
        os.makedirs(output_dir, exist_ok=True)
        
        voice = self.edge_selected_voice.get()
        rate = self.edge_rate.get().strip() or "+0%"
        volume = self.edge_volume.get().strip() or "+0%"
        pitch = self.edge_pitch.get().strip() or "+0Hz"
        ffmpeg_path = getattr(self, 'ffmpeg_path', get_default_ffmpeg_path())
        
        try:
            workers = int(self.edge_workers_var.get().strip() or "10")
        except ValueError:
            workers = 10
        
        self.edge_srt_processing = True
        self.btn_edge_process_srt.configure(state="disabled")
        self.btn_edge_stop_srt.configure(state="normal")
        self.edge_srt_progress.set(0)
        
        # Check if input is directory or file
        if os.path.isdir(input_path):
            threading.Thread(
                target=self._edge_folder_worker,
                args=(input_path, output_dir, voice, rate, volume, pitch, workers, ffmpeg_path, merge_after),
                daemon=True
            ).start()
        else:
            threading.Thread(
                target=self._edge_srt_worker,
                args=(input_path, output_dir, voice, rate, volume, pitch, workers, ffmpeg_path, merge_after),
                daemon=True
            ).start()

    def _edge_srt_worker(self, file_path, output_dir, voice, rate, volume, pitch, workers, ffmpeg_path="ffmpeg.exe", merge_after=False):
        """Worker thread for Edge TTS SRT/text file processing with parallel workers and chunking support"""
        try:
            from edge.communicate import Communicate
            
            ext = os.path.splitext(file_path)[1].lower()
            base_name = os.path.splitext(os.path.basename(file_path))[0]
            
            # Check if it's subtitle file or text document
            if ext in ['.srt', '.vtt']:
                subtitles = parse_subtitle_file(file_path)
                is_subtitle = True
            else:
                # Read as text file and create chunks (1000 chars for Edge TTS)
                content = read_document_file(file_path)
                chunks = split_text_smart(content, max_chars=EDGE_MAX_CHUNK_SIZE)
                subtitles = [Subtitle(c.index, "", "", c.text) for c in chunks]
                is_subtitle = False
            
            total = len(subtitles)
            
            if total == 0:
                self.after(0, lambda: self._edge_log("❌ Không có nội dung nào trong file!"))
                return
            
            self.after(0, lambda: self._edge_log(f"🚀 Bắt đầu xử lý {total} {'dòng' if is_subtitle else 'chunks'} với {workers} workers..."))
            self.after(0, lambda: self.edge_srt_status.configure(text=f"Đang xử lý 0/{total}"))
            
            completed = 0
            success_count = 0
            failed_count = 0
            lock = threading.Lock()
            results = []
            
            def process_single(sub):
                nonlocal completed, success_count, failed_count
                
                if not self.edge_srt_processing:
                    return None
                
                text = sub.text
                output_file = os.path.join(output_dir, f"{sub.index:04d}.mp3")
                
                # Retry logic for voice creation
                max_retries = MAX_RETRIES
                last_error = None
                
                for attempt in range(1, max_retries + 1):
                    if not self.edge_srt_processing:
                        return None
                    
                    loop = None
                    try:
                        # For long text in subtitle line, Edge TTS handles it internally
                        communicate = Communicate(text, voice, rate=rate, volume=volume, pitch=pitch)
                        
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        loop.run_until_complete(communicate.save(output_file))
                        
                        # Verify file was created and has content
                        if not os.path.exists(output_file) or os.path.getsize(output_file) < MIN_AUDIO_FILE_SIZE:
                            raise ValueError("Audio file empty or not created")
                        
                        with lock:
                            completed += 1
                            success_count += 1
                            results.append((sub.index, output_file))
                            progress = completed / total
                            self.after(0, lambda p=progress: self.edge_srt_progress.set(p))
                            self.after(0, lambda c=completed, t=total: self.edge_srt_status.configure(text=f"Đang xử lý {c}/{t}"))
                        
                        if attempt > 1:
                            self.after(0, lambda i=sub.index, a=attempt-1: self._edge_log(f"✅ [{i}] Thành công sau {a} lần thử lại"))
                        
                        return output_file
                        
                    except Exception as e:
                        last_error = str(e)
                        if attempt < max_retries:
                            delay = calculate_retry_delay(attempt, is_connection_error(last_error))
                            self.after(0, lambda i=sub.index, a=attempt, m=max_retries, err=last_error[:ERROR_MSG_MAX_LENGTH]: 
                                      self._edge_log(f"⚠️ [{i}] Lần thử {a}/{m} thất bại: {err}... Đang thử lại"))
                            time.sleep(delay)
                    finally:
                        # CRITICAL: Properly close and cleanup the event loop to prevent CPU leak
                        cleanup_event_loop(loop)
                
                # All retries failed
                with lock:
                    completed += 1
                    failed_count += 1
                    self.after(0, lambda err=last_error, i=sub.index: self._edge_log(f"❌ [{i}] Thất bại sau {max_retries} lần thử: {err}"))
                    progress = completed / total
                    self.after(0, lambda p=progress: self.edge_srt_progress.set(p))
                    self.after(0, lambda c=completed, t=total: self.edge_srt_status.configure(text=f"Đang xử lý {c}/{t}"))
                return None
            
            # Process with thread pool
            with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
                futures = {executor.submit(process_single, sub): sub for sub in subtitles}
                for future in concurrent.futures.as_completed(futures):
                    if not self.edge_srt_processing:
                        break
                    future.result()  # Wait for completion
            
            # Sort results by index
            results.sort(key=lambda x: x[0])
            
            # Merge all files if requested
            if merge_after and results and not is_subtitle:
                merged_file = os.path.join(output_dir, f"{base_name}_merged.mp3")
                self.after(0, lambda: self._edge_log(f"🔧 Đang hợp nhất {len(results)} file..."))
                
                result_files = [r[1] for r in results]
                merge_success = merge_mp3_files_ffmpeg(result_files, merged_file, ffmpeg_path)
                
                if merge_success:
                    self.after(0, lambda f=merged_file: self._edge_log(f"✅ Đã hợp nhất: {f}"))
                else:
                    self.after(0, lambda: self._edge_log(f"❌ Lỗi hợp nhất file!"))
            
            self.after(0, lambda: self._edge_log(f"\n{'='*40}"))
            self.after(0, lambda s=success_count, t=total, f=failed_count: self._edge_log(f"✅ Hoàn thành! Thành công: {s}/{t}, Thất bại: {f}"))
            
            if results:
                self.after(0, lambda: self._edge_log(f"📁 Files đã lưu tại: {output_dir}"))
            
        except Exception as e:
            self.after(0, lambda: self._edge_log(f"❌ Lỗi: {str(e)}"))
        finally:
            self.edge_srt_processing = False
            self.after(0, lambda: self.btn_edge_process_srt.configure(state="normal"))
            self.after(0, lambda: self.btn_edge_stop_srt.configure(state="disabled"))
            self.after(0, lambda: self.edge_srt_status.configure(text="Hoàn thành!"))

    def _edge_folder_worker(self, folder_path, output_dir, voice, rate, volume, pitch, workers, ffmpeg_path="ffmpeg.exe", merge_after=False):
        """Worker thread for processing folder of txt/docx files with Edge TTS"""
        try:
            from edge.communicate import Communicate
            
            # Find all supported files
            txt_files = glob.glob(os.path.join(folder_path, "*.txt"))
            docx_files = glob.glob(os.path.join(folder_path, "*.docx"))
            doc_files = glob.glob(os.path.join(folder_path, "*.doc"))
            
            all_files = sorted(txt_files + docx_files + doc_files)
            total_files = len(all_files)
            
            if total_files == 0:
                self.after(0, lambda: self._edge_log("❌ Không tìm thấy file txt/docx nào trong thư mục!"))
                return
            
            self.after(0, lambda: self._edge_log(f"🚀 Bắt đầu xử lý {total_files} file với {workers} workers..."))
            
            all_output_files = []
            
            for file_idx, file_path in enumerate(all_files):
                if not self.edge_srt_processing:
                    self.after(0, lambda: self._edge_log("⏹ Đã dừng bởi người dùng"))
                    break
                
                file_name = os.path.basename(file_path)
                base_name = os.path.splitext(file_name)[0]
                
                self.after(0, lambda f=file_name, i=file_idx+1, t=total_files: 
                          self._edge_log(f"\n📄 [{i}/{t}] Đang xử lý: {f}"))
                
                try:
                    # Read file content
                    content = read_document_file(file_path)
                    
                    if not content.strip():
                        self.after(0, lambda: self._edge_log(f"  ⚠️ File trống, bỏ qua"))
                        continue
                    
                    # Split into chunks (1000 chars for Edge TTS)
                    chunks = split_text_smart(content, max_chars=EDGE_MAX_CHUNK_SIZE)
                    self.after(0, lambda c=len(chunks): self._edge_log(f"  📝 Chia thành {c} chunks"))
                    
                    # Create temp directory for this file's chunks
                    file_temp_dir = os.path.join(output_dir, f"_temp_{base_name}")
                    os.makedirs(file_temp_dir, exist_ok=True)
                    
                    chunk_files = []
                    lock = threading.Lock()
                    
                    def process_chunk(chunk):
                        if not self.edge_srt_processing:
                            return None
                        
                        chunk_file = os.path.join(file_temp_dir, f"chunk_{chunk.index:04d}.mp3")
                        
                        # Retry logic for each chunk
                        for attempt in range(1, MAX_RETRIES + 1):
                            if not self.edge_srt_processing:
                                return None
                            
                            loop = None
                            try:
                                communicate = Communicate(chunk.text, voice, rate=rate, volume=volume, pitch=pitch)
                                loop = asyncio.new_event_loop()
                                asyncio.set_event_loop(loop)
                                loop.run_until_complete(communicate.save(chunk_file))
                                
                                # Verify file was created
                                if os.path.exists(chunk_file) and os.path.getsize(chunk_file) > 0:
                                    with lock:
                                        chunk_files.append((chunk.index, chunk_file))
                                    return chunk_file
                                else:
                                    raise ValueError("Audio file empty or not created")
                            except Exception as e:
                                if attempt < MAX_RETRIES:
                                    delay = calculate_retry_delay(attempt, is_connection_error(str(e)))
                                    time.sleep(delay)
                                else:
                                    self.after(0, lambda err=str(e), i=chunk.index: self._edge_log(f"  ❌ Chunk [{i}] lỗi sau {MAX_RETRIES} lần thử: {err}"))
                            finally:
                                # CRITICAL: Properly close event loop to prevent CPU leak
                                cleanup_event_loop(loop)
                        return None
                    
                    # Process chunks with thread pool
                    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
                        futures = [executor.submit(process_chunk, chunk) for chunk in chunks]
                        for future in concurrent.futures.as_completed(futures):
                            if not self.edge_srt_processing:
                                break
                            future.result()
                    
                    # Sort chunk files by index
                    chunk_files.sort(key=lambda x: x[0])
                    chunk_file_paths = [cf[1] for cf in chunk_files]
                    
                    # Merge chunks into single file
                    if chunk_file_paths:
                        output_file = os.path.join(output_dir, f"{base_name}.mp3")
                        merge_success = merge_mp3_files_ffmpeg(chunk_file_paths, output_file, ffmpeg_path)
                        
                        if merge_success:
                            self.after(0, lambda f=output_file: self._edge_log(f"  ✅ Đã tạo: {os.path.basename(f)}"))
                            all_output_files.append(output_file)
                            
                            # Clean up chunks
                            for cf in chunk_file_paths:
                                try:
                                    os.remove(cf)
                                except:
                                    pass
                            try:
                                os.rmdir(file_temp_dir)
                            except:
                                pass
                        else:
                            self.after(0, lambda: self._edge_log(f"  ❌ Lỗi ghép file!"))
                    
                except Exception as e:
                    self.after(0, lambda err=str(e): self._edge_log(f"  ❌ Lỗi: {err}"))
                
                # Update progress
                progress = (file_idx + 1) / total_files
                self.after(0, lambda p=progress: self.edge_srt_progress.set(p))
                self.after(0, lambda i=file_idx+1, t=total_files: 
                          self.edge_srt_status.configure(text=f"Đang xử lý file {i}/{t}"))
            
            # Merge all output files if requested
            if merge_after and all_output_files:
                merged_file = os.path.join(output_dir, "_all_merged.mp3")
                self.after(0, lambda: self._edge_log(f"\n🔧 Đang hợp nhất tất cả {len(all_output_files)} file..."))
                
                merge_success = merge_mp3_files_ffmpeg(all_output_files, merged_file, ffmpeg_path)
                
                if merge_success:
                    self.after(0, lambda f=merged_file: self._edge_log(f"✅ Đã hợp nhất tất cả: {f}"))
                else:
                    self.after(0, lambda: self._edge_log(f"❌ Lỗi hợp nhất!"))
            
            self.after(0, lambda: self._edge_log(f"\n{'='*40}"))
            self.after(0, lambda n=len(all_output_files), t=total_files: 
                      self._edge_log(f"✅ Hoàn thành! Đã tạo {n}/{t} file"))
            self.after(0, lambda: self._edge_log(f"📁 Files đã lưu tại: {output_dir}"))
            
        except Exception as e:
            self.after(0, lambda: self._edge_log(f"❌ Lỗi: {str(e)}"))
        finally:
            self.edge_srt_processing = False
            self.after(0, lambda: self.btn_edge_process_srt.configure(state="normal"))
            self.after(0, lambda: self.btn_edge_stop_srt.configure(state="disabled"))
            self.after(0, lambda: self.edge_srt_status.configure(text="Hoàn thành!"))

    def _edge_stop_srt(self):
        """Stop SRT processing"""
        self.edge_srt_processing = False
        self._edge_log("⏹ Đang dừng...")

    def _add_custom_capcut_voice(self):
        """Add a custom voice ID to the list"""
        voice_id = self.entry_new_voice_id.get().strip()
        voice_name = self.entry_new_voice_name.get().strip()
        
        if not voice_id:
            messagebox.showerror("Lỗi", "Vui lòng nhập Voice ID!")
            return
        
        if not voice_name:
            voice_name = voice_id
        
        # Check if already exists
        for v in self.capcut_custom_voices:
            if v.get('voice_id') == voice_id:
                messagebox.showinfo("Thông báo", "Voice ID này đã tồn tại!")
                return
        
        new_voice = {
            "voice_id": voice_id,
            "display_name": voice_name,
            "category": "Tùy chỉnh",
            "gender": "Khác",
            "language": "?"
        }
        
        self.capcut_custom_voices.append(new_voice)
        self._refresh_custom_voice_list()
        self._filter_capcut_voices()
        
        # Clear inputs
        self.entry_new_voice_id.delete(0, "end")
        self.entry_new_voice_name.delete(0, "end")
        
        messagebox.showinfo("Thành công", f"Đã thêm voice: {voice_name}")

    def _refresh_custom_voice_list(self):
        """Refresh the custom voice list display"""
        if not hasattr(self, 'capcut_custom_list'):
            return
            
        for widget in self.capcut_custom_list.winfo_children():
            widget.destroy()
        
        if not self.capcut_custom_voices:
            ctk.CTkLabel(self.capcut_custom_list, text="Chưa có voice tùy chỉnh", text_color="gray").pack(pady=10)
            return
        
        for voice in self.capcut_custom_voices:
            row = ctk.CTkFrame(self.capcut_custom_list, fg_color="#1f2937")
            row.pack(fill="x", pady=2)
            
            ctk.CTkLabel(row, text=f"{voice.get('display_name')} ({voice.get('voice_id')})", font=("Roboto", 10)).pack(side="left", padx=5, pady=5)
            
            btn_del = ctk.CTkButton(row, text="✕", width=25, height=25, fg_color="#ef4444", 
                                   command=lambda v=voice: self._remove_custom_voice(v))
            btn_del.pack(side="right", padx=5, pady=2)

    def _remove_custom_voice(self, voice):
        """Remove a custom voice"""
        self.capcut_custom_voices = [v for v in self.capcut_custom_voices if v.get('voice_id') != voice.get('voice_id')]
        self._refresh_custom_voice_list()
        self._filter_capcut_voices()

    def _browse_ffmpeg(self):
        """Browse for ffmpeg executable"""
        file_path = filedialog.askopenfilename(
            title="Chọn file ffmpeg.exe",
            filetypes=[("Executable", "*.exe"), ("All files", "*.*")]
        )
        if file_path:
            self.entry_ffmpeg_path.delete(0, "end")
            self.entry_ffmpeg_path.insert(0, file_path)

    def _refresh_edge_voices(self):
        """Refresh Edge TTS voices"""
        self._load_edge_voices()

    def _load_settings(self):
        if os.path.exists(self.settings_file):
            try:
                with open(self.settings_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.api_key_content = data.get("api_keys", "")
                    self.sys_instr_content = data.get("system_instruction", DEFAULT_SYSTEM_INSTRUCTION)
                    self.multi_worker_enabled_val = data.get("multi_worker_enabled", False)
                    self.workers_per_key_val = data.get("workers_per_key", 2)
                    # Thinking mode settings
                    self.thinking_mode_val = data.get("thinking_mode", False)
                    self.thinking_budget_val = data.get("thinking_budget", 1024)
                    self.affective_val = data.get("affective_dialog", False)
                    self.proactive_val = data.get("proactive_audio", False)
                    # Capcut settings
                    self.capcut_session_id = data.get("capcut_session_id", "")
                    self.capcut_custom_voices = data.get("capcut_custom_voices", [])
                    # FFmpeg path - use get_default_ffmpeg_path() for correct default
                    self.ffmpeg_path = data.get("ffmpeg_path", get_default_ffmpeg_path())
                    # Ngắt dòng v2 settings
                    self.gemini_chunk_v2_enabled = data.get("gemini_chunk_v2_enabled", False)
                    self.lt_chunk_v2_enabled = data.get("lt_chunk_v2_enabled", False)
                    # Gemini TTS file chunking settings
                    self.gemini_chunk_size = data.get("gemini_chunk_size", GEMINI_DEFAULT_CHUNK_SIZE)
            except Exception as e:
                print(f"Error loading settings: {e}")

    def _save_settings_from_ui(self):
        # Get data from UI widgets
        self.api_key_content = self.txt_api_keys.get("1.0", "end").strip()
        self.sys_instr_content = self.txt_sys_instr.get("1.0", "end").strip()
        self.multi_worker_enabled_val = bool(self.sw_multi_worker.get())
        self.workers_per_key_val = int(self.slider_workers.get())
        # Get thinking mode settings
        self.thinking_mode_val = bool(self.sw_thinking.get())
        self.thinking_budget_val = int(self.slider_budget.get())
        self.affective_val = bool(self.sw_affective.get())
        self.proactive_val = bool(self.sw_proactive.get())
        # Get Capcut session ID
        if hasattr(self, 'entry_capcut_session'):
            self.capcut_session_id = self.entry_capcut_session.get().strip()
        # Get FFmpeg path
        if hasattr(self, 'entry_ffmpeg_path'):
            self.ffmpeg_path = self.entry_ffmpeg_path.get().strip()
        # Get Ngắt dòng v2 settings from UI
        if hasattr(self, 'gemini_sw_chunk_v2'):
            self.gemini_chunk_v2_enabled = bool(self.gemini_sw_chunk_v2.get())
        if hasattr(self, 'lt_sw_chunk_v2'):
            self.lt_chunk_v2_enabled = bool(self.lt_sw_chunk_v2.get())
        # Get Gemini chunk size from UI
        if hasattr(self, 'gemini_chunk_size_entry'):
            try:
                self.gemini_chunk_size = int(self.gemini_chunk_size_entry.get().strip() or GEMINI_DEFAULT_CHUNK_SIZE)
            except ValueError:
                self.gemini_chunk_size = GEMINI_DEFAULT_CHUNK_SIZE
        
        data = {
            "api_keys": self.api_key_content,
            "system_instruction": self.sys_instr_content,
            "multi_worker_enabled": self.multi_worker_enabled_val,
            "workers_per_key": self.workers_per_key_val,
            "thinking_mode": self.thinking_mode_val,
            "thinking_budget": self.thinking_budget_val,
            "affective_dialog": self.affective_val,
            "proactive_audio": self.proactive_val,
            "capcut_session_id": self.capcut_session_id,
            "capcut_custom_voices": self.capcut_custom_voices,
            "ffmpeg_path": self.ffmpeg_path,
            "gemini_chunk_v2_enabled": self.gemini_chunk_v2_enabled,
            "lt_chunk_v2_enabled": self.lt_chunk_v2_enabled,
            "gemini_chunk_size": self.gemini_chunk_size
        }
        try:
            with open(self.settings_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
            # Update Capcut session display
            self._update_capcut_session_display()
            # Update Long Text Engine ffmpeg path if exists
            if hasattr(self, 'lt_entry_ffmpeg'):
                self.lt_entry_ffmpeg.delete(0, "end")
                self.lt_entry_ffmpeg.insert(0, self.ffmpeg_path)
            messagebox.showinfo("Saved", "Settings saved successfully!\nCấu hình đã được lưu.")
        except Exception as e:
            messagebox.showerror("Error", f"Could not save settings: {e}")

    def _get_api_keys(self) -> List[str]:
        # Always get latest from the Textbox in Settings Tab
        content = self.txt_api_keys.get("1.0", "end").strip()
        return [k.strip() for k in content.split('\n') if k.strip()]

    def _browse_input(self):
        file_path = filedialog.askopenfilename(filetypes=[("Subtitle files", "*.srt *.txt"), ("All files", "*.*")])
        if file_path:
            self.entry_file.delete(0, "end")
            self.entry_file.insert(0, file_path)
            self._load_file()

    def _browse_output(self):
        dir_path = filedialog.askdirectory()
        if dir_path:
            self.entry_out.delete(0, "end")
            self.entry_out.insert(0, dir_path)

    def _load_file(self):
        file_path = self.entry_file.get()
        if not file_path or not Path(file_path).exists():
            messagebox.showerror("Error", "File not found")
            return
        
        try:
            content = Path(file_path).read_text(encoding='utf-8')
            
            if file_path.endswith('.srt'):
                self.subtitles = parse_srt(content)
            else:
                # Parse txt file first
                raw_subtitles = parse_txt(content)
                
                # Get chunk settings from UI
                chunk_size = int(self.gemini_chunk_size_entry.get().strip() or GEMINI_DEFAULT_CHUNK_SIZE) if hasattr(self, 'gemini_chunk_size_entry') else GEMINI_DEFAULT_CHUNK_SIZE
                chunk_v2_enabled = bool(self.gemini_sw_chunk_v2.get()) if hasattr(self, 'gemini_sw_chunk_v2') else False
                
                # Process each subtitle - chunk if needed
                processed_subtitles = []
                sub_index = 1
                
                for raw_sub in raw_subtitles:
                    # Clean the text first
                    cleaned_text = clean_text_for_tts(raw_sub.text)
                    
                    if len(cleaned_text) <= chunk_size:
                        # Short enough, just add it
                        processed_subtitles.append(Subtitle(index=sub_index, text=cleaned_text))
                        sub_index += 1
                    else:
                        # Long text - need to chunk
                        if chunk_v2_enabled:
                            chunks = split_text_by_punctuation_v2(cleaned_text, target_chunk_size=chunk_size, remove_punct=True)
                        else:
                            chunks = split_text_into_chunks(cleaned_text, chunk_size)
                        
                        for chunk in chunks:
                            processed_subtitles.append(Subtitle(index=sub_index, text=chunk.text))
                            sub_index += 1
                
                self.subtitles = processed_subtitles
                
                if len(self.subtitles) > len(raw_subtitles):
                    self.log(f"📝 Văn bản dài được chia thành {len(self.subtitles)} phần (chunk size: {chunk_size}, v2: {chunk_v2_enabled})", "INFO")
            
            self.log(f"✅ Loaded {len(self.subtitles)} lines from {Path(file_path).name}", "SUCCESS")
        except Exception as e:
            self.log(f"❌ Error loading file: {e}", "ERROR")

    def _clear_audio_list(self):
        self.generated_audios = []
        # Clear UI rows
        for widget in self.audio_scroll.winfo_children():
            widget.destroy()

    def _add_audio_row(self, audio: GeneratedAudio):
        # Create a card for the audio
        row = ctk.CTkFrame(self.audio_scroll, fg_color="#444")
        row.pack(fill="x", pady=2, padx=2)
        
        # Info
        ctk.CTkLabel(row, text=f"#{audio.index:04d}", width=50, font=("Consolas", 12, "bold")).pack(side="left", padx=5)
        ctk.CTkLabel(row, text=f"{audio.duration_ms:.0f}ms", width=60, text_color="gray").pack(side="left", padx=5)
        
        # Text Preview
        preview = audio.text[:60] + "..." if len(audio.text) > 60 else audio.text
        ctk.CTkLabel(row, text=preview, anchor="w").pack(side="left", fill="x", expand=True, padx=5)
        
        # Play Button
        btn = ctk.CTkButton(row, text="▶", width=30, height=25, fg_color="#3B8ED0", 
                            command=lambda: self.player.play(audio.file_path))
        btn.pack(side="right", padx=5, pady=2)

    def _start(self):
        api_keys = self._get_api_keys()
        if not api_keys:
            messagebox.showerror("Error", "Thiếu API key")
            self.tabview.set("⚙️ Configuration")
            return
        
        if not self.subtitles:
            messagebox.showerror("Error", "Load file đã rồi chạy")
            return
        
        self.is_processing = True
        self.btn_start.configure(state="disabled")
        self.btn_stop.configure(state="normal")
        
        # Get live_session_enabled from checkbox
        live_session_enabled = bool(self.tts_sw_live_session.get()) if hasattr(self, 'tts_sw_live_session') else False
        # Get keep_voice_beta from checkbox
        keep_voice_beta = bool(self.tts_sw_keep_voice_beta.get()) if hasattr(self, 'tts_sw_keep_voice_beta') else False
        
        # Build config
        config = TTSConfig(
            voice=self.combo_voice.get(),
            media_resolution=MEDIA_RESOLUTIONS.get(self.combo_res.get(), "MEDIA_RESOLUTION_MEDIUM"),
            thinking_mode=bool(self.sw_thinking.get()),
            thinking_budget=int(self.slider_budget.get()),
            affective_dialog=bool(self.sw_affective.get()),
            proactive_audio=bool(self.sw_proactive.get()),
            system_instruction=self.txt_sys_instr.get("1.0", "end").strip(),
            speed=self.slider_speed.get(),
            multi_worker_enabled=bool(self.sw_multi_worker.get()),
            workers_per_key=int(self.slider_workers.get()),
            live_session_enabled=live_session_enabled,
            keep_voice_beta=keep_voice_beta
        )
        
        if live_session_enabled:
            self.log("📞 Live Session Mode enabled - workers sẽ duy trì kết nối liên tục", "INFO")
        if keep_voice_beta:
            self.log("🎤 Giữ giọng beta enabled - text sẽ được wrap trong {nội dung}", "INFO")

        threading.Thread(target=self._process_thread, args=(api_keys, config), daemon=True).start()

    def _process_thread(self, api_keys, config):
        asyncio.run(self._process_async(api_keys, config))

    async def _process_async(self, api_keys, config):
        try:
            output_dir = Path(self.entry_out.get())
            output_dir.mkdir(parents=True, exist_ok=True)
            prefix = self.entry_prefix.get()

            self.processor = MultiThreadProcessor(
                api_keys=api_keys,
                config=config,
                log_callback=self.log,
                status_callback=lambda s: self.lbl_status.configure(text=s),
                progress_callback=self._update_main_progress,
                audio_callback=lambda a: self.audio_queue.put(a)
            )
            await self.processor.process_all(self.subtitles, output_dir, prefix)

        except Exception as e:
            self.log(f"❌ Fatal Error: {e}", "ERROR")
        finally:
            self.is_processing = False
            self.btn_start.configure(state="normal")
            self.btn_stop.configure(state="disabled")

    def _stop(self):
        if self.processor: self.processor.stop()
        self.log("⏹️ Stopping requested...", "WARNING")

    def _play_all(self):
        if not HAS_PYAUDIO: return
        self.is_playing_all = True
        self.current_play_index = 0
        self._play_next()

    def _play_next(self):
        # Simple Logic for play all (Could be improved)
        if not self.is_playing_all or self.current_play_index >= len(self.generated_audios):
            self.is_playing_all = False
            return
        audio = self.generated_audios[self.current_play_index]
        self.current_play_index += 1
        self.player.play(audio.file_path, on_complete=lambda: self.after(100, self._play_next))

    def _stop_playback(self):
        self.is_playing_all = False
        self.player.stop()

    def _update_main_progress(self, val):
        self.progress_bar.set(val / 100)

    # ==========================================================================
    # LONG TEXT LOGIC
    # ==========================================================================
    def _lt_browse_files(self):
        files = filedialog.askopenfilenames(filetypes=[("Text files", "*.txt"), ("All files", "*.*")])
        if files:
            self.lt_selected_files = list(files)
            self.lbl_lt_files.configure(text=f"{len(files)} files selected")
            self._lt_log(f"Selected {len(files)} files.", "INFO")

    def _lt_update_char_count(self, event=None):
        text = self.lt_txt_input.get("1.0", "end")
        count = len(text.replace(" ", "").replace("\n", ""))
        self.lt_lbl_chars.configure(text=f"Chars: {count}")

    def _lt_log(self, msg, level):
        self.lt_txt_log.configure(state="normal")
        self.lt_txt_log.insert("end", f"[{level}] {msg}\n")
        self.lt_txt_log.see("end")
        self.lt_txt_log.configure(state="disabled")

    def _lt_process_direct_text(self):
        text = self.lt_txt_input.get("1.0", "end").strip()
        if not text: return
        self._run_lt_processor(text=text, is_file=False)

    def _lt_process_files(self):
        if not self.lt_selected_files: return
        self._run_lt_processor(files=self.lt_selected_files, is_file=True)

    def _run_lt_processor(self, text=None, files=None, is_file=False):
        api_keys = self._get_api_keys()
        if not api_keys:
            messagebox.showerror("Error", "Chưa cài API key kìa thằng lz")
            return

        self.btn_lt_stop.configure(state="normal")
        
        # Get live_session_enabled from checkbox
        live_session_enabled = bool(self.lt_sw_live_session.get()) if hasattr(self, 'lt_sw_live_session') else False
        # Get keep_voice_beta from checkbox
        keep_voice_beta = bool(self.lt_sw_keep_voice_beta.get()) if hasattr(self, 'lt_sw_keep_voice_beta') else False
        
        config = TTSConfig(
            voice=self.lt_combo_voice.get(),
            media_resolution="MEDIA_RESOLUTION_MEDIUM",
            speed=1.0, # Could add slider
            system_instruction=self.txt_sys_instr.get("1.0", "end").strip(),
            multi_worker_enabled=bool(self.sw_multi_worker.get()),
            workers_per_key=int(self.slider_workers.get()),
            live_session_enabled=live_session_enabled,
            keep_voice_beta=keep_voice_beta
        )
        
        if live_session_enabled:
            self._lt_log("📞 Live Session Mode enabled - workers sẽ duy trì kết nối liên tục", "INFO")
        if keep_voice_beta:
            self._lt_log("🎤 Giữ giọng beta enabled - text sẽ được wrap trong {nội dung}", "INFO")
        
        threading.Thread(target=self._lt_thread, 
                         args=(api_keys, config, text, files, is_file), 
                         daemon=True).start()

    def _lt_thread(self, api_keys, config, text, files, is_file):
        asyncio.run(self._lt_async(api_keys, config, text, files, is_file))

    async def _lt_async(self, api_keys, config, text, files, is_file):
        out_dir = self.lt_entry_out.get()
        chunk_size = int(self.lt_chunk_size.get())
        ffmpeg = self.lt_entry_ffmpeg.get()
        delete_chunks = bool(self.lt_sw_del.get())
        # Get v2 chunking mode
        chunk_v2_enabled = bool(self.lt_sw_chunk_v2.get()) if hasattr(self, 'lt_sw_chunk_v2') else False
        
        self.long_text_processor = LongTextProcessor(
            api_keys=api_keys, config=config,
            log_callback=self._lt_log,
            status_callback=lambda s: None,
            progress_callback=lambda v: self.lt_progress.set(v/100)
        )

        try:
            if not is_file:
                # Direct text - clean whitespace first
                cleaned_text = clean_text_for_tts(text)
                await self.long_text_processor.process_text(
                    cleaned_text, os.path.join(out_dir, "direct_output.wav"), 
                    chunk_size, ffmpeg_path=ffmpeg, delete_chunks=delete_chunks,
                    chunk_v2_mode=chunk_v2_enabled
                )
            else:
                # Files
                for f in files:
                    out_name = Path(f).stem + ".wav"
                    with open(f, "r", encoding="utf-8") as rf:
                        content = rf.read()
                    # Clean whitespace
                    cleaned_content = clean_text_for_tts(content)
                    self._lt_log(f"Processing {out_name}...", "INFO")
                    await self.long_text_processor.process_text(
                        cleaned_content, os.path.join(out_dir, out_name),
                        chunk_size, ffmpeg_path=ffmpeg, delete_chunks=delete_chunks,
                        chunk_v2_mode=chunk_v2_enabled
                    )
        except Exception as e:
            self._lt_log(f"Error: {e}", "ERROR")
        finally:
            self.btn_lt_stop.configure(state="disabled")
            self.lt_progress.set(0)

    def _lt_stop(self):
        if self.long_text_processor: self.long_text_processor.stop()

    # ==========================================================================
    # UTILS
    # ==========================================================================
    def log(self, message: str, level: str = "INFO"):
        print(f"[{level}] {message}") # Debug write to console
        self.log_queue.put((message, level))

    def _start_consumers(self):
        def consume_logs():
            if self._is_closing:
                return
            try:
                while not self.log_queue.empty():
                    msg, level = self.log_queue.get()
                    self.txt_log.configure(state="normal")
                    color = "white"
                    if level == "ERROR": color = "#FF5555"
                    elif level == "SUCCESS": color = "#50FA7B"
                    elif level == "WARNING": color = "#FFB86C"
                    
                    # CustomTkinter Textbox doesn't support tags easily like Tkinter
                    # Just appending for now. ideally use a tag workaround if needed.
                    self.txt_log.insert("end", f"[{level}] {msg}\n") 
                    self.txt_log.see("end")
                    self.txt_log.configure(state="disabled")
                if not self._is_closing:
                    self.after(100, consume_logs)
            except Exception:
                pass  # Ignore errors during shutdown

        def consume_audio():
            if self._is_closing:
                return
            try:
                while not self.audio_queue.empty():
                    audio = self.audio_queue.get()
                    self.generated_audios.append(audio)
                    self.generated_audios.sort(key=lambda x: x.index)
                    self._add_audio_row(audio)
                if not self._is_closing:
                    self.after(100, consume_audio)
            except Exception:
                pass  # Ignore errors during shutdown

        self.after(100, consume_logs)
        self.after(100, consume_audio)

    def _on_close(self):
        # Set flag to stop consumers
        self._is_closing = True
        # Stop any active processors
        if self.processor:
            self.processor.stop()
        if self.long_text_processor:
            self.long_text_processor.stop()
        # Cleanup player
        self.player.cleanup()
        # Give time for callbacks to check the flag (200ms is sufficient for 100ms consumer polling)
        self.after(200, self._final_close)
    
    def _final_close(self):
        try:
            self.destroy()
        except Exception:
            pass
        os._exit(0)
# =============================================================================
# MAIN
# =============================================================================

# Global auth manager instance
_auth_manager: Optional[AuthManager] = None


def get_auth_manager() -> Optional[AuthManager]:
    """Get the global auth manager instance"""
    return _auth_manager


if __name__ == "__main__":
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    except:
        pass
    
    # ==========================================================================
    # LOGIN REQUIREMENT
    # ==========================================================================
    # Show login window before starting the main application
    # If login fails or is cancelled, exit the application
    
    # Default server URL - change this to your server
    DEFAULT_SERVER_URL = "http://34.173.37.168"
    
    # Initialize authentication manager
    _auth_manager = AuthManager(server_url=DEFAULT_SERVER_URL)
    
    # Try auto-login first (with saved credentials)
    auto_success, auto_msg = _auth_manager.auto_login()
    
    if auto_success:
        print(f"Auto-login successful: {_auth_manager.session.username}")
    else:
        # Show login dialog
        if not AuthManager.show_login_dialog(None, _auth_manager):
            print("Login cancelled or failed. Exiting...")
            sys.exit(0)
        print(f"Login successful: {_auth_manager.session.username}")
    
    # ==========================================================================
    # START MAIN APPLICATION
    # ==========================================================================
    app = StudioGUI()
    
    # Update window title with username
    if _auth_manager.session:
        app.title(f"VN TTS Studio - {_auth_manager.session.username}")
    
    app.mainloop()