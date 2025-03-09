import asyncio
from voice_interface import VoiceInterface, talk

async def test_cooking_assistant():
    # Initialize voice interface
    voice = VoiceInterface()
    
    # Add all detected ingredients as objects
    ingredients = [
        'tomato', 'romaine lettuce hearts', 'pineapple chunks', 'cheese', 'green grapes',
        'hamburger', 'lettuce', 'raspberries', 'ground beef chuck', 'lemons', 'red onion',
        'baby carrots', 'broccoli florets', 'green beans', 'strawberries', 'pickles',
        'mayonnaise', 'olive oil', 'yogurt', 'romaine lettuce', 'spinach', 'pate',
        'avocado', 'hummus', 'lemon', 'apple', 'red bell pepper', 'bell pepper',
        'cucumber', 'orange bell pepper', 'broccoli', 'mango chunks', 'pear',
        'blueberries', 'green apple slices', 'arugula', 'bread', 'sour cream',
        'green peas', 'bagel', 'berries', 'eggs', 'salad', 'grapes', 'butter',
        'mandarin orange segments', 'cucumber slices', 'ginger', 'shredded beets',
        'carrots', 'cooked chicken breast', 'milk', 'honey', 'cereal', 'apples',
        'string beans', 'radishes', 'whole wheat bread', 'salad mix', 'kale',
        'red grapes', 'cooked chicken', 'cooked pasta', 'cooked rice or grains',
        'lime', 'beetroot', 'green onions'
    ]
    
    objects = [{"label": ingredient, "confidence": 0.95} for ingredient in ingredients]
    voice.update_detected_objects(objects)
    
    # Test conversation flow
    test_queries = [
        "Hey, I just got home from a terribly long workday",  # Empty string for initial greeting
        "I'd like to make a fancy dinner",
        "Nah, I was hoping for more comfort foods, something sweet and fatty. I feel stressed!",
        "That sounds good. WIll that leave me with enough food in the fridge for this weekend? I don't have time to grocery shop until next week.",
        "Perfect. I'm ready to start cooking."
    ]
    
    # Process each query and get responses
    for query in test_queries:
        if query:
            print(f"\nUser: {query}")
        response = voice.get_response(query)
        talk(response)
        await asyncio.sleep(3)  # Wait between responses

if __name__ == "__main__":
    asyncio.run(test_cooking_assistant())