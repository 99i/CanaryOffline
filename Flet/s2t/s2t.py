import keyboard
import sounddevice as sd
import numpy as np
import scipy.io.wavfile as wav
from faster_whisper import WhisperModel
import threading
import time
import os

# --- Configuration ---
MODEL_SIZE = "small"  # Options: "tiny", "base", "small", "OVER medium", "OVER large-v1", "OVERlarge-v2"
DEVICE = "cpu"  # "cuda" for GPU, "cpu" for CPU
COMPUTE_TYPE = "int8"  # "float16" or "int8_float16" for GPU, "int8" for CPU
SAMPLERATE = 44100  # Sample rate for recording
FILENAME = "temp_recording.wav"
RECORD_TIME = 50  # seconds (2 minutes)

# --- Recording State ---
_recording = False
_recorded_frames = []
_stream = None
_recording_lock = threading.Lock()
_recording_start_time = None

# --- Initialize Whisper Model (singleton for API use) ---
_model = None
def get_model():
    global _model
    if _model is None:
        try:
            _model = WhisperModel(MODEL_SIZE, device=DEVICE, compute_type=COMPUTE_TYPE)
        except Exception as e:
            print(f"Error initializing Whisper model: {e}")
            _model = None
    return _model

def start_recording():
    """Start recording audio from the microphone (toggle ON)."""
    global _recording, _recorded_frames, _stream, _recording_start_time
    with _recording_lock:
        if _recording:
            print("Already recording.")
            return False  # Prevent duplicate starts
        _recording = True
        _recorded_frames = []
        _recording_start_time = time.time()
    def callback(indata, frames, time_, status):
        if status:
            print(status)
        with _recording_lock:
            if _recording:
                _recorded_frames.append(indata.copy())
    _stream = sd.InputStream(samplerate=SAMPLERATE, channels=1, callback=callback)
    _stream.start()
    print("[Recording started]")
    # Start a timer thread to auto-stop after RECORD_TIME
    def auto_stop():
        time.sleep(RECORD_TIME)
        if is_recording():
            print("[Auto-stopping after RECORD_TIME]")
            # Call stop_recording_and_transcribe and return transcript
            result = stop_recording_and_transcribe(auto=True)
            # If a callback is set, call it with the result
            if _on_transcription:
                _on_transcription(result)
    threading.Thread(target=auto_stop, daemon=True).start()
    return True

def stop_recording_and_transcribe(auto=False):
    """Stop recording and transcribe the audio. Returns transcription string or error."""
    global _recording, _recorded_frames, _stream
    with _recording_lock:
        if not _recording:
            print("Not currently recording.")
            return "[Not recording]"
        _recording = False
    if _stream is not None:
        _stream.stop()
        _stream.close()
        _stream = None
    if not _recorded_frames:
        return "[No audio recorded]"
    audio_data = np.concatenate(_recorded_frames, axis=0)
    wav.write(FILENAME, SAMPLERATE, audio_data)
    model = get_model()
    if model is None:
        return "[Model not initialized]"
    try:
        segments, info = model.transcribe(FILENAME, beam_size=5)
        text = " ".join([seg.text for seg in segments])
        # Delete the temporary recording file after transcription
        if os.path.exists(FILENAME):
            os.remove(FILENAME)
        return text.strip()
    except Exception as e:
        # Delete the temporary recording file even if transcription fails
        if os.path.exists(FILENAME):
            os.remove(FILENAME)
        return f"[Transcription error: {e}]"

def is_recording():
    global _recording
    return _recording

def get_recording_progress():
    """Returns seconds elapsed since recording started, or 0 if not recording."""
    global _recording, _recording_start_time
    if not _recording or _recording_start_time is None:
        return 0
    return min(time.time() - _recording_start_time, RECORD_TIME)

# --- UI callback for auto transcription ---
_on_transcription = None

def set_on_transcription_callback(cb):
    global _on_transcription
    _on_transcription = cb

if __name__ == "__main__":
    try:
        while True:
            cmd = input("Press Enter to start/stop recording, or 'q' to quit: ")
            if cmd.strip().lower() == 'q':
                break
            if not is_recording():
                start_recording()
            else:
                result = stop_recording_and_transcribe()
                print("Result:", result)
    except KeyboardInterrupt:
        print("\nExiting program.")


def start():
    if not is_recording():
        start_recording()
    else:
        result = stop_recording_and_transcribe()
        print("Result:", result)
