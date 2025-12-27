#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SRT Audio Sync Tool - GUI Version
==================================
Giao diện đồ họa để sync audio với SRT subtitle.

Requirements:
    pip install customtkinter
    FFmpeg phải nằm cùng thư mục với exe hoặc trong system PATH
"""

import os
import sys
import re
import subprocess
import glob
import tempfile
import shutil
import threading
import tkinter as tk
from tkinter import filedialog, messagebox
from dataclasses import dataclass
from typing import List, Optional
from pathlib import Path
from queue import Queue

try:
    import customtkinter as ctk
    ctk.set_appearance_mode("Dark")
    ctk.set_default_color_theme("blue")
except ImportError:
    print("Cần cài đặt customtkinter: pip install customtkinter")
    exit(1)


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
    return "ffmpeg"


def get_default_ffprobe_path(ffmpeg_path: str) -> str:
    """
    Lấy đường dẫn ffprobe dựa trên ffmpeg path.
    """
    if ffmpeg_path == "ffmpeg":
        return "ffprobe"
    
    # Thay thế ffmpeg -> ffprobe trong path
    dir_path = os.path.dirname(ffmpeg_path)
    
    if sys.platform == "win32":
        return os.path.join(dir_path, "ffprobe.exe")
    else:
        return os.path.join(dir_path, "ffprobe")


# Flag để ẩn console window trên Windows
SUBPROCESS_FLAGS = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class SubtitleLine:
    """Lưu thông tin 1 dòng phụ đề"""
    index: int
    start_time: float  # seconds
    end_time: float    # seconds
    duration: float    # seconds
    text: str


@dataclass
class AudioMatch:
    """Lưu thông tin match giữa phụ đề và audio"""
    subtitle: SubtitleLine
    audio_path: str
    audio_duration: float
    needs_speedup: bool
    speed_factor: float
    processed_path: Optional[str] = None


# =============================================================================
# CORE FUNCTIONS
# =============================================================================

def parse_srt_time(time_str: str) -> float:
    """Parse thời gian SRT format thành seconds."""
    time_str = time_str.strip().replace(',', '.')
    match = re.match(r'(\d{1,2}):(\d{2}):(\d{2})\.(\d{3})', time_str)
    if not match:
        match = re.match(r'(\d{1,2}):(\d{2}):(\d{2})', time_str)
        if match:
            h, m, s = map(int, match.groups())
            return h * 3600 + m * 60 + s
        raise ValueError(f"Invalid SRT time format: {time_str}")
    
    h, m, s, ms = match.groups()
    return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000


def parse_srt_file(srt_path: str) -> List[SubtitleLine]:
    """Parse file SRT và trả về danh sách SubtitleLine."""
    subtitles = []
    
    with open(srt_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    pattern = r'(\d+)\s*\n(\d{1,2}:\d{2}:\d{2}[,\.]\d{3})\s*-->\s*(\d{1,2}:\d{2}:\d{2}[,\.]\d{3})\s*\n(.*?)(?=\n\n|\n*$)'
    matches = re.findall(pattern, content, re.DOTALL)
    
    for match in matches:
        index = int(match[0])
        start_time = parse_srt_time(match[1])
        end_time = parse_srt_time(match[2])
        text = match[3].strip()
        duration = end_time - start_time
        
        subtitles.append(SubtitleLine(
            index=index,
            start_time=start_time,
            end_time=end_time,
            duration=duration,
            text=text
        ))
    
    subtitles.sort(key=lambda x: x.index)
    return subtitles


def get_audio_duration(audio_path: str, ffprobe_path: str = "ffprobe") -> float:
    """Lấy duration của file audio bằng ffprobe."""
    cmd = [
        ffprobe_path, "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        audio_path
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True, creationflags=SUBPROCESS_FLAGS)
    return float(result.stdout.strip())


def find_audio_for_subtitle(subtitle: SubtitleLine, audio_dir: str) -> Optional[str]:
    """
    Tìm file audio tương ứng với subtitle index.
    
    Hỗ trợ các format:
    - 0001.wav, 0001.mp3 (4 chữ số - format từ main.py)
    - 0001_*.wav, 0001_*.mp3 (4 chữ số với suffix)
    - 001.wav, 001_*.wav (3 chữ số)
    - 1.wav, 1_*.wav (không padding)
    - Hỗ trợ tất cả định dạng audio phổ biến (wav, mp3, m4a, aac, flac, ogg, wma, opus, webm, amr, 3gp...)
    """
    # Danh sách extension audio được hỗ trợ (cả lowercase và uppercase)
    audio_extensions = {
        '.wav', '.mp3', '.m4a', '.aac', '.flac', '.ogg', 
        '.wma', '.opus', '.webm', '.amr', '.3gp', '.ape',
        '.alac', '.aiff', '.aif', '.au', '.ra', '.mid', '.midi'
    }
    
    # Các format index: 4 chữ số, 3 chữ số, không padding
    index_formats = [
        str(subtitle.index).zfill(4),  # 0001, 0010, 0100
        str(subtitle.index).zfill(3),  # 001, 010, 100
        str(subtitle.index)             # 1, 10, 100
    ]
    
    # Phương pháp 1: Scan thư mục và tìm file match (nhanh và chính xác nhất)
    try:
        all_files = os.listdir(audio_dir)
        
        for index_str in index_formats:
            for filename in all_files:
                filepath = os.path.join(audio_dir, filename)
                
                # Bỏ qua thư mục
                if not os.path.isfile(filepath):
                    continue
                
                # Lấy phần tên file và extension
                name_without_ext, ext = os.path.splitext(filename)
                ext_lower = ext.lower()
                
                # Kiểm tra extension có phải audio không
                if ext_lower not in audio_extensions:
                    continue
                
                # Exact match: "0001" == "0001"
                if name_without_ext == index_str:
                    return filepath
                    
                # Prefix match: "0001_text" starts with "0001_"
                if name_without_ext.startswith(f"{index_str}_"):
                    return filepath
                    
    except Exception:
        pass
    
    # Phương pháp 2: Fallback dùng glob pattern (backup)
    extensions_list = ['wav', 'mp3', 'm4a', 'aac', 'flac', 'ogg', 'wma', 'opus', 'webm', 'amr', '3gp']
    
    for index_str in index_formats:
        # Tìm với glob pattern cho từng extension
        for ext in extensions_list:
            # Pattern 1: 0001.ext (exact match)
            exact_path = os.path.join(audio_dir, f"{index_str}.{ext}")
            if os.path.exists(exact_path):
                return exact_path
            
            # Cũng thử với uppercase extension
            exact_path_upper = os.path.join(audio_dir, f"{index_str}.{ext.upper()}")
            if os.path.exists(exact_path_upper):
                return exact_path_upper
            
            # Pattern 2: 0001_*.ext (with suffix)
            pattern_suffix = os.path.join(audio_dir, f"{index_str}_*.{ext}")
            matches = glob.glob(pattern_suffix)
            if matches:
                return matches[0]
        
        # Pattern 3: Tìm với wildcard extension
        pattern_any = os.path.join(audio_dir, f"{index_str}.*")
        matches = glob.glob(pattern_any)
        for match in matches:
            if os.path.isfile(match):
                ext_lower = os.path.splitext(match)[1].lower()
                if ext_lower in audio_extensions:
                    return match
    
    return None


def process_audio_speed(match: AudioMatch, output_dir: str, ffmpeg_path: str = "ffmpeg") -> str:
    """Xử lý tăng tốc audio nếu cần."""
    basename = os.path.basename(match.audio_path)
    name, ext = os.path.splitext(basename)
    output_path = os.path.join(output_dir, f"{name}_processed.wav")
    
    if not match.needs_speedup:
        cmd = [
            ffmpeg_path, "-y", "-i", match.audio_path,
            "-acodec", "pcm_s16le", "-ar", "24000", "-ac", "1",
            output_path
        ]
    else:
        speed = match.speed_factor
        atempo_filters = []
        
        while speed > 2.0:
            atempo_filters.append("atempo=2.0")
            speed /= 2.0
        
        while speed < 0.5:
            atempo_filters.append("atempo=0.5")
            speed /= 0.5
        
        atempo_filters.append(f"atempo={speed:.6f}")
        filter_str = ",".join(atempo_filters)
        
        cmd = [
            ffmpeg_path, "-y", "-i", match.audio_path,
            "-af", filter_str,
            "-acodec", "pcm_s16le", "-ar", "24000", "-ac", "1",
            output_path
        ]
    
    subprocess.run(cmd, capture_output=True, check=True, creationflags=SUBPROCESS_FLAGS)
    match.processed_path = output_path
    return output_path


def generate_silence(duration: float, output_path: str, ffmpeg_path: str = "ffmpeg") -> str:
    """Tạo file audio im lặng."""
    cmd = [
        ffmpeg_path, "-y",
        "-f", "lavfi", "-i", "anullsrc=r=24000:cl=mono",
        "-t", str(duration),
        "-acodec", "pcm_s16le",
        output_path
    ]
    subprocess.run(cmd, capture_output=True, check=True, creationflags=SUBPROCESS_FLAGS)
    return output_path


def create_timeline(matches: List[AudioMatch], output_path: str, temp_dir: str,
                   ffmpeg_path: str = "ffmpeg") -> str:
    """Tạo timeline hoàn chỉnh với audio và silence gaps."""
    matches.sort(key=lambda x: x.subtitle.start_time)
    
    segment_files = []
    current_time = 0.0
    
    for i, match in enumerate(matches):
        gap_before = match.subtitle.start_time - current_time
        
        if gap_before > 0.01:
            silence_path = os.path.join(temp_dir, f"silence_{i:04d}_before.wav")
            generate_silence(gap_before, silence_path, ffmpeg_path)
            segment_files.append(silence_path)
        
        if match.processed_path:
            segment_files.append(match.processed_path)
        
        current_time = match.subtitle.end_time
    
    list_path = os.path.join(temp_dir, "concat_list.txt")
    with open(list_path, 'w', encoding='utf-8') as f:
        for seg_file in segment_files:
            escaped_path = seg_file.replace("'", "'\\''")
            f.write(f"file '{escaped_path}'\n")
    
    cmd = [
        ffmpeg_path, "-y",
        "-f", "concat", "-safe", "0", "-i", list_path,
        "-acodec", "pcm_s16le", "-ar", "24000", "-ac", "1",
        output_path
    ]
    
    subprocess.run(cmd, capture_output=True, check=True, creationflags=SUBPROCESS_FLAGS)
    return output_path


# =============================================================================
# GUI APPLICATION
# =============================================================================

class SRTAudioSyncApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        self.title("🎬 SRT Audio Sync Tool")
        self.geometry("900x700")
        self.minsize(800, 600)
        
        self.log_queue = Queue()
        self.is_processing = False
        self._is_closing = False
        
        self._create_gui()
        self._start_log_consumer()
        
        self.protocol("WM_DELETE_WINDOW", self._on_close)
    
    def _create_gui(self):
        # Main container
        main_frame = ctk.CTkFrame(self)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Title
        title_label = ctk.CTkLabel(
            main_frame, 
            text="🎬 SRT Audio Sync Tool",
            font=ctk.CTkFont(size=24, weight="bold")
        )
        title_label.pack(pady=(10, 20))
        
        # Input Section
        input_frame = ctk.CTkFrame(main_frame)
        input_frame.pack(fill="x", padx=10, pady=5)
        
        # SRT File
        srt_frame = ctk.CTkFrame(input_frame, fg_color="transparent")
        srt_frame.pack(fill="x", pady=5)
        
        ctk.CTkLabel(srt_frame, text="📄 File SRT:", width=100, anchor="w").pack(side="left", padx=5)
        self.entry_srt = ctk.CTkEntry(srt_frame, placeholder_text="Chọn file phụ đề .srt")
        self.entry_srt.pack(side="left", fill="x", expand=True, padx=5)
        ctk.CTkButton(srt_frame, text="Browse", width=80, command=self._browse_srt).pack(side="right", padx=5)
        
        # Audio Directory
        audio_frame = ctk.CTkFrame(input_frame, fg_color="transparent")
        audio_frame.pack(fill="x", pady=5)
        
        ctk.CTkLabel(audio_frame, text="🎵 Audio Dir:", width=100, anchor="w").pack(side="left", padx=5)
        self.entry_audio = ctk.CTkEntry(audio_frame, placeholder_text="Chọn thư mục chứa audio files")
        self.entry_audio.pack(side="left", fill="x", expand=True, padx=5)
        ctk.CTkButton(audio_frame, text="Browse", width=80, command=self._browse_audio).pack(side="right", padx=5)
        
        # Output File
        output_frame = ctk.CTkFrame(input_frame, fg_color="transparent")
        output_frame.pack(fill="x", pady=5)
        
        ctk.CTkLabel(output_frame, text="💾 Output:", width=100, anchor="w").pack(side="left", padx=5)
        self.entry_output = ctk.CTkEntry(output_frame, placeholder_text="output_synced.wav")
        self.entry_output.pack(side="left", fill="x", expand=True, padx=5)
        ctk.CTkButton(output_frame, text="Save As", width=80, command=self._browse_output).pack(side="right", padx=5)
        
        # FFmpeg Path
        ffmpeg_frame = ctk.CTkFrame(input_frame, fg_color="transparent")
        ffmpeg_frame.pack(fill="x", pady=5)
        
        ctk.CTkLabel(ffmpeg_frame, text="🔧 FFmpeg:", width=100, anchor="w").pack(side="left", padx=5)
        self.entry_ffmpeg = ctk.CTkEntry(ffmpeg_frame)
        self.entry_ffmpeg.insert(0, get_default_ffmpeg_path())
        self.entry_ffmpeg.pack(side="left", fill="x", expand=True, padx=5)
        ctk.CTkButton(ffmpeg_frame, text="Test", width=50, command=self._test_ffmpeg).pack(side="right", padx=2)
        ctk.CTkButton(ffmpeg_frame, text="Browse", width=80, command=self._browse_ffmpeg).pack(side="right", padx=2)
        
        # Hiển thị thư mục app
        app_dir_frame = ctk.CTkFrame(input_frame, fg_color="transparent")
        app_dir_frame.pack(fill="x", pady=2)
        
        app_dir_label = ctk.CTkLabel(
            app_dir_frame, 
            text=f"📁 App Directory: {get_app_dir()}",
            font=ctk.CTkFont(size=11),
            text_color="gray"
        )
        app_dir_label.pack(anchor="w", padx=5)
        
        # Options
        options_frame = ctk.CTkFrame(main_frame)
        options_frame.pack(fill="x", padx=10, pady=10)
        
        ctk.CTkLabel(options_frame, text="⚙️ Tùy chọn", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=10, pady=5)
        
        opts_inner = ctk.CTkFrame(options_frame, fg_color="transparent")
        opts_inner.pack(fill="x", padx=10, pady=5)
        
        self.var_keep_temp = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(opts_inner, text="Giữ temp files (debug)", variable=self.var_keep_temp).pack(side="left", padx=10)
        
        ctk.CTkLabel(opts_inner, text="Sample Rate:").pack(side="left", padx=(20, 5))
        self.combo_sample_rate = ctk.CTkComboBox(opts_inner, values=["24000", "44100", "48000"], width=100)
        self.combo_sample_rate.set("24000")
        self.combo_sample_rate.pack(side="left", padx=5)
        
        # Progress
        progress_frame = ctk.CTkFrame(main_frame)
        progress_frame.pack(fill="x", padx=10, pady=5)
        
        self.label_status = ctk.CTkLabel(progress_frame, text="Sẵn sàng")
        self.label_status.pack(anchor="w", padx=10, pady=5)
        
        self.progress_bar = ctk.CTkProgressBar(progress_frame)
        self.progress_bar.pack(fill="x", padx=10, pady=5)
        self.progress_bar.set(0)
        
        # Buttons
        btn_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        btn_frame.pack(fill="x", padx=10, pady=10)
        
        self.btn_start = ctk.CTkButton(
            btn_frame, 
            text="▶️ Bắt đầu Sync", 
            font=ctk.CTkFont(size=16, weight="bold"),
            height=45,
            command=self._start_sync
        )
        self.btn_start.pack(side="left", expand=True, fill="x", padx=5)
        
        self.btn_stop = ctk.CTkButton(
            btn_frame,
            text="⏹️ Dừng",
            height=45,
            fg_color="#FF5555",
            hover_color="#FF3333",
            state="disabled",
            command=self._stop_sync
        )
        self.btn_stop.pack(side="right", padx=5)
        
        # Log Area
        log_frame = ctk.CTkFrame(main_frame)
        log_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        ctk.CTkLabel(log_frame, text="📋 Log", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=10, pady=5)
        
        self.txt_log = ctk.CTkTextbox(log_frame, font=ctk.CTkFont(family="Consolas", size=11))
        self.txt_log.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Info
        info_label = ctk.CTkLabel(
            main_frame,
            text="💡 Audio files format: 0001.wav, 0001.mp3, 0001_ten.wav, ... (4 chữ số = index trong SRT)",
            font=ctk.CTkFont(size=11),
            text_color="gray"
        )
        info_label.pack(pady=5)
    
    def _browse_srt(self):
        path = filedialog.askopenfilename(
            title="Chọn file SRT",
            filetypes=[("SRT files", "*.srt"), ("All files", "*.*")]
        )
        if path:
            self.entry_srt.delete(0, "end")
            self.entry_srt.insert(0, path)
    
    def _browse_audio(self):
        path = filedialog.askdirectory(title="Chọn thư mục chứa audio")
        if path:
            self.entry_audio.delete(0, "end")
            self.entry_audio.insert(0, path)
    
    def _browse_output(self):
        path = filedialog.asksaveasfilename(
            title="Lưu file output",
            defaultextension=".wav",
            filetypes=[("WAV files", "*.wav"), ("MP3 files", "*.mp3"), ("All files", "*.*")]
        )
        if path:
            self.entry_output.delete(0, "end")
            self.entry_output.insert(0, path)
    
    def _browse_ffmpeg(self):
        path = filedialog.askopenfilename(
            title="Chọn FFmpeg executable",
            filetypes=[("Executable", "*.exe"), ("All files", "*.*")]
        )
        if path:
            self.entry_ffmpeg.delete(0, "end")
            self.entry_ffmpeg.insert(0, path)
    
    def _test_ffmpeg(self):
        """Kiểm tra ffmpeg có hoạt động không"""
        ffmpeg_path = self.entry_ffmpeg.get().strip()
        
        try:
            result = subprocess.run(
                [ffmpeg_path, "-version"],
                capture_output=True,
                text=True,
                timeout=10,
                creationflags=SUBPROCESS_FLAGS
            )
            
            if result.returncode == 0:
                # Lấy version từ output
                version_line = result.stdout.split('\n')[0] if result.stdout else "Unknown version"
                messagebox.showinfo(
                    "✅ FFmpeg OK",
                    f"FFmpeg hoạt động bình thường!\n\n{version_line}\n\nPath: {ffmpeg_path}"
                )
            else:
                messagebox.showerror(
                    "❌ FFmpeg Error",
                    f"FFmpeg không hoạt động!\n\nPath: {ffmpeg_path}\n\nError: {result.stderr}"
                )
        except FileNotFoundError:
            messagebox.showerror(
                "❌ Không tìm thấy FFmpeg",
                f"Không tìm thấy FFmpeg tại:\n{ffmpeg_path}\n\n"
                f"Vui lòng đặt ffmpeg.exe vào thư mục:\n{get_app_dir()}\n\n"
                f"Hoặc chọn đường dẫn khác."
            )
        except subprocess.TimeoutExpired:
            messagebox.showerror("❌ Timeout", "FFmpeg không phản hồi!")
        except Exception as e:
            messagebox.showerror("❌ Lỗi", f"Lỗi khi kiểm tra FFmpeg:\n{e}")
    
    def _log(self, message: str, level: str = "INFO"):
        self.log_queue.put((message, level))
    
    def _start_log_consumer(self):
        def consume():
            if self._is_closing:
                return
            try:
                while not self.log_queue.empty():
                    msg, level = self.log_queue.get()
                    
                    prefix = ""
                    if level == "ERROR":
                        prefix = "❌ "
                    elif level == "SUCCESS":
                        prefix = "✅ "
                    elif level == "WARNING":
                        prefix = "⚠️ "
                    elif level == "INFO":
                        prefix = "ℹ️ "
                    
                    self.txt_log.insert("end", f"{prefix}{msg}\n")
                    self.txt_log.see("end")
                
                if not self._is_closing:
                    self.after(100, consume)
            except Exception:
                pass
        
        self.after(100, consume)
    
    def _start_sync(self):
        # Validate inputs
        srt_path = self.entry_srt.get().strip()
        audio_dir = self.entry_audio.get().strip()
        output_path = self.entry_output.get().strip()
        ffmpeg_path = self.entry_ffmpeg.get().strip()
        
        if not srt_path:
            messagebox.showerror("Lỗi", "Vui lòng chọn file SRT!")
            return
        
        if not audio_dir:
            messagebox.showerror("Lỗi", "Vui lòng chọn thư mục audio!")
            return
        
        if not output_path:
            output_path = os.path.join(audio_dir, "output_synced.wav")
            self.entry_output.delete(0, "end")
            self.entry_output.insert(0, output_path)
        
        if not os.path.exists(srt_path):
            messagebox.showerror("Lỗi", f"Không tìm thấy file SRT: {srt_path}")
            return
        
        if not os.path.isdir(audio_dir):
            messagebox.showerror("Lỗi", f"Không tìm thấy thư mục audio: {audio_dir}")
            return
        
        # Start processing
        self.is_processing = True
        self.btn_start.configure(state="disabled")
        self.btn_stop.configure(state="normal")
        self.progress_bar.set(0)
        self.txt_log.delete("1.0", "end")
        
        # Run in thread
        thread = threading.Thread(
            target=self._sync_thread,
            args=(srt_path, audio_dir, output_path, ffmpeg_path),
            daemon=True
        )
        thread.start()
    
    def _sync_thread(self, srt_path, audio_dir, output_path, ffmpeg_path):
        try:
            self._log("=" * 50)
            self._log("🎬 SRT Audio Sync Tool - Bắt đầu", "INFO")
            self._log("=" * 50)
            self._log(f"📄 SRT: {srt_path}")
            self._log(f"🎵 Audio: {audio_dir}")
            self._log(f"💾 Output: {output_path}")
            
            # Parse SRT
            self._update_status("Đang đọc file SRT...")
            subtitles = parse_srt_file(srt_path)
            self._log(f"📄 Đã đọc {len(subtitles)} dòng phụ đề")
            
            if not subtitles:
                raise ValueError("Không tìm thấy subtitle trong file SRT")
            
            self._update_progress(0.1)
            
            # Determine ffprobe path
            ffprobe_path = get_default_ffprobe_path(ffmpeg_path)
            
            # Match audio
            self._update_status("Đang match audio files...")
            matches = []
            
            for i, sub in enumerate(subtitles):
                if not self.is_processing:
                    self._log("Đã dừng bởi người dùng", "WARNING")
                    return
                
                audio_path = find_audio_for_subtitle(sub, audio_dir)
                
                if audio_path is None:
                    self._log(f"⚠️ Không tìm thấy audio cho index {sub.index}", "WARNING")
                    continue
                
                try:
                    audio_duration = get_audio_duration(audio_path, ffprobe_path)
                except Exception as e:
                    self._log(f"❌ Lỗi khi đọc {audio_path}: {e}", "ERROR")
                    continue
                
                needs_speedup = audio_duration > sub.duration
                speed_factor = audio_duration / sub.duration if needs_speedup else 1.0
                
                matches.append(AudioMatch(
                    subtitle=sub,
                    audio_path=audio_path,
                    audio_duration=audio_duration,
                    needs_speedup=needs_speedup,
                    speed_factor=speed_factor
                ))
                
                status = "🚀 Tăng tốc" if needs_speedup else "✅ OK"
                self._log(f"[{sub.index:04d}] {status} | Sub: {sub.duration:.2f}s | Audio: {audio_duration:.2f}s | Speed: {speed_factor:.2f}x")
            
            self._update_progress(0.3)
            
            if not matches:
                raise ValueError("Không match được audio nào!")
            
            self._log(f"\n✅ Match: {len(matches)}/{len(subtitles)} files")
            
            # Create temp directory
            keep_temp = self.var_keep_temp.get()
            temp_dir = tempfile.mkdtemp(prefix="srt_sync_")
            self._log(f"📁 Temp: {temp_dir}")
            
            try:
                # Process audio speed
                self._update_status("Đang xử lý tốc độ audio...")
                total = len(matches)
                
                for i, match in enumerate(matches):
                    if not self.is_processing:
                        self._log("Đã dừng bởi người dùng", "WARNING")
                        return
                    
                    self._update_status(f"Xử lý audio {i+1}/{total}...")
                    process_audio_speed(match, temp_dir, ffmpeg_path)
                    self._update_progress(0.3 + (0.5 * (i + 1) / total))
                
                # Create timeline
                self._update_status("Đang tạo timeline...")
                self._log("\n🎼 Đang ghép timeline...")
                
                create_timeline(matches, output_path, temp_dir, ffmpeg_path)
                
                self._update_progress(1.0)
                
                # Get output duration
                try:
                    final_duration = get_audio_duration(output_path, ffprobe_path)
                    self._log(f"\n📊 Tổng thời lượng: {final_duration:.2f}s ({final_duration/60:.1f} phút)")
                except:
                    pass
                
                self._log(f"\n💾 Đã lưu: {output_path}", "SUCCESS")
                self._log("\n🎉 HOÀN THÀNH!", "SUCCESS")
                self._update_status("✅ Hoàn thành!")
                
                # Show success message
                self.after(0, lambda: messagebox.showinfo(
                    "Thành công", 
                    f"Đã sync thành công!\n\nOutput: {output_path}"
                ))
                
            finally:
                if not keep_temp:
                    shutil.rmtree(temp_dir, ignore_errors=True)
                    self._log("🧹 Đã xóa temp files")
                else:
                    self._log(f"📁 Giữ temp files: {temp_dir}")
        
        except Exception as e:
            self._log(f"\n❌ Lỗi: {e}", "ERROR")
            self._update_status(f"❌ Lỗi: {e}")
            self.after(0, lambda: messagebox.showerror("Lỗi", str(e)))
        
        finally:
            self.is_processing = False
            self.after(0, lambda: self.btn_start.configure(state="normal"))
            self.after(0, lambda: self.btn_stop.configure(state="disabled"))
    
    def _stop_sync(self):
        self.is_processing = False
        self._log("🛑 Đang dừng...", "WARNING")
    
    def _update_status(self, text):
        self.after(0, lambda: self.label_status.configure(text=text))
    
    def _update_progress(self, value):
        self.after(0, lambda: self.progress_bar.set(value))
    
    def _on_close(self):
        self._is_closing = True
        self.is_processing = False
        self.after(200, self.destroy)


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    except:
        pass
    
    app = SRTAudioSyncApp()
    app.mainloop()