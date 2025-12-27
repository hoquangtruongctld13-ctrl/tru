@echo off
chcp 65001 >nul
setlocal EnableDelayedExpansion

echo ====================================================
echo   VN TTS Studio Build Script
echo   Build với PyInstaller + External Heavy Libraries
echo ====================================================
echo.

:: ===========================
:: 1. Kiểm tra Python version
:: ===========================
echo [1/6] Kiểm tra Python version...
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
:: 2. Cài đặt dependencies cơ bản
:: ===========================
echo [2/6] Cài đặt dependencies cơ bản...

python -m pip install --upgrade pip >nul 2>&1

echo       - Cài đặt PyInstaller...
pip install pyinstaller >nul 2>&1

echo       - Cài đặt UI dependencies...
pip install customtkinter requests python-docx google-genai >nul 2>&1

echo       - Cài đặt websockets...
pip install websockets aiohttp >nul 2>&1

echo       ✓ Các dependencies cơ bản đã được cài đặt
echo.

:: ===========================
:: 3. Build với PyInstaller
:: ===========================
echo [3/6] Build executable với PyInstaller...
echo       Đang build... (có thể mất 2-5 phút)

:: Xóa build cũ
if exist "build" rmdir /s /q "build"
if exist "dist\VNTTSStudio" rmdir /s /q "dist\VNTTSStudio"

:: Build
pyinstaller build.spec --clean --noconfirm

if errorlevel 1 (
    echo [ERROR] Build thất bại!
    echo        Xem log ở trên để biết chi tiết.
    pause
    exit /b 1
)
echo       ✓ Build thành công
echo.

:: ===========================
:: 4. Copy heavy libraries
:: ===========================
echo [4/6] Copy heavy libraries...
set "DIST_DIR=dist\VNTTSStudio"
set "LIB_DIR=%DIST_DIR%\_libs"

:: Tạo thư mục libs
if not exist "%LIB_DIR%" mkdir "%LIB_DIR%"

echo       QUAN TRỌNG: Bạn cần copy thủ công các thư viện nặng vào %LIB_DIR%
echo.
echo       Các thư viện cần copy:
echo       - torch (PyTorch)
echo       - torchaudio
echo       - librosa
echo       - neucodec
echo       - phonemizer (+ eSpeak NG)
echo       - onnxruntime
echo       - numpy, scipy
echo.
echo       Hoặc chạy lệnh sau để copy từ site-packages:
echo       python -c "import torch; print(torch.__path__[0])"
echo.

:: ===========================
:: 5. Copy các file bổ sung
:: ===========================
echo [5/6] Copy các file bổ sung...

:: Copy ffmpeg nếu có
if exist "ffmpeg.exe" (
    copy "ffmpeg.exe" "%DIST_DIR%\" >nul 2>&1
    echo       ✓ Đã copy ffmpeg.exe
)

:: Copy ffprobe nếu có
if exist "ffprobe.exe" (
    copy "ffprobe.exe" "%DIST_DIR%\" >nul 2>&1
    echo       ✓ Đã copy ffprobe.exe
)

:: Copy VN TTS samples (nếu chưa có)
if not exist "%DIST_DIR%\vntts\sample" (
    xcopy /E /I /Y "vntts\sample" "%DIST_DIR%\vntts\sample" >nul 2>&1
    echo       ✓ Đã copy VN TTS samples
)

:: Copy VN TTS config
if not exist "%DIST_DIR%\vntts\config.yaml" (
    copy "vntts\config.yaml" "%DIST_DIR%\vntts\" >nul 2>&1
    echo       ✓ Đã copy config.yaml
)

echo.

:: ===========================
:: 6. Hoàn thành
:: ===========================
echo [6/6] Hoàn thành!
echo.
echo ====================================================
echo   BUILD HOÀN TẤT!
echo ====================================================
echo.
echo   Output: %DIST_DIR%\VNTTSStudio.exe
echo.
echo   Các thư mục cần thiết:
echo   - %DIST_DIR%\vntts\sample\   (voice samples)
echo   - %DIST_DIR%\vntts\utils\    (utility modules)
echo   - %DIST_DIR%\edge\           (Edge TTS module)
echo   - %DIST_DIR%\_libs\          (Heavy libraries - CẦN COPY THỦ CÔNG)
echo.
echo   Lưu ý:
echo   - Copy các thư viện nặng vào thư mục _libs
echo   - Copy ffmpeg.exe vào thư mục output nếu cần ghép audio
echo   - Đảm bảo eSpeak NG đã được cài trên máy người dùng (cho VN TTS)
echo.
echo ====================================================

pause
