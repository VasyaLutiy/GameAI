from datetime import datetime
import pytz
from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.orm import relationship
from models.base import Base
from models.note import Note
from models.event import Event
from models.chat_history import ChatHistory

class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, unique=True, nullable=False)
    username = Column(String(255))
    first_name = Column(String(255))
    last_name = Column(String(255))
    created_at = Column(DateTime, default=lambda: datetime.now(pytz.UTC))
    
    # Отношения
    events = relationship("Event", back_populates="user", cascade="all, delete-orphan")
    chat_history = relationship("ChatHistory", back_populates="user", 
                              order_by="desc(ChatHistory.timestamp)",
                              cascade="all, delete-orphan")
    notes = relationship("Note", back_populates="user", cascade="all, delete-orphan")
    
    def get_recent_dialogs(self, limit: int = 5) -> list:
        """Получить последние диалоги пользователя"""
        return self.chat_history[:limit]
    
    def get_dialogs_by_character(self, character_mode: str, limit: int = 5) -> list:
        """Получить диалоги пользователя с определенным характером бота"""
        return [d for d in self.chat_history 
                if d.character_mode == character_mode][:limit]
    
    def __repr__(self):
        return f"<User(telegram_id={self.telegram_id}, username={self.username})>"
    
    @property
    def full_name(self):
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.first_name or self.username or str(self.telegram_id)