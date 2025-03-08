import os
import anthropic
from PIL import Image
import io
import base64
import numpy as np
from typing import List, Dict, Any, Tuple
import cv2
import json
import re
import time

class AnthropicVision:
    def __init__(self):
        self.client = anthropic.Client(api_key=os.getenv("ANTHROPIC_API_KEY"))
        self.cache = {}  # Simple cache for recent object detections
        self.cache_size = 100
        self.frame_count = 0
        self.last_processed_frame = None

    async def process_frame(self, frame: np.ndarray) -> List[Dict[Any, Any]]:
        """Process a frame through Anthropic's Vision-Language Model"""
        try:
            self.frame_count += 1
            
            # Skip every other frame to reduce API calls while maintaining decent tracking
            if self.frame_count % 2 != 0:
                return self.last_processed_frame or []

            # Convert frame to base64
            _, buffer = cv2.imencode('.jpg', frame)
            img_base64 = base64.b64encode(buffer).decode('utf-8')
            
            # Call Anthropic API with structured prompt
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
                            "text": """Analyze this image and provide object detection results in the following JSON format:
{
    "objects": [
        {
            "label": "object name",
            "category": "object category",
            "description": "brief description",
            "confidence": 0.95,
            "bbox": [x1, y1, x2, y2]
        }
    ]
}
For each object, include:
1. Accurate bounding box coordinates [x1, y1, x2, y2] relative to the image dimensions
2. A descriptive label and category
3. A brief but informative description
4. A confidence score between 0 and 1
Focus on main objects and ensure bounding boxes are properly positioned."""
                        }
                    ]
                }]
            )

            # Parse the response and extract object information
            objects = self._parse_response(response.content)
            
            # Update cache and last processed frame
            self._update_cache(objects)
            self.last_processed_frame = objects
            
            return objects

        except Exception as e:
            print(f"Error processing frame: {e}")
            return self.last_processed_frame or []

    def _parse_response(self, response: str) -> List[Dict[Any, Any]]:
        """Parse the Anthropic API response into structured object data"""
        try:
            # Find JSON in the response using regex
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                json_str = json_match.group(0)
                data = json.loads(json_str)
                
                # Validate and clean objects
                objects = []
                for obj in data.get('objects', []):
                    if all(k in obj for k in ['label', 'category', 'description', 'confidence', 'bbox']):
                        # Ensure bbox coordinates are integers
                        obj['bbox'] = [int(coord) for coord in obj['bbox']]
                        # Ensure confidence is float between 0 and 1
                        obj['confidence'] = float(min(max(obj['confidence'], 0), 1))
                        objects.append(obj)
                
                return objects
            
            return []
                
        except Exception as e:
            print(f"Error parsing response: {e}")
            return []

    def _update_cache(self, objects: List[Dict[Any, Any]]):
        """Update the object detection cache"""
        # Simple FIFO cache implementation
        for obj in objects:
            cache_key = f"{obj['label']}_{obj['category']}_{self.frame_count}"
            self.cache[cache_key] = {
                **obj,
                'frame_number': self.frame_count,
                'timestamp': time.time()
            }
            
            # Remove oldest entries if cache is full
            while len(self.cache) > self.cache_size:
                oldest_key = min(self.cache.keys(), key=lambda k: self.cache[k]['timestamp'])
                del self.cache[oldest_key]

    async def search_objects(self, query: str) -> List[Dict[Any, Any]]:
        """Search for objects in recent detections"""
        matching_objects = []
        for obj in self.cache.values():
            if (query.lower() in obj['label'].lower() or 
                query.lower() in obj['category'].lower() or
                query.lower() in obj['description'].lower()):
                matching_objects.append(obj)
        
        # Sort by frame number (most recent first)
        matching_objects.sort(key=lambda x: x['frame_number'], reverse=True)
        return matching_objects

    def get_frame_objects(self, frame_number: int) -> List[Dict[Any, Any]]:
        """Get all objects detected in a specific frame"""
        return [obj for obj in self.cache.values() if obj['frame_number'] == frame_number]
