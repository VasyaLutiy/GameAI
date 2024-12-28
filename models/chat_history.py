from datetime import datetime, UTC
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, LargeBinary
from sqlalchemy.orm import relationship

from .user import Base

class ChatHistory(Base):
    """Модель для хранения истории диалогов"""
    __tablename__ = "chat_history"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    message = Column(Text, nullable=False)
    response = Column(Text, nullable=False)
    character_mode = Column(String(50), nullable=False)
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow)
    embedding = Column(LargeBinary, nullable=True)  # Для будущего использования с векторными эмбеддингами
    
    # Отношение к пользователю
    user = relationship("User", back_populates="chat_history")
    
    def __repr__(self):
        return f"<ChatHistory(id={self.id}, user_id={self.user_id}, timestamp={self.timestamp})>"
    
    @property
    def formatted_dialog(self) -> str:
        """Форматирует диалог для использования в контексте"""
        return f"User: {self.message}\nAssistant ({self.character_mode}): {self.response}"
    
    @classmethod
    def create_dialog_entry(cls, user_id: int, message: str, response: str, 
                          character_mode: str, embedding: bytes = None):
        """Создает новую запись диалога"""
        return cls(
            user_id=user_id,
            message=message,
            response=response,
            character_mode=character_mode,
            embedding=embedding,
            timestamp=datetime.now(UTC)
        )