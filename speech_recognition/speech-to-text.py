import speech_recognition as sr
from google import genai
from model_characters import get_payload
from tts import talk
from dotenv import load_dotenv
import os
import threading
import keyboard

# Load environment variables
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
gemini_client = genai.Client(api_key=GEMINI_API_KEY)

def record_and_interpret_audio():
    # Initialize recognizer
    recognizer = sr.Recognizer()
    recording = True
    text_detected = None
    audio_chunks = []
    
    def stop_recording():
        nonlocal recording, text_detected
        input("Press Enter to stop recording...")
        recording = False
        if text_detected:
            print(f"You said: {text_detected}")
    
    # Use the microphone as the source of input
    with sr.Microphone() as source:
        print("Please speak into the microphone (Press Enter when done)...")
        # Adjust for ambient noise
        recognizer.adjust_for_ambient_noise(source, duration=1)
        print("Listening...")
        
        # Start the keyboard listener in a separate thread
        stop_thread = threading.Thread(target=stop_recording)
        stop_thread.start()
        
        # Record until Enter is pressed
        while recording:
            try:
                audio_chunk = recognizer.listen(source, timeout=2, phrase_time_limit=None)
                audio_chunks.append(audio_chunk)
            except sr.WaitTimeoutError:
                continue  # Keep listening even if there's silence
        
        # Combine all audio chunks
        if audio_chunks:
            try:
                # Recognize speech using Google Web Speech API
                full_text = ""
                for chunk in audio_chunks:
                    try:
                        text = recognizer.recognize_google(chunk)
                        if text:
                            full_text += " " + text
                    except sr.UnknownValueError:
                        continue  # Skip chunks that couldn't be recognized
                
                if full_text:
                    text_detected = full_text.strip()
                    return text_detected
                else:
                    talk("Sorry, not sure I understood you. Mind if you repeat it?")
                    return None
                    
            except sr.RequestError as e:
                print(f"Could not request results from Google Speech Recognition service; {e}")
                return None
        else:
            talk("Uh, sorry. What did you just say?")
            return None

def get_response(text):
    # Create a casual, conversational prompt
    prompt = f"""
    Respond to: "{text}"
    
    Rules:
    - Be super casual and friendly, like chatting with a buddy
    - Keep response under 30 words
    - Always end with a short question, unless the user says "bye" or "see you" or any of the alike terms to end the conversation
    - Use casual language, contractions, and informal tone
    - If user introduces themselves, respond naturally with their name (e.g., "Hey Alex! Nice to meet you!")
    - Never use placeholders like [username] or [name]
    - Always respond in plain conversational text
    """
    
    response = gemini_client.models.generate_content(
        model="gemini-2.0-flash",
        contents=[prompt]
    )
    
    # Clean up response
    response_text = response.text.strip()
    response_text = response_text.replace('[username]', 'Bubble')  # Fallback cleanup
    response_text = response_text.replace('[name]', 'Bubble')     # Fallback cleanup
    
    print(f"Gemini response: {response_text}")
    return response_text

def interact():
    while True:
        input("Press Enter to start listening...")
        
        text = record_and_interpret_audio()
        if text and "bye" in text.lower():
            talk("Catch you later! It was fun chatting!")
            break
        if text:  # Only get response if we have valid text
            response = get_response(text)
            talk(response)
        else:
            print("No valid text to process. Please try speaking again.")


if __name__ == "__main__":
    interact()