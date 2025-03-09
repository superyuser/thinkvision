import asyncio
from voice_interface import VoiceInterface
from tts import talk

# take in both detected_obj_JSON + user query -> Deepgram response

async def test_voice_interface():
    # Initialize voice interface
    voice = VoiceInterface()
    
    # Sample detected objects
    objects = [
        {"label": "coffee cup", "confidence": 0.95},
        {"label": "spoon", "confidence": 0.88},
        {"label": "sugar bowl", "confidence": 0.92},
        {"label": "kettle", "confidence": 0.85}
    ]
    
    # Update voice interface with objects
    voice.update_detected_objects(objects)
    
    # Test some sample queries
    test_queries = [
        "What objects can you see?",
        "Tell me about the coffee cup",
        "Where is the spoon?",
        "Is there any sugar?",
        "bye"
    ]
    
    # Process each query and get responses
    for query in test_queries:
        print(f"\nUser Query: {query}")
        response = voice.get_response(query)
        talk(response)
        if "bye" in query.lower():
            break
        await asyncio.sleep(2)  # Wait between responses

if __name__ == "__main__":
    asyncio.run(test_voice_interface())