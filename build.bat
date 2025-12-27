@echo off
chcp 65001 >nul
setlocal EnableDelayedExpansion

echo ====================================================
echo   FathTTS Build Script với VieNeu-TTS Support
echo   Build cho CPU (llama-cpp-python + GGUF models)
echo ====================================================
echo.

:: ===========================
:: 1. Kiểm tra Python version
:: ===========================
echo [1/7] Kiểm tra Python version...
python --version 2>&1 | findstr "3.12" >nul
if errorlevel 1 (
    echo [ERROR] Python 3.12 là bắt buộc!
    echo        Vui lòng cài Python 3.12.x từ https://www.python.org/downloads/
    pause
    exit /b 1
)
echo       ✓ Python 3.12 đã được cài đặt
echo.

:: ===========================
:: 2. Kiểm tra eSpeak NG
:: ===========================
echo [2/7] Kiểm tra eSpeak NG...
espeak-ng --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] eSpeak NG chưa được cài đặt hoặc không trong PATH!
    echo        Vui lòng:
    echo        1. Tải từ: https://github.com/espeak-ng/espeak-ng/releases
    echo        2. Cài đặt vào: C:\Program Files\eSpeak NG\
    echo        3. Thêm "C:\Program Files\eSpeak NG" vào PATH
    pause
    exit /b 1
)
echo       ✓ eSpeak NG đã được cài đặt
echo.

:: ===========================
:: 3. Kiểm tra VieNeu-TTS
:: ===========================
echo [3/7] Kiểm tra VieNeu-TTS...
if not exist "VieNeu-TTS" (
    echo [INFO] VieNeu-TTS chưa tồn tại. Đang clone...
    git clone https://github.com/pnnbao97/VieNeu-TTS.git
    if errorlevel 1 (
        echo [ERROR] Không thể clone VieNeu-TTS!
        pause
        exit /b 1
    )
)
echo       ✓ VieNeu-TTS đã sẵn sàng
echo.

:: ===========================
:: 4. Cài đặt dependencies
:: ===========================
echo [4/7] Cài đặt dependencies...

:: Upgrade pip
python -m pip install --upgrade pip >nul 2>&1

:: PyInstaller
echo       - Cài đặt PyInstaller...
pip install pyinstaller >nul 2>&1

:: llama-cpp-python (CPU)
echo       - Cài đặt llama-cpp-python (CPU)...
pip install llama-cpp-python --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cpu >nul 2>&1
if errorlevel 1 (
    echo [WARNING] Không thể cài llama-cpp-python từ wheel. Thử build từ source...
    :: Set CMAKE_ARGS và build trong cùng một command line
    cmd /c "set CMAKE_ARGS=-DLLAMA_BLAS=OFF -DLLAMA_CUBLAS=OFF && pip install llama-cpp-python --no-cache-dir --force-reinstall"
)

:: PyTorch CPU
echo       - Cài đặt PyTorch (CPU)...
pip install torch torchaudio --index-url https://download.pytorch.org/whl/cpu >nul 2>&1

:: Phonemizer
echo       - Cài đặt phonemizer...
pip install phonemizer >nul 2>&1

:: VieNeu-TTS dependencies
echo       - Cài đặt VieNeu-TTS dependencies...
pip install neucodec librosa soundfile onnxruntime >nul 2>&1

:: UI và các thư viện khác
echo       - Cài đặt UI dependencies...
pip install customtkinter requests python-docx google-genai >nul 2>&1

echo       ✓ Tất cả dependencies đã được cài đặt
echo.

:: ===========================
:: 5. Kiểm tra llama-cpp-python
:: ===========================
echo [5/7] Kiểm tra llama-cpp-python...
python -c "from llama_cpp import Llama; print('OK')" >nul 2>&1
if errorlevel 1 (
    echo [ERROR] llama-cpp-python không hoạt động!
    echo        Vui lòng xem BUILD_GUIDE.md để biết cách cài đặt thủ công.
    pause
    exit /b 1
)
echo       ✓ llama-cpp-python hoạt động bình thường
echo.

:: ===========================
:: 6. Build với PyInstaller
:: ===========================
echo [6/7] Build executable với PyInstaller...
echo       Đang build... (có thể mất 5-15 phút)

:: Xóa build cũ
if exist "build" rmdir /s /q "build"
if exist "dist\FathTTS" rmdir /s /q "dist\FathTTS"

:: Build
pyinstaller main_fath.spec --clean --noconfirm

if errorlevel 1 (
    echo [ERROR] Build thất bại!
    echo        Xem log ở trên để biết chi tiết.
    pause
    exit /b 1
)
echo       ✓ Build thành công
echo.

:: ===========================
:: 7. Copy các file bổ sung
:: ===========================
echo [7/7] Copy các file bổ sung...

:: Copy ffmpeg nếu có
if exist "ffmpeg.exe" (
    copy "ffmpeg.exe" "dist\FathTTS\" >nul 2>&1
    echo       ✓ Đã copy ffmpeg.exe
)

:: Copy VieNeu-TTS samples (đảm bảo đầy đủ)
if not exist "dist\FathTTS\VieNeu-TTS\sample" (
    xcopy /E /I /Y "VieNeu-TTS\sample" "dist\FathTTS\VieNeu-TTS\sample" >nul 2>&1
    echo       ✓ Đã copy VieNeu-TTS samples
)

:: Copy config.yaml
if not exist "dist\FathTTS\VieNeu-TTS\config.yaml" (
    copy "VieNeu-TTS\config.yaml" "dist\FathTTS\VieNeu-TTS\" >nul 2>&1
    echo       ✓ Đã copy config.yaml
)

echo.
echo ====================================================
echo   BUILD HOÀN TẤT!
echo ====================================================
echo.
echo   Output: dist\FathTTS\FathTTS.exe
echo.
echo   Các thư mục cần thiết:
echo   - dist\FathTTS\VieNeu-TTS\sample\   (voice samples)
echo   - dist\FathTTS\VieNeu-TTS\utils\    (utility modules)
echo   - dist\FathTTS\edge\                (Edge TTS)
echo.
echo   Lưu ý:
echo   - Model GGUF sẽ tự động download lần đầu chạy
echo   - Đảm bảo eSpeak NG đã được cài trên máy người dùng
echo   - Copy ffmpeg.exe vào thư mục FathTTS nếu cần ghép audio
echo.
echo ====================================================

pause
