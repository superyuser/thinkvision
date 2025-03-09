import os
import speech_recognition as sr
import threading
from pathlib import Path
from dotenv import load_dotenv
import google.generativeai as genai
from typing import Optional, Dict, List, Any
from tts import talk

load_dotenv()

# Configure Gemini
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
if not GEMINI_API_KEY:
    raise ValueError("GOOGLE_API_KEY not found in environment variables")
genai.configure(api_key=GEMINI_API_KEY)

class VoiceInterface:
    def __init__(self, debug_mode: bool = False):
        self.recognizer = sr.Recognizer()
        self.recording = False
        self.text_detected = None
        self.debug_mode = debug_mode
        self.detected_objects: List[Dict[str, Any]] = []
        self.model = genai.GenerativeModel('gemini-2.0-flash')

    def record_and_interpret_audio(self) -> Optional[str]:
        """Record audio until Enter is pressed and interpret it"""
        self.recording = True
        self.text_detected = None
        audio_chunks = []

        def stop_recording():
            self.recording = False
            if self.text_detected:
                print(f"You said: {self.text_detected}")

        # Use the microphone as source
        with sr.Microphone() as source:
            print("Please speak into the microphone (Press Enter when done)...")
            self.recognizer.adjust_for_ambient_noise(source, duration=1)
            print("Listening...")

            # Start keyboard listener thread
            stop_thread = threading.Thread(target=stop_recording)
            stop_thread.start()

            # Record until Enter is pressed
            while self.recording:
                try:
                    audio_chunk = self.recognizer.listen(source, timeout=2, phrase_time_limit=None)
                    audio_chunks.append(audio_chunk)
                except sr.WaitTimeoutError:
                    continue

            # Combine all audio chunks
            if audio_chunks:
                try:
                    full_text = ""
                    for chunk in audio_chunks:
                        try:
                            text = self.recognizer.recognize_google(chunk)
                            if text:
                                full_text += " " + text
                        except sr.UnknownValueError:
                            continue

                    if full_text:
                        self.text_detected = full_text.strip()
                        return self.text_detected
                    else:
                        talk("Sorry, not sure I understood you. Mind if you repeat it?")
                        return None

                except sr.RequestError as e:
                    print(f"Could not request results from Google Speech Recognition service; {e}")
                    return None
            else:
                talk("Uh, sorry. What did you just say?")
                return None

    def get_response(self, text: str) -> str:
        """Generate a response based on the user's query and detected objects"""
        # Create a context-aware prompt that includes detected objects
        objects_context = ""
        if self.detected_objects:
            objects_list = [f"{obj['label']} ({obj.get('confidence', 0):.2f})" 
                          for obj in self.detected_objects]
            objects_context = "Detected objects: " + ", ".join(objects_list)

        prompt = f"""
        User Query: "{text}"
        {objects_context}

        Rules:
        - Be super casual and friendly, like chatting with a buddy
        - Keep response under 30 words
        - Always end with a short question, unless the user says "bye" or similar
        - Use casual language and contractions
        - Focus on answering questions about the detected objects
        - If no relevant objects are detected, mention that
        """

        response = self.model.generate_content(prompt)
        response_text = response.text.strip()

        print(f"Gemini response: {response_text}")
        return response_text

    def update_detected_objects(self, objects: List[Dict[str, Any]]):
        """Update the list of detected objects from video processing"""
        self.detected_objects = objects

    async def interact(self):
        """Main interaction loop"""
        while True:
            input("Press Enter to start listening...")
            print("\n--- New Conversation ---")

            text = self.record_and_interpret_audio()
            if text and "bye" in text.lower():
                talk("Catch you later! It was fun chatting!")
                break
            if text:
                response = self.get_response(text)
                talk(response)
            else:
                print("No valid text to process. Please try speaking again.")
