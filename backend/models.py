from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()

class Video(Base):
    __tablename__ = "videos"
    
    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, nullable=False)
    original_path = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    segments = relationship("Segment", back_populates="video")

class Segment(Base):
    __tablename__ = "segments"
    
    id = Column(Integer, primary_key=True, index=True)
    video_id = Column(Integer, ForeignKey("videos.id"), nullable=False)
    index = Column(Integer, nullable=False)
    path = Column(String, nullable=False)
    start_sec = Column(Float, nullable=False)
    end_sec = Column(Float, nullable=False)
    decision = Column(String, default="pending")  # pending, keep, drop
    name = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    video = relationship("Video", back_populates="segments")
