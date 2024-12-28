"""Note model for storing user notes"""
from datetime import datetime
import pytz
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship

from .base import Base

class Note(Base):
    """Model for storing user notes"""
    __tablename__ = "notes"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(pytz.UTC))
    updated_at = Column(DateTime, default=lambda: datetime.now(pytz.UTC), 
                       onupdate=lambda: datetime.now(pytz.UTC))

    # Relationship to user
    user = relationship("User", back_populates="notes")

    def __repr__(self):
        return f"<Note(id={self.id}, user_id={self.user_id}, title={self.title})>"