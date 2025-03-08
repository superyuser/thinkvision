from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, JSON, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import json

Base = declarative_base()

class Video(Base):
    __tablename__ = 'videos'

    id = Column(Integer, primary_key=True)
    filename = Column(String)
    timestamp = Column(DateTime, default=datetime.utcnow)
    total_frames = Column(Integer)
    video_data = Column(JSON)  # Renamed from metadata

class Frame(Base):
    __tablename__ = 'frames'

    id = Column(Integer, primary_key=True)
    video_id = Column(Integer, ForeignKey('videos.id'))
    frame_number = Column(Integer)
    timestamp = Column(DateTime, default=datetime.utcnow)
    frame_data = Column(JSON)  # Renamed from metadata
    
    video = relationship("Video", back_populates="frames")
    objects = relationship("ObjectDetection", back_populates="frame")

Video.frames = relationship("Frame", back_populates="video")

class ObjectDetection(Base):
    __tablename__ = 'object_detections'

    id = Column(Integer, primary_key=True)
    frame_id = Column(Integer, ForeignKey('frames.id'))
    label = Column(String)
    category = Column(String)
    description = Column(String)
    confidence = Column(Float)
    bbox = Column(JSON)  # Stores bounding box coordinates [x1, y1, x2, y2]
    timestamp = Column(DateTime, default=datetime.utcnow)
    extra_data = Column(JSON)  # Additional metadata
    
    frame = relationship("Frame", back_populates="objects")

class ObjectStorage:
    def __init__(self, db_url: str = "sqlite:///objects.db"):
        self.engine = create_engine(db_url)
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.current_video_id = None

    async def start_video(self, filename: str, total_frames: int, metadata: Dict = None) -> int:
        """Start processing a new video"""
        session = self.Session()
        try:
            video = Video(
                filename=filename,
                total_frames=total_frames,
                video_data=metadata or {}
            )
            session.add(video)
            session.commit()
            self.current_video_id = video.id
            return video.id
        finally:
            session.close()

    async def store_objects(self, frame_number: int, timestamp: datetime, objects: List[Dict[Any, Any]]):
        """Store objects detected in a video frame"""
        if not self.current_video_id:
            return

        session = self.Session()
        try:
            # Create frame record
            frame = Frame(
                video_id=self.current_video_id,
                frame_number=frame_number,
                timestamp=timestamp,
                frame_data={"timestamp": timestamp.isoformat()}
            )
            session.add(frame)
            session.flush()  # Get frame ID

            # Store detected objects
            for obj in objects:
                detection = ObjectDetection(
                    frame_id=frame.id,
                    label=obj.get('label'),
                    category=obj.get('category'),
                    description=obj.get('description'),
                    confidence=obj.get('confidence', 0.0),
                    bbox=obj.get('bbox'),
                    extra_data=obj.get('metadata', {})
                )
                session.add(detection)
            
            session.commit()
        except Exception as e:
            session.rollback()
            print(f"Error storing frame objects: {e}")
        finally:
            session.close()

    async def find_object(self, query: str, video_id: Optional[int] = None) -> List[Dict[Any, Any]]:
        """Search for objects by label or description, optionally filtered by video"""
        session = self.Session()
        try:
            query_obj = session.query(ObjectDetection, Frame, Video).join(Frame).join(Video)
            
            # Add search conditions
            query_obj = query_obj.filter(
                (ObjectDetection.label.ilike(f"%{query}%")) |
                (ObjectDetection.description.ilike(f"%{query}%"))
            )
            
            # Filter by video if specified
            if video_id:
                query_obj = query_obj.filter(Video.id == video_id)
            
            results = query_obj.order_by(ObjectDetection.timestamp.desc()).limit(10).all()

            return [{
                'label': obj.label,
                'category': obj.category,
                'description': obj.description,
                'confidence': obj.confidence,
                'bbox': obj.bbox,
                'frame_number': frame.frame_number,
                'video_filename': video.filename,
                'timestamp': obj.timestamp.isoformat(),
                'metadata': obj.extra_data
            } for obj, frame, video in results]
        finally:
            session.close()

    async def get_frame_objects(self, frame_number: int, video_id: Optional[int] = None) -> List[Dict[Any, Any]]:
        """Get objects detected in a specific frame"""
        if not video_id:
            video_id = self.current_video_id
        if not video_id:
            return []

        session = self.Session()
        try:
            frame = session.query(Frame).filter(
                Frame.video_id == video_id,
                Frame.frame_number == frame_number
            ).first()
            
            if not frame:
                return []
            
            objects = session.query(ObjectDetection).filter(
                ObjectDetection.frame_id == frame.id
            ).all()

            return [{
                'label': obj.label,
                'category': obj.category,
                'description': obj.description,
                'confidence': obj.confidence,
                'bbox': obj.bbox,
                'timestamp': obj.timestamp.isoformat(),
                'metadata': obj.extra_data
            } for obj in objects]
        finally:
            session.close()

    async def get_video_summary(self, video_id: Optional[int] = None) -> Dict[str, Any]:
        """Get summary of objects detected in a video"""
        if not video_id:
            video_id = self.current_video_id
        if not video_id:
            return {}

        session = self.Session()
        try:
            # Get video info
            video = session.query(Video).filter(Video.id == video_id).first()
            if not video:
                return {}

            # Get object statistics
            objects = session.query(ObjectDetection).join(Frame).filter(
                Frame.video_id == video_id
            ).all()

            object_counts = {}
            confidence_sums = {}
            for obj in objects:
                label = obj.label
                object_counts[label] = object_counts.get(label, 0) + 1
                confidence_sums[label] = confidence_sums.get(label, 0) + obj.confidence

            # Calculate average confidence per object type
            summary = {
                'filename': video.filename,
                'total_frames': video.total_frames,
                'processed_frames': session.query(Frame).filter(Frame.video_id == video_id).count(),
                'objects': [{
                    'label': label,
                    'count': count,
                    'avg_confidence': confidence_sums[label] / count
                } for label, count in object_counts.items()]
            }

            return summary
        finally:
            session.close()

    async def cleanup_old_detections(self, days: int = 30):
        """Remove detections older than specified days"""
        session = self.Session()
        try:
            cutoff = datetime.utcnow() - timedelta(days=days)
            
            # Delete old object detections
            session.query(ObjectDetection).filter(
                ObjectDetection.timestamp < cutoff
            ).delete()
            
            # Delete old frames
            session.query(Frame).filter(
                Frame.timestamp < cutoff
            ).delete()
            
            # Delete old videos
            session.query(Video).filter(
                Video.timestamp < cutoff
            ).delete()
            
            session.commit()
        except Exception as e:
            session.rollback()
            print(f"Error cleaning up old data: {e}")
        finally:
            session.close()
