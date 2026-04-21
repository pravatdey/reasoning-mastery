"""
Database utilities for tracking lesson generation and video uploads
"""

from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any

from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

from .logger import get_logger

logger = get_logger(__name__)
Base = declarative_base()


class LessonRecord(Base):
    """Model for tracking generated lessons and videos"""
    __tablename__ = "lessons"

    id = Column(Integer, primary_key=True)
    part_number = Column(Integer, unique=True, nullable=False)
    topic_title = Column(String(500))
    category = Column(String(100))  # verbal_reasoning / analytical_reasoning
    status = Column(String(20), default="pending")  # pending, generated, uploaded, failed
    video_path = Column(String(500))
    youtube_id = Column(String(50))
    youtube_url = Column(String(200))
    playlist_id = Column(String(50))
    comment_id = Column(String(50))
    script_path = Column(String(500))
    audio_path = Column(String(500))
    thumbnail_path = Column(String(500))
    duration = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)
    uploaded_at = Column(DateTime)
    error = Column(Text)


class Database:
    """Database manager for lesson tracking"""

    def __init__(self, db_path: str = "data/reasoning_tracker.db"):
        db_file = Path(db_path)
        db_file.parent.mkdir(parents=True, exist_ok=True)

        self.engine = create_engine(f"sqlite:///{db_path}", echo=False)
        self.SessionLocal = sessionmaker(bind=self.engine)
        Base.metadata.create_all(self.engine)
        logger.info(f"Database initialized at: {db_path}")

    def get_session(self) -> Session:
        return self.SessionLocal()

    def get_next_part_number(self) -> int:
        """Get the next part number to generate"""
        with self.get_session() as session:
            last = session.query(LessonRecord).filter(
                LessonRecord.status.in_(["generated", "uploaded"])
            ).order_by(LessonRecord.part_number.desc()).first()
            return (last.part_number + 1) if last else 1

    def create_lesson_record(self, part_number: int, topic_title: str, category: str) -> LessonRecord:
        """Create a new lesson record"""
        with self.get_session() as session:
            existing = session.query(LessonRecord).filter_by(part_number=part_number).first()
            if existing:
                logger.info(f"Lesson record already exists for part {part_number}")
                return existing

            record = LessonRecord(
                part_number=part_number,
                topic_title=topic_title,
                category=category,
                status="pending"
            )
            session.add(record)
            session.commit()
            session.refresh(record)
            logger.info(f"Created lesson record: Part {part_number} - {topic_title}")
            return record

    def update_lesson_status(self, part_number: int, status: str, **fields) -> None:
        """Update lesson status and optional fields"""
        with self.get_session() as session:
            record = session.query(LessonRecord).filter_by(part_number=part_number).first()
            if record:
                record.status = status
                for key, value in fields.items():
                    if hasattr(record, key):
                        setattr(record, key, value)
                if status == "uploaded":
                    record.uploaded_at = datetime.utcnow()
                session.commit()
                logger.info(f"Part {part_number} status updated to: {status}")

    def get_lesson_by_part(self, part_number: int) -> Optional[LessonRecord]:
        """Get lesson record by part number"""
        with self.get_session() as session:
            record = session.query(LessonRecord).filter_by(part_number=part_number).first()
            if record:
                # Detach from session
                session.expunge(record)
            return record

    def get_progress(self) -> Dict[str, Any]:
        """Get overall progress statistics"""
        with self.get_session() as session:
            total = session.query(LessonRecord).count()
            uploaded = session.query(LessonRecord).filter_by(status="uploaded").count()
            generated = session.query(LessonRecord).filter_by(status="generated").count()
            failed = session.query(LessonRecord).filter_by(status="failed").count()

            return {
                "total_recorded": total,
                "uploaded": uploaded,
                "generated": generated,
                "failed": failed,
                "next_part": self.get_next_part_number()
            }
