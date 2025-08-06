#!/bin/bash

echo "🚀 Canary Online - Model Download Script"
echo "========================================"
echo

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if Python is installed
print_status "Checking Python installation..."
if command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
elif command -v python &> /dev/null; then
    PYTHON_CMD="python"
else
    print_error "Python is not installed. Please install Python 3.8 or higher."
    exit 1
fi

print_success "Python found: $($PYTHON_CMD --version)"

# Check if pip is available
print_status "Checking pip installation..."
if ! $PYTHON_CMD -m pip --version &> /dev/null; then
    print_error "pip is not available. Please install pip."
    exit 1
fi

print_success "pip is available"

# Check if Ollama is installed
print_status "Checking Ollama installation..."
if ! command -v ollama &> /dev/null; then
    print_error "Ollama is not installed. Please install Ollama from https://ollama.ai/"
    print_status "After installing Ollama, run this script again."
    exit 1
fi

print_success "Ollama found: $(ollama --version)"

# Check if Ollama service is running
print_status "Checking Ollama service..."
if ! ollama list &> /dev/null; then
    print_warning "Ollama service is not running. Starting Ollama..."
    ollama serve &
    sleep 5
fi

print_success "Ollama service is running"

# Install Python dependencies
print_status "Installing Python dependencies..."
$PYTHON_CMD -m pip install --upgrade pip
$PYTHON_CMD -m pip install -r requirements.txt

if [ $? -eq 0 ]; then
    print_success "Python dependencies installed successfully"
else
    print_error "Failed to install Python dependencies"
    exit 1
fi

# Download Ollama model
print_status "Downloading Ollama model: gemma3n:e2b-it-q4_K_M"
echo "This may take several minutes depending on your internet connection..."

# Check if model already exists
if ollama list | grep -q "gemma3n:e2b-it-q4_K_M"; then
    print_success "Model already exists: gemma3n:e2b-it-q4_K_M"
else
    print_status "Starting model download..."
    ollama pull gemma3n:e2b-it-q4_K_M
    
    if [ $? -eq 0 ]; then
        print_success "Ollama model downloaded successfully"
    else
        print_error "Failed to download Ollama model"
        exit 1
    fi
fi

# Test the model
print_status "Testing Ollama model..."
TEST_RESPONSE=$(ollama chat gemma3n:e2b-it-q4_K_M -m "Hello" 2>/dev/null | head -n 1)

if [ ! -z "$TEST_RESPONSE" ]; then
    print_success "Ollama model test successful"
else
    print_warning "Ollama model test failed, but model is downloaded"
fi

# Download Fast Whisper models (this happens automatically when first used)
print_status "Setting up Fast Whisper models..."
print_status "Fast Whisper models will be downloaded automatically on first use"
print_status "This includes speech recognition models (tiny/small/base)"

# Test Fast Whisper import
print_status "Testing Fast Whisper installation..."
$PYTHON_CMD -c "
try:
    from faster_whisper import WhisperModel
    print('✅ Fast Whisper imported successfully')
    print('📥 Models will be downloaded automatically on first use')
except ImportError as e:
    print('❌ Fast Whisper import failed:', e)
    exit(1)
"

if [ $? -eq 0 ]; then
    print_success "Fast Whisper is ready"
else
    print_error "Fast Whisper installation failed"
    exit 1
fi

# Test TTS components
print_status "Testing Text-to-Speech components..."
$PYTHON_CMD -c "
try:
    import t2s
    print('✅ TTS module imported successfully')
except ImportError as e:
    print('❌ TTS import failed:', e)
    exit(1)
"

if [ $? -eq 0 ]; then
    print_success "TTS components are ready"
else
    print_error "TTS components failed"
    exit 1
fi

# Test AI backend
print_status "Testing AI backend..."
$PYTHON_CMD -c "
try:
    from src.OllamaBackend import CanaryTopicModel
    print('✅ AI backend imported successfully')
except ImportError as e:
    print('❌ AI backend import failed:', e)
    exit(1)
"

if [ $? -eq 0 ]; then
    print_success "AI backend is ready"
else
    print_error "AI backend failed"
    exit 1
fi

# Test database
print_status "Testing database components..."
$PYTHON_CMD -c "
try:
    from storage.data.DB.DB_API import TopicsDB
    print('✅ Database components imported successfully')
except ImportError as e:
    print('❌ Database import failed:', e)
    exit(1)
"

if [ $? -eq 0 ]; then
    print_success "Database components are ready"
else
    print_error "Database components failed"
    exit 1
fi

# Final test - try to import main
print_status "Testing main application import..."
$PYTHON_CMD -c "
try:
    import main
    print('✅ Main application imports successfully')
except ImportError as e:
    print('❌ Main application import failed:', e)
    exit(1)
"

if [ $? -eq 0 ]; then
    print_success "Main application is ready"
else
    print_error "Main application import failed"
    exit 1
fi

echo
echo "========================================"
echo "🎉 ALL MODELS AND COMPONENTS READY!"
echo "========================================"
echo
echo "✅ Python dependencies installed"
echo "✅ Ollama model downloaded"
echo "✅ Fast Whisper ready (models download on first use)"
echo "✅ TTS components ready"
echo "✅ AI backend ready"
echo "✅ Database components ready"
echo "✅ Main application ready"
echo
echo "🚀 You can now run the application with:"
echo "   python main.py"
echo
echo "💡 First time you use voice features, Fast Whisper will"
echo "   automatically download the speech recognition models."
echo 