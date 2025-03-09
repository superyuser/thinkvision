import os
import cv2
import numpy as np
import asyncio
from pathlib import Path
import tempfile
import json
from typing import Dict, List, Any, Generator, Tuple, AsyncGenerator
import time
import base64
import PIL  # Import the entire PIL package
from src.gemini_vision import GeminiVision

class VideoProcessor:
    def __init__(self, debug_mode: bool = True):
        """Initialize video processor"""
        self.video = None
        self.frame_count = 0
        self.fps = 0
        self.duration = 0
        self.vision_processor = GeminiVision()
        self.all_ingredients = set()
        self.frame_ingredients = []
        self.debug_mode = debug_mode

    async def load_video(self, video_path: str) -> bool:
        """Load video file and extract metadata"""
        try:
            # Check if file exists
            if not os.path.exists(video_path):
                print(f"Video file not found: {video_path}")
                return False
                
            # Open video file
            self.video = cv2.VideoCapture(video_path)
            if not self.video.isOpened():
                print(f"Failed to open video: {video_path}")
                return False
                
            # Get video metadata
            self.frame_count = int(self.video.get(cv2.CAP_PROP_FRAME_COUNT))
            self.fps = self.video.get(cv2.CAP_PROP_FPS)
            self.duration = self.frame_count / self.fps if self.fps > 0 else 0
            
            print(f"Video loaded: {video_path}")
            print(f"Frames: {self.frame_count}, FPS: {self.fps}, Duration: {self.duration:.2f}s")
            
            return True
            
        except Exception as e:
            print(f"Error loading video: {e}")
            return False

    async def process_video(self, video_path: str, sample_rate=10) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Process video and extract ingredients
        
        Args:
            video_path: Path to the video file
            sample_rate: Process every Nth frame (default: 10)
            
        Yields:
            Dictionary with frame path and detected ingredients
        """
        try:
            # Load the video first
            success = await self.load_video(video_path)
            if not success:
                raise ValueError(f"Failed to load video: {video_path}")
            
            # Create output directory for frames
            output_dir = Path("static/frames")
            output_dir.mkdir(exist_ok=True, parents=True)
            
            # Reset state
            self.all_ingredients = set()
            self.frame_ingredients = []
            
            # Process frames
            frame_index = 0
            processed_count = 0
            
            while True:
                # Read frame
                ret, frame = self.video.read()
                if not ret:
                    break
                    
                # Process every Nth frame
                if frame_index % sample_rate == 0:
                    # Save frame to disk
                    frame_filename = f"frame_{processed_count:04d}.jpg"
                    frame_path = output_dir / frame_filename
                    cv2.imwrite(str(frame_path), frame)
                    
                    # Process frame with Gemini Vision
                    print(f"Processing frame {frame_index} (saved as {frame_filename})")
                    
                    # Add a small delay to avoid rate limiting
                    await asyncio.sleep(0.1)
                    
                    # Process with vision API
                    try:
                        # Use a hardcoded list of ingredients for testing if needed
                        # ingredients = [{"label": "tomato", "category": "ingredient", "confidence": 0.95}]
                        
                        # Process with Gemini Vision
                        ingredients = await self.vision_processor.process_frame(frame, debug_mode=self.debug_mode)
                        
                        # If no ingredients were found, add a placeholder for testing
                        if not ingredients and self.debug_mode:
                            print("No ingredients detected, adding test ingredient for debugging")
                            ingredients = [{"label": "test ingredient", "category": "ingredient", "confidence": 0.99}]
                        
                        # Update all ingredients set
                        for ingredient in ingredients:
                            self.all_ingredients.add(ingredient["label"])
                        
                        # Add to frame ingredients
                        frame_data = {
                            "frame_path": f"/static/frames/{frame_filename}",
                            "ingredients": ingredients
                        }
                        self.frame_ingredients.append(frame_data)
                        
                        # Yield progress update
                        yield frame_data
                        
                        processed_count += 1
                    except Exception as e:
                        print(f"Error processing frame {frame_index}: {e}")
                        # Continue to next frame on error
                
                frame_index += 1
            
            # Release video
            self.video.release()
            
            print(f"Video processing complete. Processed {processed_count} frames.")
            print(f"Detected {len(self.all_ingredients)} unique ingredients: {', '.join(self.all_ingredients)}")
            
        except Exception as e:
            print(f"Error in process_video: {e}")
            import traceback
            traceback.print_exc()
            raise

    def get_frame(self, frame_number: int) -> Tuple[bool, np.ndarray]:
        """Get specific frame from video"""
        if not self.video or not self.video.isOpened():
            return False, None
            
        # Set position to requested frame
        self.video.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
        
        # Read frame
        ret, frame = self.video.read()
        
        return ret, frame

    def create_thumbnail(self, frame: np.ndarray) -> str:
        """Create a base64 encoded thumbnail of the frame"""
        try:
            # Resize frame to thumbnail size
            height, width = frame.shape[:2]
            max_dim = 300
            scale = max_dim / max(height, width)
            new_width = int(width * scale)
            new_height = int(height * scale)
            thumbnail = cv2.resize(frame, (new_width, new_height))
            
            # Convert to JPEG
            _, buffer = cv2.imencode('.jpg', thumbnail, [cv2.IMWRITE_JPEG_QUALITY, 70])
            
            # Convert to base64
            base64_thumbnail = base64.b64encode(buffer).decode('utf-8')
            
            return f"data:image/jpeg;base64,{base64_thumbnail}"
        except Exception as e:
            print(f"Error creating thumbnail: {e}")
            return ""

    def close(self):
        """Close video file"""
        if self.video and self.video.isOpened():
            self.video.release()
            self.video = None
