# Canary Online - AI-Powered Learning Assistant

An intelligent, offline-capable learning assistant that helps students master topics through interactive conversations, voice recognition, and personalized study tools.
## 🎥 Demo Video

[![Watch the demo](https://img.youtube.com/vi/zFBgixQ0b0o/hqdefault.jpg)](https://www.youtube.com/watch?v=zFBgixQ0b0o)


## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- [Ollama](https://ollama.com/)

### Installation

1. **Clone the repository**

```bash
git clone https://github.com/99i/CanaryOffline.git
cd CanaryOnline/Flet
```

2. **Run the setup script**

```bash
# Linux/macOS
chmod +x download_models.sh
./download_models.sh

# Windows
download_models.bat
```

3. **Start the application**

```bash
python main.py
```

## 🎯 Features

- **Voice Interaction**: Speech-to-text and text-to-speech
- **AI-Powered Learning**: Personalized study assistance
- **Interactive Quizzes**: Auto-generated questions with explanations
- **Flashcard System**: Create and study flashcards
- **Progress Tracking**: Monitor study statistics and streaks
- **Offline Capable**: All AI processing done locally

## 🛠️ Technology Stack

- **UI**: Flet (Cross-platform)
- **AI**: Ollama + Gemma 3n
- **Speech**: Faster Whisper + Piper TTS
- **Data**: CSV-based storage

## 📁 Project Structure

```
Flet/
├── main.py              # Main application
├── requirements.txt     # Python dependencies
├── download_models.sh   # Setup script (Linux/macOS)
├── download_models.bat  # Setup script (Windows)
├── s2t/                # Speech-to-text
├── t2s/                # Text-to-speech
├── src/                # Core modules
└── storage/            # Data and assets
```

## 🔧 Development

### Manual Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Download Ollama model
ollama pull gemma3n:e2b-it-q4_K_M

# Run application
python main.py
```

## 📖 Usage

1. **Create a Topic**: Enter a topic name to start studying
2. **Voice Interaction**: Click microphone to speak questions
3. **AI Response**: Get encouraging questions and guidance
4. **Study Tools**: Use quizzes, flashcards, and notes
5. **Track Progress**: Monitor study statistics

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## 📄 License

MIT License - see LICENSE file for details.

## 🙏 Acknowledgments

- **Flet**: Cross-platform UI framework
- **Ollama**: Local AI model serving
- **Faster Whisper**: Speech recognition
- **Piper TTS**: Text-to-speech synthesis
- **Gemma**: Language model by Google

---

**Note**: Requires 8GB+ RAM and 4GB+ disk space for optimal performance.
