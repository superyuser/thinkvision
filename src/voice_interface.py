import os
from typing import List, Dict, Any, Optional
import asyncio
import speech_recognition as sr
import pyttsx3
import queue
import threading
from datetime import datetime
import time

class VoiceInterface:
    def __init__(self):
        self.engine = pyttsx3.init()
        self.recognizer = sr.Recognizer()
        self.command_queue = queue.Queue()
        self.response_queue = queue.Queue()
        self.is_listening = False
        self.wake_word = "assistant"
        
        # Configure voice properties
        self.engine.setProperty('rate', 150)
        self.engine.setProperty('volume', 0.9)

    async def initialize(self):
        """Initialize voice components and start background threads"""
        try:
            # Start background listening thread
            self.is_listening = True
            threading.Thread(target=self._listen_loop, daemon=True).start()
            
            # Start response processing thread
            threading.Thread(target=self._process_responses, daemon=True).start()
            
        except Exception as e:
            print(f"Error initializing voice interface: {e}")

    def _listen_loop(self):
        """Continuous listening loop for voice commands"""
        while self.is_listening:
            try:
                with sr.Microphone() as source:
                    print("Listening for commands...")
                    self.recognizer.adjust_for_ambient_noise(source)
                    audio = self.recognizer.listen(source, timeout=5, phrase_time_limit=5)
                    
                    try:
                        text = self.recognizer.recognize_google(audio)
                        if self.wake_word in text.lower():
                            # Process command after wake word
                            command = text.lower().split(self.wake_word, 1)[1].strip()
                            self.command_queue.put(command)
                    except sr.UnknownValueError:
                        pass  # Speech not understood
                    except sr.RequestError as e:
                        print(f"Could not request results; {e}")
                        
            except Exception as e:
                print(f"Error in listening loop: {e}")
            
            time.sleep(0.1)

    def _process_responses(self):
        """Process and speak responses from the queue"""
        while self.is_listening:
            try:
                if not self.response_queue.empty():
                    response = self.response_queue.get()
                    self.engine.say(response)
                    self.engine.runAndWait()
            except Exception as e:
                print(f"Error processing response: {e}")
            time.sleep(0.1)

    async def process_command(self, command: str) -> Optional[str]:
        """Process voice commands and generate responses"""
        try:
            # Basic command processing - expand based on needs
            response = None
            
            if "what" in command and "see" in command:
                response = "describe_scene"
            elif "where" in command and "is" in command:
                item = command.split("is")[-1].strip()
                response = f"find_object:{item}"
            elif "help" in command:
                response = "I can help you find objects, describe what I see, or manage your home inventory. Just ask!"
            else:
                response = "I'm not sure how to help with that. Try asking me what I see or where something is."
            
            return response
                
        except Exception as e:
            print(f"Error processing command: {e}")
            return None

    async def generate_response(self, objects: List[Dict[Any, Any]]) -> str:
        """Generate voice response based on detected objects"""
        try:
            if not objects:
                response = "I don't see any objects clearly right now."
            else:
                # Create a natural description of the scene
                object_descriptions = []
                
                for obj in objects[:3]:  # Limit to top 3 objects for brevity
                    desc = f"a {obj['label']}"
                    if obj.get('description'):
                        desc += f" which {obj['description']}"
                    object_descriptions.append(desc)
                
                response = "I can see " + ", ".join(object_descriptions)
            
            # Add response to queue for speaking
            self.response_queue.put(response)
            return response
            
        except Exception as e:
            print(f"Error generating response: {e}")
            return "Sorry, I encountered an error while processing the response."

    async def stop(self):
        """Stop voice interface and cleanup resources"""
        self.is_listening = False
        self.engine.stop()
        # Clear queues
        while not self.command_queue.empty():
            self.command_queue.get()
        while not self.response_queue.empty():
            self.response_queue.get()
