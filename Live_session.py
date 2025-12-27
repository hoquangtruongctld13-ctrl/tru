# -*- coding: utf-8 -*-
"""
Gemini Live API Demo - Persistent Streaming Session
====================================================

Demo này tạo kết nối liên tục (streaming session) với Gemini Live API:
- Tab 1: Text-to-Speech (TTS) - Tạo voice từ text
- Tab 2: Translation - Dịch thuật text (Text-to-Text)

Tính năng:
- Kết nối liên tục với Gemini Live API
- Đa luồng với 1 API key
- System instruction rõ ràng
- UI đơn giản với CustomTkinter

Cài đặt:
    pip install google-genai customtkinter pyaudio

Sử dụng:
    python gemini_live_demo.py
"""

import asyncio
import json
import os
import sys
import threading
import wave
import time
import shutil
from dataclasses import dataclass
from pathlib import Path
from queue import Queue, Empty
from typing import Optional, List, Dict, Any
from concurrent.futures import ThreadPoolExecutor

try:
    import customtkinter as ctk
    from tkinter import filedialog, messagebox
except ImportError:
    print("Cần cài đặt customtkinter: pip install customtkinter")
    sys.exit(1)

try:
    from google import genai
    from google.genai import types
except ImportError:
    print("Cần cài đặt google-genai: pip install google-genai")
    sys.exit(1)

try:
    import pyaudio
    HAS_PYAUDIO = True
except ImportError:
    HAS_PYAUDIO = False
    print("Warning: PyAudio not installed - audio playback disabled")

# =============================================================================
# CONFIGURATION
# =============================================================================

# Model cho TTS (native audio)
TTS_MODEL = "models/gemini-2.5-flash-native-audio-preview-12-2025"

# Model cho Translation (text-to-text) - sử dụng live model non-native-audio
# QUAN TRỌNG: Model native-audio-preview KHÔNG hỗ trợ response_modalities=["TEXT"] alone
# Phải sử dụng model khác cho translation text-to-text
TRANSLATION_MODEL = "gemini-2.0-flash-live-001"

# Audio settings
RECEIVE_SAMPLE_RATE = 24000
AUDIO_CHANNELS = 1
AUDIO_SAMPLE_WIDTH = 2

# Available voices cho TTS
VOICES = [
    "Zephyr", "Puck", "Charon", "Kore", "Fenrir", "Leda", "Orus", "Aoede",
    "Callirrhoe", "Autonoe", "Enceladus", "Iapetus", "Umbriel", "Algieba",
    "Despina", "Erinome", "Algenib", "Rasalgethi", "Laomedeia", "Achernar",
    "Alnilam", "Schedar", "Gacrux", "Pulcherrima", "Achird", "Zubenelgenubi",
    "Vindemiatrix", "Sadachbia", "Sadaltager", "Sulafat"
]

# Language options cho translation
LANGUAGES = {
    "Tiếng Việt": "Vietnamese",
    "Tiếng Anh": "English",
    "Tiếng Nhật": "Japanese",
    "Tiếng Hàn": "Korean",
    "Tiếng Trung": "Chinese (Simplified)",
    "Tiếng Pháp": "French",
    "Tiếng Đức": "German",
    "Tiếng Tây Ban Nha": "Spanish",
    "Tiếng Bồ Đào Nha": "Portuguese",
    "Tiếng Nga": "Russian",
    "Tiếng Ý": "Italian",
    "Tiếng Thái": "Thai",
    "Tiếng Indonesia": "Indonesian",
}

# Default System Instructions
DEFAULT_TTS_INSTRUCTION = """Bạn là một trợ lý đọc văn bản. 
Chỉ cần đọc chính xác những gì người dùng gửi. 
Không thêm, không bớt, không giải thích gì thêm.
Đọc với giọng điệu tự nhiên, rõ ràng."""

DEFAULT_TRANSLATION_INSTRUCTION = """Bạn là một dịch giả chuyên nghiệp.
Chỉ trả về bản dịch, không giải thích hay thêm bất kỳ nội dung nào khác.
Giữ nguyên ý nghĩa và ngữ cảnh của văn bản gốc.
Dịch tự nhiên, không dịch máy móc từng từ."""

# Settings file
SETTINGS_FILE = "gemini_live_settings.json"

# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class TTSConfig:
    voice: str = "Kore"
    system_instruction: str = DEFAULT_TTS_INSTRUCTION


@dataclass
class TranslationConfig:
    source_lang: str = "Vietnamese"
    target_lang: str = "English"
    system_instruction: str = DEFAULT_TRANSLATION_INSTRUCTION


# =============================================================================
# GEMINI LIVE API MANAGER - Persistent Session
# =============================================================================

class GeminiLiveManager:
    """
    Quản lý kết nối liên tục với Gemini Live API.
    Hỗ trợ đa luồng với 1 API key thông qua multiple sessions.
    """
    
    def __init__(self, api_key: str, log_callback=None):
        self.api_key = api_key
        self.log = log_callback or print
        self.is_connected = False
        self._lock = threading.Lock()
        
        # Tạo client với API key
        self._setup_client()
    
    def _setup_client(self, api_version: str = "v1beta"):
        """Setup Google GenAI client"""
        self.client = genai.Client(
            http_options={"api_version": api_version},
            api_key=self.api_key,
        )
        self.log(f"✅ Client initialized (API version: {api_version})")
    
    async def generate_tts_audio(self, text: str, config: TTSConfig) -> Optional[bytes]:
        """
        Tạo audio từ text sử dụng Live API.
        Mỗi request là một session mới để đảm bảo ổn định.
        """
        try:
            # Build config cho TTS với system instruction
            live_config = types.LiveConnectConfig(
                response_modalities=["AUDIO"],
                speech_config=types.SpeechConfig(
                    voice_config=types.VoiceConfig(
                        prebuilt_voice_config=types.PrebuiltVoiceConfig(
                            voice_name=config.voice
                        )
                    )
                ),
                system_instruction=config.system_instruction,
            )
            
            # Text input (system instruction đã được set trong config)
            input_text = text
            
            self.log(f"🎤 Đang tạo audio với voice: {config.voice}")
            self.log(f"📝 Text: {text[:50]}..." if len(text) > 50 else f"📝 Text: {text}")
            
            audio_chunks = []
            
            # Mở session và gửi request
            async with self.client.aio.live.connect(
                model=TTS_MODEL, 
                config=live_config
            ) as session:
                # Gửi text với end_of_turn=True
                await session.send(input=input_text, end_of_turn=True)
                
                # Nhận audio chunks
                async for response in session.receive():
                    if data := response.data:
                        audio_chunks.append(data)
                        self.log(".", end="")
            
            self.log("")  # New line after dots
            
            if audio_chunks:
                self.log(f"✅ Nhận được {len(audio_chunks)} chunks audio")
                return b''.join(audio_chunks)
            else:
                self.log("❌ Không nhận được audio data")
                return None
                
        except Exception as e:
            self.log(f"❌ Lỗi TTS: {str(e)}")
            return None
    
    async def translate_text(self, text: str, config: TranslationConfig) -> Optional[str]:
        """
        Dịch text sử dụng Live API (Text-to-Text).
        
        QUAN TRỌNG: 
        - Model native-audio-preview KHÔNG hỗ trợ response_modalities=["TEXT"] alone
        - Phải sử dụng model khác (gemini-2.0-flash-live-001) cho text-to-text translation
        - Lỗi "Cannot extract voices from a non-audio request" xảy ra khi dùng
          native-audio model với TEXT-only modalities
        """
        try:
            # Build config cho translation (text output)
            # QUAN TRỌNG: Dùng TRANSLATION_MODEL (gemini-2.0-flash-live-001)
            # KHÔNG dùng TTS_MODEL (native-audio) vì nó không hỗ trợ TEXT-only
            live_config = types.LiveConnectConfig(
                response_modalities=["TEXT"],
                system_instruction=config.system_instruction,
            )
            
            # Tạo prompt dịch thuật đơn giản
            translation_prompt = f"""Dịch văn bản sau từ {config.source_lang} sang {config.target_lang}. Chỉ trả về bản dịch, không giải thích:

"{text}"""
            
            self.log(f"🌐 Đang dịch từ {config.source_lang} sang {config.target_lang}")
            self.log(f"📝 Text gốc: {text[:50]}..." if len(text) > 50 else f"📝 Text gốc: {text}")
            self.log(f"🔧 Model: {TRANSLATION_MODEL}")
            
            translated_text = []
            
            # Mở session và gửi request
            # Sử dụng TRANSLATION_MODEL (non-native-audio) cho text-to-text
            async with self.client.aio.live.connect(
                model=TRANSLATION_MODEL, 
                config=live_config
            ) as session:
                # Sử dụng send() với end_of_turn=True
                await session.send(input=translation_prompt, end_of_turn=True)
                
                # Nhận text response
                async for response in session.receive():
                    if text_chunk := response.text:
                        translated_text.append(text_chunk)
                        self.log(".", end="")
            
            self.log("")  # New line after dots
            
            if translated_text:
                result = ''.join(translated_text).strip()
                self.log(f"✅ Dịch thành công: {len(result)} ký tự")
                return result
            else:
                self.log("❌ Không nhận được kết quả dịch")
                return None
                
        except Exception as e:
            self.log(f"❌ Lỗi dịch thuật: {str(e)}")
            return None


# =============================================================================
# PERSISTENT TTS SESSION - Phiên kết nối liên tục
# =============================================================================

class PersistentTTSSession:
    """
    Phiên TTS liên tục - giống như một cuộc gọi điện thoại với Gemini.
    
    Logic:
    - Giữ client và config sẵn sàng
    - Khi cần generate audio, tạo session mới và gửi request
    - Session tự động đóng sau mỗi turn để tránh timeout
    - Cách này đáng tin cậy hơn giữ session mở liên tục
    
    Lưu ý quan trọng về gemini-2.5-flash-native-audio-preview:
    - Model này YÊU CẦU response_modalities phải có "AUDIO"
    - Không hỗ trợ response_modalities=["TEXT"] alone
    - Để bypass và nhận cả text lẫn audio, dùng response_modalities=["AUDIO"]
      và model sẽ tự động trả về audio (không có text transcript trong native-audio)
    """
    
    def __init__(self, api_key: str, config: TTSConfig, log_callback=None):
        self.api_key = api_key
        self.config = config
        self.log = log_callback or print
        self.client = None
        self.is_connected = False
        self._running = False
        self._lock = asyncio.Lock()
        self._live_config = None
        
    def _setup_client(self, api_version: str = "v1beta"):
        """Setup Google GenAI client"""
        self.client = genai.Client(
            http_options={"api_version": api_version},
            api_key=self.api_key,
        )
    
    def _build_config(self) -> types.LiveConnectConfig:
        """Build LiveConnectConfig cho TTS"""
        return types.LiveConnectConfig(
            response_modalities=["AUDIO"],
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                        voice_name=self.config.voice
                    )
                )
            ),
            system_instruction=self.config.system_instruction,
        )
    
    async def connect(self):
        """
        Initialize client và config cho Persistent Session.
        Client sẽ được giữ sẵn sàng để tạo session khi cần.
        """
        if self.is_connected:
            self.log("⚠️ Session đã được khởi tạo")
            return True
            
        try:
            self._setup_client()
            self._live_config = self._build_config()
            
            self.log(f"🔗 Khởi tạo Persistent Session...")
            self.log(f"🎭 Voice: {self.config.voice}")
            
            # Test connection bằng cách tạo một session test
            async with self.client.aio.live.connect(
                model=TTS_MODEL,
                config=self._live_config
            ) as session:
                # Gửi một text ngắn để test
                await session.send(input="test", end_of_turn=True)
                async for _ in session.receive():
                    break  # Chỉ cần nhận 1 response để confirm hoạt động
            
            self.is_connected = True
            self._running = True
            
            self.log(f"✅ Persistent Session sẵn sàng!")
            return True
            
        except Exception as e:
            self.log(f"❌ Lỗi khởi tạo: {str(e)}")
            self.is_connected = False
            return False
    
    async def disconnect(self):
        """Cleanup và đánh dấu ngắt kết nối"""
        self._running = False
        self.is_connected = False
        self.client = None
        self._live_config = None
        self.log("🔌 Đã ngắt kết nối Persistent Session")
    
    async def generate_audio(self, text: str) -> Optional[bytes]:
        """
        Gửi văn bản và nhận audio.
        Mỗi request tạo session mới nhưng sử dụng chung client và config.
        
        Args:
            text: Văn bản cần đọc
            
        Returns:
            bytes: PCM audio data hoặc None nếu lỗi
        """
        if not self.is_connected or not self.client:
            self.log("❌ Chưa kết nối! Gọi connect() trước.")
            return None
        
        try:
            async with self._lock:
                self.log(f"📝 Gửi: {text[:50]}..." if len(text) > 50 else f"📝 Gửi: {text}")
                
                audio_chunks = []
                
                # Tạo session mới cho mỗi request (sử dụng async with đúng cách)
                async with self.client.aio.live.connect(
                    model=TTS_MODEL,
                    config=self._live_config
                ) as session:
                    # Gửi text
                    await session.send(input=text, end_of_turn=True)
                    
                    # Thu thập audio chunks
                    async for response in session.receive():
                        if data := response.data:
                            audio_chunks.append(data)
                            self.log(".", end="")
                
                self.log("")  # New line
                
                if audio_chunks:
                    self.log(f"✅ Nhận {len(audio_chunks)} chunks audio")
                    return b''.join(audio_chunks)
                else:
                    self.log("⚠️ Không nhận được audio")
                    return None
                    
        except Exception as e:
            self.log(f"❌ Lỗi generate_audio: {str(e)}")
            return None
    
    async def generate_audio_batch(self, texts: List[str], 
                                    progress_callback=None) -> List[tuple]:
        """
        Xử lý batch văn bản.
        
        Args:
            texts: List văn bản cần đọc
            progress_callback: Callback để cập nhật progress (0-100)
            
        Returns:
            List of (index, audio_bytes or None)
        """
        results = []
        total = len(texts)
        
        if not self.is_connected:
            success = await self.connect()
            if not success:
                return [(i, None) for i in range(total)]
        
        for i, text in enumerate(texts):
            if not self._running:
                self.log("⏹ Đã dừng bởi người dùng")
                results.append((i, None))
                continue
                
            audio = await self.generate_audio(text)
            results.append((i, audio))
            
            if progress_callback:
                progress_callback((i + 1) / total * 100)
        
        return results
    
    def stop(self):
        """Dừng xử lý"""
        self._running = False


# =============================================================================
# MULTI-THREADED PROCESSOR
# =============================================================================

class MultiThreadedProcessor:
    """
    Xử lý đa luồng với 1 API key.
    Mỗi thread tạo session riêng để tránh conflict.
    """
    
    def __init__(self, api_key: str, max_workers: int = 2, log_callback=None):
        """
        Initialize multi-threaded processor.
        
        Args:
            api_key: Gemini API key
            max_workers: Maximum concurrent workers (default 2 to avoid rate limiting)
            log_callback: Logging function
        """
        self.api_key = api_key
        self.max_workers = max_workers
        self.log = log_callback or print
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.is_running = False
        self._lock = threading.Lock()
    
    def process_tts_batch(self, texts: List[str], config: TTSConfig, 
                          progress_callback=None) -> List[tuple]:
        """
        Xử lý batch TTS với đa luồng.
        Returns: List of (index, audio_bytes or None)
        """
        self.is_running = True
        results = []
        total = len(texts)
        completed = 0
        lock = threading.Lock()
        
        def process_single(index: int, text: str) -> tuple:
            nonlocal completed
            
            if not self.is_running:
                return (index, None)
            
            # Mỗi thread tạo manager riêng
            manager = GeminiLiveManager(self.api_key, log_callback=self.log)
            
            # Chạy async trong thread
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                audio = loop.run_until_complete(
                    manager.generate_tts_audio(text, config)
                )
                return (index, audio)
            except Exception as e:
                self.log(f"❌ Error in thread {index}: {e}")
                return (index, None)
            finally:
                loop.close()
                with lock:
                    completed += 1
                    if progress_callback:
                        progress_callback(completed / total * 100)
        
        # Submit tasks to thread pool
        futures = []
        for i, text in enumerate(texts):
            future = self.executor.submit(process_single, i, text)
            futures.append(future)
        
        # Collect results
        for future in futures:
            try:
                result = future.result(timeout=60)  # 1 minute timeout per request
                results.append(result)
            except Exception as e:
                self.log(f"❌ Task error: {e}")
        
        self.is_running = False
        return sorted(results, key=lambda x: x[0])
    
    def stop(self):
        """Dừng xử lý"""
        self.is_running = False


# =============================================================================
# AUDIO PLAYER
# =============================================================================

class AudioPlayer:
    """Simple audio player for WAV data"""
    
    def __init__(self):
        self.is_playing = False
        self.should_stop = False
        self.play_thread = None
        
        if HAS_PYAUDIO:
            self.pya = pyaudio.PyAudio()
        else:
            self.pya = None
    
    def play_pcm(self, pcm_data: bytes, sample_rate: int = RECEIVE_SAMPLE_RATE):
        """Play PCM audio data"""
        if not HAS_PYAUDIO or not self.pya:
            print("PyAudio not available - cannot play audio")
            return
        
        self.stop()
        self.should_stop = False
        
        def _play():
            try:
                self.is_playing = True
                stream = self.pya.open(
                    format=pyaudio.paInt16,
                    channels=AUDIO_CHANNELS,
                    rate=sample_rate,
                    output=True
                )
                
                chunk_size = 1024
                pos = 0
                while pos < len(pcm_data) and not self.should_stop:
                    chunk = pcm_data[pos:pos + chunk_size]
                    if chunk:
                        stream.write(chunk)
                    pos += chunk_size
                
                stream.stop_stream()
                stream.close()
            except Exception as e:
                print(f"Play error: {e}")
            finally:
                self.is_playing = False
        
        self.play_thread = threading.Thread(target=_play, daemon=True)
        self.play_thread.start()
    
    def play_file(self, file_path: str):
        """Play WAV file"""
        if not HAS_PYAUDIO or not self.pya:
            return
        
        self.stop()
        self.should_stop = False
        
        def _play():
            try:
                self.is_playing = True
                wf = wave.open(file_path, 'rb')
                
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
            finally:
                self.is_playing = False
        
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
        if self.pya:
            self.pya.terminate()


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def save_wave_file(filename: str, pcm_data: bytes, rate: int = RECEIVE_SAMPLE_RATE):
    """Save PCM data to WAV file"""
    with wave.open(filename, "wb") as wf:
        wf.setnchannels(AUDIO_CHANNELS)
        wf.setsampwidth(AUDIO_SAMPLE_WIDTH)
        wf.setframerate(rate)
        wf.writeframes(pcm_data)


def get_app_dir() -> str:
    """Get application directory"""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


# =============================================================================
# MAIN GUI APPLICATION
# =============================================================================

class GeminiLiveDemoApp(ctk.CTk):
    """
    Main application với 2 tabs:
    - Tab 1: Text-to-Speech (TTS)
    - Tab 2: Translation (Text-to-Text)
    """
    
    def __init__(self):
        super().__init__()
        
        # Configure window
        self.title("🎙️ Gemini Live API Demo - Persistent Streaming")
        self.geometry("1000x700")
        
        # Set theme
        ctk.set_appearance_mode("Dark")
        ctk.set_default_color_theme("blue")
        
        # Initialize variables
        self.api_key = ""
        self.manager = None
        self.processor = None
        self.player = AudioPlayer()
        self.log_queue = Queue()
        self.is_processing = False
        self._is_closing = False
        
        # Last generated audio
        self.last_audio_data = None
        
        # Persistent TTS Session - giữ client sẵn sàng để tạo session nhanh hơn
        self.persistent_session: Optional[PersistentTTSSession] = None
        
        # Load settings
        self._load_settings()
        
        # Build UI
        self._build_ui()
        
        # Start log consumer
        self._start_log_consumer()
        
        # Handle close event
        self.protocol("WM_DELETE_WINDOW", self._on_close)
    
    def _build_ui(self):
        """Build the main UI"""
        
        # Main container
        main_frame = ctk.CTkFrame(self)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # ===== API KEY SECTION (Top) =====
        api_frame = ctk.CTkFrame(main_frame)
        api_frame.pack(fill="x", padx=5, pady=5)
        
        ctk.CTkLabel(api_frame, text="🔑 API Key:", font=("Roboto", 12, "bold")).pack(side="left", padx=5)
        
        self.entry_api_key = ctk.CTkEntry(api_frame, width=500, show="*", 
                                          placeholder_text="Nhập Gemini API Key...")
        self.entry_api_key.pack(side="left", padx=5, fill="x", expand=True)
        if self.api_key:
            self.entry_api_key.insert(0, self.api_key)
        
        self.btn_show_key = ctk.CTkButton(api_frame, text="👁", width=40,
                                          command=self._toggle_api_key_visibility)
        self.btn_show_key.pack(side="left", padx=2)
        
        self.btn_save_key = ctk.CTkButton(api_frame, text="💾 Lưu", width=80,
                                          command=self._save_settings)
        self.btn_save_key.pack(side="left", padx=5)
        
        # ===== TABVIEW =====
        self.tabview = ctk.CTkTabview(main_frame)
        self.tabview.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Create tabs
        self.tab_tts = self.tabview.add("🎤 Text-to-Speech")
        self.tab_translation = self.tabview.add("🌐 Dịch Thuật")
        self.tab_settings = self.tabview.add("⚙️ Cài Đặt")
        
        # Build each tab
        self._build_tts_tab()
        self._build_translation_tab()
        self._build_settings_tab()
        
        # ===== LOG SECTION (Bottom) =====
        log_frame = ctk.CTkFrame(main_frame)
        log_frame.pack(fill="x", padx=5, pady=5)
        
        ctk.CTkLabel(log_frame, text="📋 Log:", font=("Roboto", 11, "bold")).pack(anchor="w", padx=5)
        
        self.txt_log = ctk.CTkTextbox(log_frame, height=100, font=("Consolas", 10))
        self.txt_log.pack(fill="x", padx=5, pady=5)
        self.txt_log.configure(state="disabled")
    
    def _build_tts_tab(self):
        """Build TTS tab UI"""
        tab = self.tab_tts
        
        # Left panel - Input
        left_frame = ctk.CTkFrame(tab)
        left_frame.pack(side="left", fill="both", expand=True, padx=5, pady=5)
        
        # Voice selection và Persistent Session control
        voice_frame = ctk.CTkFrame(left_frame)
        voice_frame.pack(fill="x", padx=5, pady=5)
        
        ctk.CTkLabel(voice_frame, text="🎭 Voice:", font=("Roboto", 11)).pack(side="left", padx=5)
        
        self.combo_voice = ctk.CTkComboBox(voice_frame, values=VOICES, width=150)
        self.combo_voice.pack(side="left", padx=5)
        self.combo_voice.set("Kore")
        
        # Separator
        ctk.CTkLabel(voice_frame, text="|", text_color="gray").pack(side="left", padx=10)
        
        # Persistent Session Mode checkbox
        self.use_persistent_session = ctk.CTkCheckBox(voice_frame, text="📞 Phiên liên tục", 
                                                       font=("Roboto", 10))
        self.use_persistent_session.pack(side="left", padx=5)
        
        # Session status indicator
        self.session_status = ctk.CTkLabel(voice_frame, text="⚪ Chưa kết nối", 
                                            font=("Roboto", 10), text_color="gray")
        self.session_status.pack(side="left", padx=10)
        
        # Connect/Disconnect button
        self.btn_session = ctk.CTkButton(voice_frame, text="🔗 Kết nối", width=90,
                                         fg_color="#3b82f6", command=self._toggle_session)
        self.btn_session.pack(side="left", padx=5)
        
        # Text input
        ctk.CTkLabel(left_frame, text="📝 Nhập văn bản:", font=("Roboto", 11, "bold")).pack(anchor="w", padx=5, pady=2)
        
        self.txt_tts_input = ctk.CTkTextbox(left_frame, height=200, font=("Roboto", 11))
        self.txt_tts_input.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Buttons
        btn_frame = ctk.CTkFrame(left_frame, fg_color="transparent")
        btn_frame.pack(fill="x", padx=5, pady=5)
        
        self.btn_generate_tts = ctk.CTkButton(btn_frame, text="🎤 Tạo Audio", 
                                               fg_color="#22c55e", hover_color="#16a34a",
                                               command=self._generate_tts)
        self.btn_generate_tts.pack(side="left", padx=5)
        
        self.btn_play_tts = ctk.CTkButton(btn_frame, text="▶ Phát", width=80,
                                          state="disabled", command=self._play_tts)
        self.btn_play_tts.pack(side="left", padx=5)
        
        self.btn_stop_tts = ctk.CTkButton(btn_frame, text="⏹ Dừng", width=80,
                                          fg_color="#dc2626", command=self._stop_tts)
        self.btn_stop_tts.pack(side="left", padx=5)
        
        self.btn_save_tts = ctk.CTkButton(btn_frame, text="💾 Lưu Audio", width=100,
                                          state="disabled", command=self._save_tts)
        self.btn_save_tts.pack(side="left", padx=5)
        
        # Progress
        self.tts_progress = ctk.CTkProgressBar(left_frame)
        self.tts_progress.pack(fill="x", padx=5, pady=5)
        self.tts_progress.set(0)
        
        self.tts_status = ctk.CTkLabel(left_frame, text="Sẵn sàng", text_color="gray")
        self.tts_status.pack(anchor="w", padx=5)
        
        # Right panel - System Instruction
        right_frame = ctk.CTkFrame(tab, width=300)
        right_frame.pack(side="right", fill="y", padx=5, pady=5)
        right_frame.pack_propagate(False)
        
        ctk.CTkLabel(right_frame, text="🎯 System Instruction:", 
                     font=("Roboto", 11, "bold")).pack(anchor="w", padx=5, pady=5)
        
        self.txt_tts_instruction = ctk.CTkTextbox(right_frame, height=150, font=("Roboto", 10))
        self.txt_tts_instruction.pack(fill="both", expand=True, padx=5, pady=5)
        self.txt_tts_instruction.insert("1.0", DEFAULT_TTS_INSTRUCTION)
        
        ctk.CTkButton(right_frame, text="🔄 Reset mặc định", width=120,
                     command=lambda: self._reset_instruction(self.txt_tts_instruction, DEFAULT_TTS_INSTRUCTION)
                     ).pack(pady=5)
    
    def _build_translation_tab(self):
        """Build Translation tab UI"""
        tab = self.tab_translation
        
        # Main container with two panels
        main_container = ctk.CTkFrame(tab, fg_color="transparent")
        main_container.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Language selection row
        lang_frame = ctk.CTkFrame(main_container)
        lang_frame.pack(fill="x", padx=5, pady=5)
        
        ctk.CTkLabel(lang_frame, text="🌍 Từ:", font=("Roboto", 11)).pack(side="left", padx=5)
        
        self.combo_source_lang = ctk.CTkComboBox(lang_frame, values=list(LANGUAGES.keys()), width=150)
        self.combo_source_lang.pack(side="left", padx=5)
        self.combo_source_lang.set("Tiếng Việt")
        
        ctk.CTkLabel(lang_frame, text="➡️ Sang:", font=("Roboto", 11)).pack(side="left", padx=20)
        
        self.combo_target_lang = ctk.CTkComboBox(lang_frame, values=list(LANGUAGES.keys()), width=150)
        self.combo_target_lang.pack(side="left", padx=5)
        self.combo_target_lang.set("Tiếng Anh")
        
        # Swap button
        ctk.CTkButton(lang_frame, text="🔄 Đổi", width=60, 
                     command=self._swap_languages).pack(side="left", padx=10)
        
        # Text areas container
        text_container = ctk.CTkFrame(main_container, fg_color="transparent")
        text_container.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Source text (left)
        source_frame = ctk.CTkFrame(text_container)
        source_frame.pack(side="left", fill="both", expand=True, padx=2)
        
        ctk.CTkLabel(source_frame, text="📝 Văn bản gốc:", 
                     font=("Roboto", 11, "bold")).pack(anchor="w", padx=5, pady=2)
        
        self.txt_source = ctk.CTkTextbox(source_frame, height=200, font=("Roboto", 11))
        self.txt_source.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Target text (right)
        target_frame = ctk.CTkFrame(text_container)
        target_frame.pack(side="right", fill="both", expand=True, padx=2)
        
        ctk.CTkLabel(target_frame, text="📄 Bản dịch:", 
                     font=("Roboto", 11, "bold")).pack(anchor="w", padx=5, pady=2)
        
        self.txt_target = ctk.CTkTextbox(target_frame, height=200, font=("Roboto", 11))
        self.txt_target.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Buttons
        btn_frame = ctk.CTkFrame(main_container, fg_color="transparent")
        btn_frame.pack(fill="x", padx=5, pady=5)
        
        self.btn_translate = ctk.CTkButton(btn_frame, text="🌐 Dịch", 
                                            fg_color="#3b82f6", hover_color="#2563eb",
                                            command=self._translate)
        self.btn_translate.pack(side="left", padx=5)
        
        ctk.CTkButton(btn_frame, text="📋 Copy", width=80,
                     command=self._copy_translation).pack(side="left", padx=5)
        
        ctk.CTkButton(btn_frame, text="🗑️ Xóa", width=80, fg_color="#dc2626",
                     command=self._clear_translation).pack(side="left", padx=5)
        
        # Progress
        self.trans_progress = ctk.CTkProgressBar(main_container)
        self.trans_progress.pack(fill="x", padx=5, pady=5)
        self.trans_progress.set(0)
        
        self.trans_status = ctk.CTkLabel(main_container, text="Sẵn sàng", text_color="gray")
        self.trans_status.pack(anchor="w", padx=5)
        
        # System instruction section (collapsible)
        instr_frame = ctk.CTkFrame(main_container)
        instr_frame.pack(fill="x", padx=5, pady=5)
        
        ctk.CTkLabel(instr_frame, text="🎯 System Instruction (Hướng dẫn dịch):", 
                     font=("Roboto", 10)).pack(anchor="w", padx=5, pady=2)
        
        self.txt_trans_instruction = ctk.CTkTextbox(instr_frame, height=80, font=("Roboto", 10))
        self.txt_trans_instruction.pack(fill="x", padx=5, pady=5)
        self.txt_trans_instruction.insert("1.0", DEFAULT_TRANSLATION_INSTRUCTION)
    
    def _build_settings_tab(self):
        """Build Settings tab UI"""
        tab = self.tab_settings
        
        # Settings container
        settings_frame = ctk.CTkFrame(tab)
        settings_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        ctk.CTkLabel(settings_frame, text="⚙️ Cài Đặt Ứng Dụng", 
                     font=("Roboto", 16, "bold")).pack(pady=10)
        
        # Multi-threading settings
        thread_frame = ctk.CTkFrame(settings_frame)
        thread_frame.pack(fill="x", padx=10, pady=10)
        
        ctk.CTkLabel(thread_frame, text="🔧 Đa luồng (Multi-threading):", 
                     font=("Roboto", 12, "bold")).pack(anchor="w", padx=10, pady=5)
        
        worker_frame = ctk.CTkFrame(thread_frame, fg_color="transparent")
        worker_frame.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkLabel(worker_frame, text="Số workers (threads):").pack(side="left", padx=5)
        
        self.slider_workers = ctk.CTkSlider(worker_frame, from_=1, to=5, number_of_steps=4, width=150)
        self.slider_workers.pack(side="left", padx=10)
        self.slider_workers.set(2)  # Default to 2 to avoid rate limiting
        
        self.lbl_workers = ctk.CTkLabel(worker_frame, text="2")
        self.lbl_workers.pack(side="left", padx=5)
        
        self.slider_workers.configure(command=lambda v: self.lbl_workers.configure(text=str(int(v))))
        
        # Info text
        info_text = """
📌 Hướng dẫn sử dụng:

1. TTS (Text-to-Speech):
   - Nhập API Key của bạn
   - Chọn Voice (giọng đọc)
   - Nhập văn bản cần đọc
   - Nhấn "Tạo Audio"
   
2. Dịch Thuật:
   - Chọn ngôn ngữ nguồn và đích
   - Nhập văn bản cần dịch
   - Nhấn "Dịch"

3. System Instruction:
   - Hướng dẫn cho AI cách xử lý văn bản
   - Có thể tùy chỉnh theo nhu cầu

⚠️ Lưu ý:
   - Cần có API Key từ Google AI Studio
   - Kết nối internet ổn định
   - Text dài sẽ được xử lý theo chunks
        """
        
        info_box = ctk.CTkTextbox(settings_frame, height=300, font=("Roboto", 11))
        info_box.pack(fill="both", expand=True, padx=10, pady=10)
        info_box.insert("1.0", info_text)
        info_box.configure(state="disabled")
    
    # =========================================================================
    # TTS METHODS
    # =========================================================================
    
    def _generate_tts(self):
        """Generate TTS audio"""
        text = self.txt_tts_input.get("1.0", "end").strip()
        if not text:
            messagebox.showerror("Lỗi", "Vui lòng nhập văn bản!")
            return
        
        api_key = self.entry_api_key.get().strip()
        if not api_key:
            messagebox.showerror("Lỗi", "Vui lòng nhập API Key!")
            self.tabview.set("⚙️ Cài Đặt")
            return
        
        # Get config
        voice = self.combo_voice.get()
        instruction = self.txt_tts_instruction.get("1.0", "end").strip()
        
        config = TTSConfig(voice=voice, system_instruction=instruction)
        
        # Update UI
        self.btn_generate_tts.configure(state="disabled")
        self.tts_status.configure(text="Đang xử lý...")
        self.tts_progress.set(0)
        
        # Run in thread
        threading.Thread(target=self._tts_worker, args=(api_key, text, config), daemon=True).start()
    
    def _tts_worker(self, api_key: str, text: str, config: TTSConfig):
        """TTS worker thread"""
        try:
            # Check if using persistent session
            use_persistent = self.use_persistent_session.get()
            
            if use_persistent and self.persistent_session and self.persistent_session.is_connected:
                # Use persistent session - sử dụng client đã khởi tạo
                self._log("📞 Sử dụng Persistent Session")
                self.after(0, lambda: self.tts_progress.set(0.3))
                
                # Create new event loop for this request
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                try:
                    audio_data = loop.run_until_complete(
                        self.persistent_session.generate_audio(text)
                    )
                finally:
                    loop.close()
            else:
                # Use normal session - tạo session mới cho mỗi request
                if use_persistent and not (self.persistent_session and self.persistent_session.is_connected):
                    self._log("⚠️ Persistent Session chưa kết nối, sử dụng session thường")
                
                # Create manager
                manager = GeminiLiveManager(api_key, log_callback=self._log)
                
                # Progress simulation
                self.after(0, lambda: self.tts_progress.set(0.3))
                
                # Run async task
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                try:
                    audio_data = loop.run_until_complete(
                        manager.generate_tts_audio(text, config)
                    )
                finally:
                    loop.close()
            
            self.after(0, lambda: self.tts_progress.set(1.0))
            
            if audio_data:
                self.last_audio_data = audio_data
                self.after(0, lambda: self.btn_play_tts.configure(state="normal"))
                self.after(0, lambda: self.btn_save_tts.configure(state="normal"))
                self.after(0, lambda: self.tts_status.configure(text="✅ Hoàn thành!"))
                self._log("✅ Tạo audio thành công!")
            else:
                self.after(0, lambda: self.tts_status.configure(text="❌ Lỗi!"))
                self._log("❌ Không thể tạo audio")
                
        except Exception as e:
            self._log(f"❌ Lỗi: {str(e)}")
            self.after(0, lambda: self.tts_status.configure(text="❌ Lỗi!"))
        finally:
            self.after(0, lambda: self.btn_generate_tts.configure(state="normal"))
    
    def _play_tts(self):
        """Play generated TTS audio"""
        if self.last_audio_data:
            self.player.play_pcm(self.last_audio_data)
            self._log("▶ Đang phát audio...")
    
    def _stop_tts(self):
        """Stop TTS playback"""
        self.player.stop()
        self._log("⏹ Đã dừng phát")
    
    def _save_tts(self):
        """Save TTS audio to file"""
        if not self.last_audio_data:
            return
        
        file_path = filedialog.asksaveasfilename(
            defaultextension=".wav",
            filetypes=[("WAV files", "*.wav"), ("All files", "*.*")]
        )
        
        if file_path:
            save_wave_file(file_path, self.last_audio_data)
            self._log(f"💾 Đã lưu: {file_path}")
            messagebox.showinfo("Thành công", f"Đã lưu audio: {file_path}")
    
    # =========================================================================
    # PERSISTENT SESSION METHODS
    # =========================================================================
    
    def _toggle_session(self):
        """Toggle persistent session connection"""
        if self.persistent_session and self.persistent_session.is_connected:
            # Disconnect
            self._disconnect_session()
        else:
            # Connect
            self._connect_session()
    
    def _connect_session(self):
        """Connect persistent session"""
        api_key = self.entry_api_key.get().strip()
        if not api_key:
            messagebox.showerror("Lỗi", "Vui lòng nhập API Key!")
            return
        
        voice = self.combo_voice.get()
        instruction = self.txt_tts_instruction.get("1.0", "end").strip()
        config = TTSConfig(voice=voice, system_instruction=instruction)
        
        self._log("🔗 Đang kết nối Persistent Session...")
        self.session_status.configure(text="🟡 Đang kết nối...", text_color="yellow")
        self.btn_session.configure(state="disabled")
        
        def connect_thread():
            # Create new event loop for connection test
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                self.persistent_session = PersistentTTSSession(
                    api_key, config, log_callback=self._log
                )
                success = loop.run_until_complete(
                    self.persistent_session.connect()
                )
                
                if success:
                    self.after(0, lambda: self.session_status.configure(
                        text="🟢 Sẵn sàng", text_color="green"))
                    self.after(0, lambda: self.btn_session.configure(
                        text="🔌 Ngắt kết nối", fg_color="#dc2626", state="normal"))
                else:
                    self.after(0, lambda: self.session_status.configure(
                        text="🔴 Lỗi kết nối", text_color="red"))
                    self.after(0, lambda: self.btn_session.configure(state="normal"))
            except Exception as e:
                self._log(f"❌ Lỗi kết nối: {str(e)}")
                self.after(0, lambda: self.session_status.configure(
                    text="🔴 Lỗi", text_color="red"))
                self.after(0, lambda: self.btn_session.configure(state="normal"))
            finally:
                loop.close()
        
        threading.Thread(target=connect_thread, daemon=True).start()
    
    def _disconnect_session(self):
        """Disconnect persistent session"""
        if not self.persistent_session:
            return
        
        self._log("🔌 Đang ngắt kết nối...")
        
        def disconnect_thread():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                if self.persistent_session:
                    loop.run_until_complete(
                        self.persistent_session.disconnect()
                    )
                
                self.persistent_session = None
                self.after(0, lambda: self.session_status.configure(
                    text="⚪ Chưa kết nối", text_color="gray"))
                self.after(0, lambda: self.btn_session.configure(
                    text="🔗 Kết nối", fg_color="#3b82f6"))
                self._log("✅ Đã ngắt kết nối")
            except Exception as e:
                self._log(f"⚠️ Lỗi khi ngắt: {str(e)}")
            finally:
                loop.close()
        
        threading.Thread(target=disconnect_thread, daemon=True).start()
    
    # =========================================================================
    # TRANSLATION METHODS
    # =========================================================================
    
    def _translate(self):
        """Translate text"""
        text = self.txt_source.get("1.0", "end").strip()
        if not text:
            messagebox.showerror("Lỗi", "Vui lòng nhập văn bản cần dịch!")
            return
        
        api_key = self.entry_api_key.get().strip()
        if not api_key:
            messagebox.showerror("Lỗi", "Vui lòng nhập API Key!")
            return
        
        # Get config
        source_lang = LANGUAGES.get(self.combo_source_lang.get(), "Vietnamese")
        target_lang = LANGUAGES.get(self.combo_target_lang.get(), "English")
        instruction = self.txt_trans_instruction.get("1.0", "end").strip()
        
        config = TranslationConfig(
            source_lang=source_lang,
            target_lang=target_lang,
            system_instruction=instruction
        )
        
        # Update UI
        self.btn_translate.configure(state="disabled")
        self.trans_status.configure(text="Đang dịch...")
        self.trans_progress.set(0)
        
        # Clear previous result
        self.txt_target.delete("1.0", "end")
        
        # Run in thread
        threading.Thread(target=self._translate_worker, args=(api_key, text, config), daemon=True).start()
    
    def _translate_worker(self, api_key: str, text: str, config: TranslationConfig):
        """Translation worker thread"""
        try:
            # Create manager
            manager = GeminiLiveManager(api_key, log_callback=self._log)
            
            # Progress simulation
            self.after(0, lambda: self.trans_progress.set(0.3))
            
            # Run async task
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                result = loop.run_until_complete(
                    manager.translate_text(text, config)
                )
            finally:
                loop.close()
            
            self.after(0, lambda: self.trans_progress.set(1.0))
            
            if result:
                self.after(0, lambda r=result: self.txt_target.insert("1.0", r))
                self.after(0, lambda: self.trans_status.configure(text="✅ Hoàn thành!"))
                self._log("✅ Dịch thành công!")
            else:
                self.after(0, lambda: self.trans_status.configure(text="❌ Lỗi!"))
                self._log("❌ Không thể dịch")
                
        except Exception as e:
            self._log(f"❌ Lỗi: {str(e)}")
            self.after(0, lambda: self.trans_status.configure(text="❌ Lỗi!"))
        finally:
            self.after(0, lambda: self.btn_translate.configure(state="normal"))
    
    def _swap_languages(self):
        """Swap source and target languages"""
        source = self.combo_source_lang.get()
        target = self.combo_target_lang.get()
        self.combo_source_lang.set(target)
        self.combo_target_lang.set(source)
        
        # Also swap text if target has content
        source_text = self.txt_source.get("1.0", "end").strip()
        target_text = self.txt_target.get("1.0", "end").strip()
        
        if target_text:
            self.txt_source.delete("1.0", "end")
            self.txt_source.insert("1.0", target_text)
            self.txt_target.delete("1.0", "end")
            if source_text:
                self.txt_target.insert("1.0", source_text)
    
    def _copy_translation(self):
        """Copy translation to clipboard"""
        text = self.txt_target.get("1.0", "end").strip()
        if text:
            self.clipboard_clear()
            self.clipboard_append(text)
            self._log("📋 Đã copy bản dịch")
    
    def _clear_translation(self):
        """Clear translation fields"""
        self.txt_source.delete("1.0", "end")
        self.txt_target.delete("1.0", "end")
    
    # =========================================================================
    # UTILITY METHODS
    # =========================================================================
    
    def _toggle_api_key_visibility(self):
        """Toggle API key visibility"""
        current = self.entry_api_key.cget("show")
        if current == "*":
            self.entry_api_key.configure(show="")
            self.btn_show_key.configure(text="🙈")
        else:
            self.entry_api_key.configure(show="*")
            self.btn_show_key.configure(text="👁")
    
    def _reset_instruction(self, textbox, default_text):
        """Reset instruction to default"""
        textbox.delete("1.0", "end")
        textbox.insert("1.0", default_text)
    
    def _log(self, message: str, end: str = "\n"):
        """Add message to log"""
        self.log_queue.put((message, end))
    
    def _start_log_consumer(self):
        """Start log consumer thread"""
        def consume():
            if self._is_closing:
                return
            try:
                while not self.log_queue.empty():
                    msg, end = self.log_queue.get_nowait()
                    self.txt_log.configure(state="normal")
                    timestamp = time.strftime("%H:%M:%S")
                    if end == "\n":
                        self.txt_log.insert("end", f"[{timestamp}] {msg}\n")
                    else:
                        self.txt_log.insert("end", msg)
                    self.txt_log.see("end")
                    self.txt_log.configure(state="disabled")
            except Empty:
                pass
            except Exception:
                pass
            
            if not self._is_closing:
                self.after(100, consume)
        
        self.after(100, consume)
    
    def _load_settings(self):
        """Load settings from file"""
        settings_path = os.path.join(get_app_dir(), SETTINGS_FILE)
        if os.path.exists(settings_path):
            try:
                with open(settings_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.api_key = data.get("api_key", "")
            except Exception as e:
                print(f"Error loading settings: {e}")
    
    def _save_settings(self):
        """Save settings to file"""
        settings_path = os.path.join(get_app_dir(), SETTINGS_FILE)
        
        # Get API key from entry
        self.api_key = self.entry_api_key.get().strip()
        
        data = {
            "api_key": self.api_key,
        }
        
        try:
            with open(settings_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            messagebox.showinfo("Thành công", "Đã lưu cài đặt!")
            self._log("💾 Đã lưu cài đặt")
        except Exception as e:
            messagebox.showerror("Lỗi", f"Không thể lưu: {e}")
    
    def _on_close(self):
        """Handle window close"""
        self._is_closing = True
        
        # Cleanup persistent session
        if self.persistent_session and self.persistent_session.is_connected:
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(self.persistent_session.disconnect())
                loop.close()
            except Exception as e:
                # Log error but continue with cleanup
                print(f"Warning: Error during session cleanup: {e}")
        
        self.player.cleanup()
        self.after(200, self.destroy)


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    # Set DPI awareness on Windows
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    except:
        pass
    
    # Start application
    app = GeminiLiveDemoApp()
    app.mainloop()