from datetime import datetime
import pytz
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.orm import relationship

from .base import Base

class Event(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text)
    datetime = Column(DateTime, nullable=False)
    reminder_sent = Column(Boolean, default=False)
    created_at = Column(DateTime, default=lambda: datetime.now(pytz.UTC))
    telegram_chat_id = Column(Integer)  # ID чата для отправки напоминания
    
    # Отношение к пользователю
    user = relationship("User", back_populates="events")
    
    def __repr__(self):
        return f"<Event(id={self.id}, title={self.title}, datetime={self.datetime})>"
    
    @property
    def is_past(self):
        return self.datetime < datetime.now(pytz.UTC)
    
    @property
    def time_until(self):
        if self.is_past:
            return None
        return self.datetime - datetime.now(pytz.UTC)
    
    @property
    def formatted_datetime(self):
        """Возвращает отформатированную дату и время в московском часовом поясе"""
        moscow_tz = pytz.timezone("Europe/Moscow")
        if self.datetime.tzinfo is None:
            aware_dt = pytz.UTC.localize(self.datetime)
        else:
            aware_dt = self.datetime
        moscow_time = aware_dt.astimezone(moscow_tz)
        return moscow_time.strftime("%d.%m.%Y %H:%M")
    
    @classmethod
    def create_reminder(cls, user_id: int, chat_id: int, title: str, reminder_time: datetime, description: str = None):
        """Создает новое напоминание"""
        if reminder_time.tzinfo is None:
            reminder_time = pytz.UTC.localize(reminder_time)
        
        return cls(
            user_id=user_id,
            telegram_chat_id=chat_id,
            title=title,
            description=description,
            datetime=reminder_time,
            reminder_sent=False
        )
