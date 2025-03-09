import speech_recognition as sr
from google import genai
from model_characters import get_payload
from tts import talk
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# set up Gemini client
gemini_client = genai.Client(api_key=GEMINI_API_KEY)

def record_and_interpret_audio():
    # Initialize recognizer
    recognizer = sr.Recognizer()

    # Use the microphone as the source of input
    with sr.Microphone() as source:
        print("Please speak into the microphone...")
        
        # Listen for the first phrase and extract it into audio data
        audio_data = recognizer.listen(source)
        
        try:
            # Recognize speech using Google Web Speech API
            text = recognizer.recognize_google(audio_data)
            print(f"You said: {text}")
            return text
            
        except sr.UnknownValueError:
            response = get_response(text="I just said something you don't understand. Ask me to repeat what I just said in a clever, humorous way.")
            print("Could not understand audio. Response:", response)
            return None
        except sr.RequestError as e:
            print(f"Could not request results from Google Speech Recognition service; {e}")
            return None

def get_response(text):
# if mode == "dobby":
#     response = get_payload(text)
#     print(f"Dobby response: {response.json().get('content', '')}")
#     return response.json().get("content", "")
# else:
    response = gemini_client.models.generate_content(model="gemini-2.0-flash", contents=[text])
    print(f"Gemini response: {response}")
    return response.text

def interact():
    while True:
        text = record_and_interpret_audio()
        if ("bye" in text):
            talk("See you later!")
            break
        if text:  # Only get response if we have valid text
            response = get_response(text)
            talk(response)
        else:
            print("No valid text to process. Please try speaking again.")

if __name__ == "__main__":
    interact()