import base64
import cv2
import numpy as np
from typing import List, Dict, Any
import json
import re
import time
import os
from anthropic import Anthropic
from dotenv import load_dotenv

class AnthropicVision:
    def __init__(self):
        """Initialize Anthropic Vision API"""
        try:
            # Load environment variables
            load_dotenv()
            api_key = os.getenv('ANTHROPIC_API_KEY')
            if not api_key:
                raise ValueError("ANTHROPIC_API_KEY not found in environment variables")
            
            # Initialize Anthropic client
            self.client = Anthropic(api_key=api_key)
            print("Anthropic Vision API initialized successfully")
        except Exception as e:
            print(f"Error initializing Anthropic Vision: {e}")
            raise

    async def process_frame(self, frame: np.ndarray) -> List[Dict[Any, Any]]:
        """Process a frame through Anthropic's Vision-Language Model"""
        try:
            # Convert frame to RGB for better analysis
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # Convert frame to base64
            _, buffer = cv2.imencode('.jpg', frame_rgb)
            img_base64 = base64.b64encode(buffer).decode('utf-8')
            
            # Call Anthropic API with improved prompt
            response = self.client.messages.create(
                model="claude-3-opus-20240229",
                max_tokens=1000,
                messages=[{
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/jpeg",
                                "data": img_base64
                            }
                        },
                        {
                            "type": "text",
                            "text": """Analyze this image and identify ALL visible ingredients, foods, or cooking items.
For each item found, provide:
- Name of the item
- Its state or condition
- Approximate quantity if visible
- Location description
- Your confidence level (0-1)

Format your response EXACTLY as this JSON:
{
    "objects": [
        {
            "label": "tomato",
            "category": "ingredient",
            "description": "2 ripe whole tomatoes on cutting board",
            "confidence": 0.95,
            "bbox": [100, 100, 200, 200]
        }
    ]
}

IMPORTANT:
- Return ONLY the JSON, no other text
- Include ANY food-related items
- Include items even with lower confidence (0.3+)
- Always use the exact field names shown above
- If no items found, return empty objects array"""
                        }
                    ]
                }]
            )
            
            # Print full Claude response for debugging
            print("=== CLAUDE RESPONSE START ===")
            print(response.content)
            print("=== CLAUDE RESPONSE END ===")
            
            # Parse the response
            objects = self._parse_response(response.content[0].text)
            
            # Print parsed objects
            print("=== PARSED OBJECTS START ===")
            print(json.dumps(objects, indent=2))
            print("=== PARSED OBJECTS END ===")
            
            return objects

        except Exception as e:
            print(f"Error in process_frame: {e}")
            return []

    def _parse_response(self, response: str) -> List[Dict[Any, Any]]:
        """Parse the Anthropic API response into structured object data"""
        try:
            # Find JSON in the response using regex
            json_match = re.search(r'\{[\s\S]*\}', response)
            if not json_match:
                print("No JSON found in response")
                return []
                
            json_str = json_match.group(0)
            try:
                data = json.loads(json_str)
            except json.JSONDecodeError as e:
                print(f"Failed to parse JSON: {e}")
                return []
            
            if not isinstance(data, dict) or 'objects' not in data:
                print("Invalid JSON structure")
                return []
                
            objects = []
            for obj in data['objects']:
                try:
                    # Ensure all required fields are present
                    required_fields = ['label', 'category', 'description', 'confidence', 'bbox']
                    if not all(field in obj for field in required_fields):
                        print(f"Missing required fields in object: {obj}")
                        continue
                    
                    # Clean and validate the object data
                    cleaned_obj = {
                        'label': str(obj['label']).strip().lower(),
                        'category': 'ingredient',  # Always set to ingredient
                        'description': str(obj['description']).strip(),
                        'confidence': float(min(max(float(obj.get('confidence', 0)), 0), 1)),
                        'bbox': [int(coord) for coord in obj['bbox']]
                    }
                    
                    objects.append(cleaned_obj)
                    print(f"Successfully processed object: {cleaned_obj}")
                except (ValueError, TypeError, KeyError) as e:
                    print(f"Error processing object: {e}")
                    continue
            
            print(f"Total valid objects found: {len(objects)}")
            return objects
            
        except Exception as e:
            print(f"Error parsing response: {e}")
            return []
