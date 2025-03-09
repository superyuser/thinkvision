import os
import cv2
import time
import glob
import asyncio
import numpy as np
from typing import Dict, List, Any, AsyncGenerator
from .gemini_vision import GeminiVision

class VideoProcessor:
    def __init__(self, debug_mode=False):
        """Initialize VideoProcessor
        
        Args:
            debug_mode: Whether to print debug information
        """
        self.gemini_vision = GeminiVision()
        self.debug_mode = debug_mode
        
        # Create directories if they don't exist
        os.makedirs("static/frames", exist_ok=True)

    async def process_video(self, video_path: str, sample_rate=None, max_frames=5) -> AsyncGenerator[Dict[str, Any], None]:
        """Process a video file and extract ingredients from frames

        Args:
            video_path: Path to the video file
            sample_rate: Sample every N frames
            max_frames: Maximum number of frames to process (default: 5)

        Yields:
            Dictionary with frame path and detected ingredients
        """
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"Video file not found: {video_path}")
        
        # Open the video file
        cap = cv2.VideoCapture(video_path)
        
        # Get video properties
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        duration = frame_count / fps if fps > 0 else 0
        
        if self.debug_mode:
            print(f"Video has {frame_count} frames, {fps} fps, duration: {duration:.2f} seconds")
        
        # Clear previous frames
        for f in glob.glob("static/frames/*.jpg"):
            os.remove(f)
            
        # Calculate appropriate sample rate to get ~max_frames frames
        adjusted_sample_rate = max(1, frame_count // max_frames)
        
        if self.debug_mode:
            print(f"Using sample rate: {adjusted_sample_rate} to get approximately {max_frames} frames")
        
        # Process frames
        frame_idx = 0
        processed_frames = 0
        all_ingredients = set()
        
        # Track API usage to stay within limits
        # Gemini API has a rate limit of approximately 60 requests per minute
        # We'll be more conservative and limit to 30 requests per minute
        api_calls = 0
        api_call_start_time = time.time()
        
        while cap.isOpened() and processed_frames < max_frames:
            ret, frame = cap.read()
            
            if not ret:
                break
                
            if frame_idx % adjusted_sample_rate == 0:
                # Save frame
                frame_path = f"static/frames/frame_{processed_frames:04d}.jpg"
                cv2.imwrite(frame_path, frame)
                
                # Check API rate limiting
                api_calls += 1
                current_time = time.time()
                elapsed = current_time - api_call_start_time
                
                # If we're making calls too quickly, add a delay
                if api_calls >= 5 and elapsed < 60:  # 5 calls per minute is very conservative
                    sleep_time = max(0, (60 / 5) - elapsed)
                    if self.debug_mode:
                        print(f"Rate limiting: sleeping for {sleep_time:.2f} seconds")
                    await asyncio.sleep(sleep_time)
                    api_calls = 0
                    api_call_start_time = time.time()
                
                # Process frame with Gemini Vision
                try:
                    if self.debug_mode:
                        print(f"Processing frame {processed_frames} (original idx: {frame_idx})")
                    
                    # Process with Gemini Vision
                    ingredients = await self.gemini_vision.process_frame(frame, self.debug_mode)
                    
                    # Add to all ingredients
                    for ingredient in ingredients:
                        all_ingredients.add(ingredient["label"])
                    
                    # Yield frame result
                    yield {
                        "frame": f"/static/frames/frame_{processed_frames:04d}.jpg",
                        "ingredients": ingredients
                    }
                    
                    # Add a small delay between API calls to prevent rate limiting
                    await asyncio.sleep(1)
                    
                except Exception as e:
                    if self.debug_mode:
                        print(f"Error processing frame {frame_idx}: {e}")
                
                processed_frames += 1
            
            frame_idx += 1
        
        # Release video capture
        cap.release()
        
        # Yield summary
        yield {
            "summary": True,
            "total_frames": frame_count,
            "processed_frames": processed_frames,
            "unique_ingredients": list(all_ingredients)
        }
