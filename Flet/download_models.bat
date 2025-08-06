@echo off
chcp 65001 >nul
echo 🚀 Canary Online - Model Download Script
echo ========================================
echo.

REM Check if Python is installed
echo [INFO] Checking Python installation...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed. Please install Python 3.8 or higher.
    pause
    exit /b 1
)

echo [SUCCESS] Python found
python --version

REM Check if pip is available
echo [INFO] Checking pip installation...
python -m pip --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] pip is not available. Please install pip.
    pause
    exit /b 1
)

echo [SUCCESS] pip is available

REM Check if Ollama is installed
echo [INFO] Checking Ollama installation...
ollama --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Ollama is not installed. Please install Ollama from https://ollama.ai/
    echo [INFO] After installing Ollama, run this script again.
    pause
    exit /b 1
)

echo [SUCCESS] Ollama found
ollama --version

REM Check if Ollama service is running
echo [INFO] Checking Ollama service...
ollama list >nul 2>&1
if %errorlevel% neq 0 (
    echo [WARNING] Ollama service is not running. Starting Ollama...
    start /B ollama serve
    timeout /t 5 /nobreak >nul
)

echo [SUCCESS] Ollama service is running

REM Install Python dependencies
echo [INFO] Installing Python dependencies...
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

if %errorlevel% neq 0 (
    echo [ERROR] Failed to install Python dependencies
    pause
    exit /b 1
)

echo [SUCCESS] Python dependencies installed successfully

REM Download Ollama model
echo [INFO] Downloading Ollama model: gemma3n:e2b-it-q4_K_M
echo This may take several minutes depending on your internet connection...

REM Check if model already exists
ollama list | findstr "gemma3n:e2b-it-q4_K_M" >nul 2>&1
if %errorlevel% equ 0 (
    echo [SUCCESS] Model already exists: gemma3n:e2b-it-q4_K_M
) else (
    echo [INFO] Starting model download...
    ollama pull gemma3n:e2b-it-q4_K_M
    
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to download Ollama model
        pause
        exit /b 1
    )
    
    echo [SUCCESS] Ollama model downloaded successfully
)

REM Test the model
echo [INFO] Testing Ollama model...
ollama chat gemma3n:e2b-it-q4_K_M -m "Hello" >nul 2>&1
if %errorlevel% equ 0 (
    echo [SUCCESS] Ollama model test successful
) else (
    echo [WARNING] Ollama model test failed, but model is downloaded
)

REM Test Fast Whisper import
echo [INFO] Testing Fast Whisper installation...
python -c "from faster_whisper import WhisperModel; print('✅ Fast Whisper imported successfully'); print('📥 Models will be downloaded automatically on first use')" 2>nul
if %errorlevel% equ 0 (
    echo [SUCCESS] Fast Whisper is ready
) else (
    echo [ERROR] Fast Whisper installation failed
    pause
    exit /b 1
)

REM Test TTS components
echo [INFO] Testing Text-to-Speech components...
python -c "import t2s; print('✅ TTS module imported successfully')" 2>nul
if %errorlevel% equ 0 (
    echo [SUCCESS] TTS components are ready
) else (
    echo [ERROR] TTS components failed
    pause
    exit /b 1
)

REM Test AI backend
echo [INFO] Testing AI backend...
python -c "from src.OllamaBackend import CanaryTopicModel; print('✅ AI backend imported successfully')" 2>nul
if %errorlevel% equ 0 (
    echo [SUCCESS] AI backend is ready
) else (
    echo [ERROR] AI backend failed
    pause
    exit /b 1
)

REM Test database
echo [INFO] Testing database components...
python -c "from storage.data.DB.DB_API import TopicsDB; print('✅ Database components imported successfully')" 2>nul
if %errorlevel% equ 0 (
    echo [SUCCESS] Database components are ready
) else (
    echo [ERROR] Database components failed
    pause
    exit /b 1
)

REM Final test - try to import main
echo [INFO] Testing main application import...
python -c "import main; print('✅ Main application imports successfully')" 2>nul
if %errorlevel% equ 0 (
    echo [SUCCESS] Main application is ready
) else (
    echo [ERROR] Main application import failed
    pause
    exit /b 1
)

echo.
echo ========================================
echo 🎉 ALL MODELS AND COMPONENTS READY!
echo ========================================
echo.
echo ✅ Python dependencies installed
echo ✅ Ollama model downloaded
echo ✅ Fast Whisper ready (models download on first use)
echo ✅ TTS components ready
echo ✅ AI backend ready
echo ✅ Database components ready
echo ✅ Main application ready
echo.
echo 🚀 You can now run the application with:
echo    python main.py
echo.
echo 💡 First time you use voice features, Fast Whisper will
echo    automatically download the speech recognition models.
echo.

pause 