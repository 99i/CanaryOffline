import os
import subprocess
import re
import asyncio

# Suppress pygame welcome message - must be set before importing pygame
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "hide"
import pygame
from pydub import AudioSegment

async def t2s(text):
    # Remove emojis and special characters
    text = re.sub(r'[*./\\?!\n\t]', '', text).strip()
    # Remove emojis using Unicode ranges
    text = re.sub(r'[^\w\s.,!?;:()"\'-]', '', text).strip()
    
    # Get the directory where this script is located
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    model_path = os.path.join(script_dir, "en", "en_US-kristin-medium.onnx")
    piper_path = os.path.join(script_dir, "piper.exe")
    temp_file = os.path.join(script_dir, "temp_audio.wav")
    
    print(f"[T2S] Model path: {model_path}")
    print(f"[T2S] Piper path: {piper_path}")
    print(f"[T2S] Text to speak: {text[:50]}...")

    # Check if files exist
    if not os.path.exists(model_path):
        print(f"[T2S] Error: Model file not found at {model_path}")
        return
    if not os.path.exists(piper_path):
        print(f"[T2S] Error: Piper executable not found at {piper_path}")
        return

    try:
        process = subprocess.Popen([piper_path, "--model", model_path, "--output_file", temp_file], 
                                  stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        process.communicate(input=text.encode())

        if process.returncode == 0:
            pygame.mixer.init()
            pygame.mixer.music.load(temp_file)
            pygame.mixer.music.play()
            
            while pygame.mixer.music.get_busy():
                await asyncio.sleep(0.1)
            
            pygame.mixer.quit()
            if os.path.exists(temp_file):
                os.remove(temp_file)
        else:
            print(f"[T2S] Error: Piper process failed with return code {process.returncode}")
    except Exception as e:
        print(f"[T2S] Error: {e}")

