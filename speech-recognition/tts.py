import time
from deepgram.utils import verboselogs
import wave
import datetime
import os
from dotenv import load_dotenv
import re
from deepgram import (
    DeepgramClient,
    SpeakWebSocketEvents,
    SpeakWSOptions,
)

# Load environment variables
load_dotenv()
DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY")

def split_text(text, max_length=500):
    """Split text into chunks at sentence boundaries"""
    # Split into sentences
    sentences = re.split('(?<=[.!?])\s+', text)
    chunks = []
    current_chunk = ""
    
    for sentence in sentences:
        if len(current_chunk) + len(sentence) < max_length:
            current_chunk += " " + sentence if current_chunk else sentence
        else:
            if current_chunk:
                chunks.append(current_chunk.strip())
            current_chunk = sentence
    
    if current_chunk:
        chunks.append(current_chunk.strip())
    
    return chunks

def talk(TTS_TEXT):
    try:
        if not TTS_TEXT or not isinstance(TTS_TEXT, str):
            print("Invalid text input for TTS")
            return

        # Split text into manageable chunks
        text_chunks = split_text(TTS_TEXT)
        
        for i, chunk in enumerate(text_chunks):
            AUDIO_FILE = f"./outputs/{datetime.datetime.now().strftime('%H%M%S')}_{i}.wav"
            
            # Initialize with API key
            deepgram = DeepgramClient(DEEPGRAM_API_KEY)
            dg_connection = deepgram.speak.websocket.v("1")

            def on_binary_data(self, data, **kwargs):
                with open(AUDIO_FILE, "ab") as f:
                    f.write(data)
                    f.flush()

            dg_connection.on(SpeakWebSocketEvents.AudioData, on_binary_data)

            # Ensure outputs directory exists
            os.makedirs("outputs", exist_ok=True)

            # Generate WAV header
            header = wave.open(AUDIO_FILE, "wb")
            header.setnchannels(1)
            header.setsampwidth(2)
            header.setframerate(16000)
            header.close()

            # Connect and generate audio
            options = SpeakWSOptions(
                model="aura-asteria-en",
                encoding="linear16",
                sample_rate=16000,
            )

            print(f"\nGenerating audio part {i+1}/{len(text_chunks)}...")
            if dg_connection.start(options) is False:
                print(f"Failed to start TTS connection for chunk {i+1}")
                continue

            dg_connection.send_text(chunk)
            dg_connection.flush()
            time.sleep(3)  # Reduced wait time per chunk
            dg_connection.finish()
            print(f"Part {i+1} saved to: {AUDIO_FILE}")

    except Exception as e:
        print(f"TTS Error: {e}")