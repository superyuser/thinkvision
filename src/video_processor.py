import cv2
import numpy as np
from typing import Tuple, Optional, Generator, Dict, Any
import asyncio
from datetime import datetime
from pathlib import Path
from .ai_vision import AnthropicVision
from .storage import ObjectStorage

class VideoProcessor:
    def __init__(self):
        self.video = None
        self.frame_width = 640
        self.frame_height = 480
        self.processing = False
        self.current_frame_count = 0
        self.total_frames = 0
        self.vision = AnthropicVision()
        self.storage = ObjectStorage()
        self.last_objects = []

    async def load_video(self, video_path: str) -> bool:
        """Load a video file for processing"""
        if not Path(video_path).exists():
            return False
            
        self.video = cv2.VideoCapture(video_path)
        if not self.video.isOpened():
            return False
            
        self.total_frames = int(self.video.get(cv2.CAP_PROP_FRAME_COUNT))
        self.current_frame_count = 0
        self.frame_width = int(self.video.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.frame_height = int(self.video.get(cv2.CAP_PROP_FRAME_HEIGHT))
        return True

    async def get_frame(self) -> Optional[np.ndarray]:
        """Get next frame from the video"""
        if not self.video or not self.video.isOpened():
            return None
        
        ret, frame = self.video.read()
        if not ret:
            return None
            
        self.current_frame_count += 1
        return frame

    def get_progress(self) -> float:
        """Get current processing progress as percentage"""
        if self.total_frames == 0:
            return 0.0
        return (self.current_frame_count / self.total_frames) * 100

    async def process_video(self, video_path: str) -> Generator[Tuple[np.ndarray, dict], None, None]:
        """Process entire video and yield frames with metadata"""
        if not await self.load_video(video_path):
            return

        while True:
            frame = await self.get_frame()
            if frame is None:
                break

            annotated_frame, metadata = await self.process_frame(frame)
            if annotated_frame is not None:
                yield annotated_frame, metadata

        self.release()

    async def process_frame(self, frame: np.ndarray) -> Tuple[np.ndarray, dict]:
        """Process a frame and return the annotated frame with metadata"""
        if frame is None:
            return None, {}

        # Create a copy for annotation
        annotated_frame = frame.copy()
        
        # Detect objects using AI Vision
        detected_objects = await self.vision.process_frame(frame)
        
        # Add visual overlays
        annotated_frame = self.add_overlay(annotated_frame, detected_objects)
        
        # Store objects in database
        if detected_objects:
            await self.storage.store_objects(
                frame_number=self.current_frame_count,
                timestamp=datetime.now(),
                objects=detected_objects
            )
            self.last_objects = detected_objects
        
        # Basic frame metadata
        metadata = {
            "timestamp": datetime.now().isoformat(),
            "frame_size": frame.shape,
            "frame_number": self.current_frame_count,
            "total_frames": self.total_frames,
            "progress_percent": self.get_progress(),
            "objects": detected_objects
        }

        return annotated_frame, metadata

    def add_overlay(self, frame: np.ndarray, objects: list) -> np.ndarray:
        """Add text overlays for detected objects"""
        if frame is None or not objects:
            return frame

        overlay = frame.copy()
        alpha = 0.3  # Transparency factor

        for obj in objects:
            if "bbox" in obj and "label" in obj:
                x1, y1, x2, y2 = obj["bbox"]
                conf = obj.get("confidence", 0.0)
                
                # Draw semi-transparent background for text
                cv2.rectangle(overlay, (x1, y1-25), (x1 + len(obj["label"])*10, y1), (0, 0, 0), -1)
                
                # Draw bounding box with confidence-based color
                color = (0, int(255 * conf), 0)  # Green based on confidence
                cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                
                # Add label with confidence score
                label = f"{obj['label']} ({conf:.2f})"
                cv2.putText(frame, label, (x1, y1 - 10),
                          cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)
                
                # Add object category and description as tooltip
                if "category" in obj and "description" in obj:
                    tooltip = f"{obj['category']}: {obj['description']}"
                    cv2.putText(frame, tooltip, (x1, y2 + 15),
                              cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 200, 200), 1)

        # Blend the overlay with the original frame
        cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0, frame)
        return frame

    async def search_objects(self, query: str) -> list:
        """Search for objects in processed frames"""
        return await self.vision.search_objects(query)

    def get_frame_objects(self, frame_number: int) -> list:
        """Get objects detected in a specific frame"""
        return self.vision.get_frame_objects(frame_number)

    def release(self):
        """Release video resources"""
        if self.video:
            self.video.release()
            self.video = None
            
    def __del__(self):
        self.release()
