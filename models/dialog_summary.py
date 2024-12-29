from datetime import datetime
from sqlalchemy import Column, Integer, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from models.base import Base

class DialogSummary(Base):
    __tablename__ = 'dialog_summaries'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    summary_text = Column(Text, nullable=False)
    start_message_id = Column(Integer, ForeignKey('chat_history.id'))
    end_message_id = Column(Integer, ForeignKey('chat_history.id'))
    level = Column(Integer, default=1)  # 1=20 сообщений, 2=5 саммари, 3=общее
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Связи
    user = relationship("User", back_populates="summaries")
    start_message = relationship("ChatHistory", foreign_keys=[start_message_id])
    end_message = relationship("ChatHistory", foreign_keys=[end_message_id])

    def __repr__(self):
        return f"<DialogSummary(id={self.id}, user_id={self.user_id}, level={self.level})>"