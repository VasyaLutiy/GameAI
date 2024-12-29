from datetime import datetime
import pytz
from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.orm import relationship
from models.base import Base
from models.note import Note
from models.event import Event
from models.chat_history import ChatHistory
from models.dialog_summary import DialogSummary

class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, unique=True, nullable=False)
    username = Column(String(255))
    first_name = Column(String(255))
    last_name = Column(String(255))
    character_mode = Column(String(50), default='default')
    user_info = Column(String(1000))  # JSON строка с информацией о пользователе
    created_at = Column(DateTime, default=lambda: datetime.now(pytz.UTC))
    
    # Отношения
    events = relationship("Event", back_populates="user", cascade="all, delete-orphan")
    chat_history = relationship("ChatHistory", back_populates="user", 
                              order_by="desc(ChatHistory.timestamp)",
                              cascade="all, delete-orphan")
    notes = relationship("Note", back_populates="user", cascade="all, delete-orphan")
    summaries = relationship("DialogSummary", back_populates="user", 
                           order_by="desc(DialogSummary.created_at)",
                           cascade="all, delete-orphan")
    
    def get_recent_dialogs(self, limit: int = 20) -> list:
        """Получить последние диалоги пользователя"""
        # Получаем последние сообщения в обратном порядке
        messages = sorted(
            self.chat_history,
            key=lambda x: x.timestamp,
            reverse=True
        )[:limit]
        # Возвращаем в правильном порядке (от старых к новым)
        return sorted(messages, key=lambda x: x.timestamp)
    
    def get_dialogs_by_character(self, character_mode: str, limit: int = 20) -> list:
        """Получить диалоги пользователя с определенным характером бота"""
        # Фильтруем и сортируем сообщения по времени
        messages = sorted(
            [d for d in self.chat_history if d.character_mode == character_mode],
            key=lambda x: x.timestamp,
            reverse=True
        )[:limit]
        # Возвращаем в правильном порядке (от старых к новым)
        return sorted(messages, key=lambda x: x.timestamp)
    
    def __repr__(self):
        return f"<User(telegram_id={self.telegram_id}, username={self.username})>"
    
    @property
    def full_name(self):
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.first_name or self.username or str(self.telegram_id)
        
    def get_latest_summary(self, level: int = None) -> 'DialogSummary':
        """Получить последнее саммари определенного уровня"""
        query = self.summaries
        if level is not None:
            query = [s for s in query if s.level == level]
        return query[0] if query else None
    
    def get_summaries_by_level(self, level: int, limit: int = 5) -> list:
        """Получить саммари определенного уровня"""
        return [s for s in self.summaries if s.level == level][:limit]
    
    def get_summary_chain(self) -> str:
        """Получить цепочку саммари от общего к детальному"""
        # Сначала берем самое последнее саммари высшего уровня
        high_level = self.get_latest_summary(level=2)
        if not high_level:
            high_level = self.get_latest_summary(level=1)
        
        if not high_level:
            return "История диалогов пока не накоплена"
            
        result = [f"Общее саммари (уровень {high_level.level}):", high_level.summary_text]
        
        # Добавляем последние детальные саммари
        if high_level.level == 2:
            recent_l1 = self.get_summaries_by_level(level=1, limit=3)
            if recent_l1:
                result.append("\nПоследние детальные саммари:")
                for s in recent_l1:
                    result.append(f"- {s.summary_text}")
        
        return "\n".join(result)

    def update_user_info(self, key: str, value: str):
        """Обновить информацию о пользователе"""
        import json
        try:
            info = json.loads(self.user_info) if self.user_info else {}
        except:
            info = {}
        info[key] = value
        self.user_info = json.dumps(info)

    def get_user_info(self, key: str = None) -> dict:
        """Получить информацию о пользователе"""
        import json
        try:
            info = json.loads(self.user_info) if self.user_info else {}
        except:
            info = {}
        return info.get(key) if key else info

    def get_user_profile(self) -> str:
        """Получить профиль пользователя в текстовом виде"""
        info = self.get_user_info()
        if not info:
            return "🤔 Пока я ничего не знаю о вас. Расскажите о себе в диалоге!"
            
        parts = ["👤 Профиль пользователя"]
        
        # Основная информация
        if 'name' in info:
            parts.append(f"📝 Имя: {info['name']}")
        if 'age' in info:
            parts.append(f"🎂 Возраст: {info['age']} лет")
        if 'occupation' in info:
            parts.append(f"💼 Род занятий: {info['occupation']}")
        if 'interests' in info:
            parts.append(f"🎯 Интересы: {info['interests']}")
            
        # Статистика диалогов
        dialog_count = len(self.chat_history)
        if dialog_count > 0:
            parts.append("\n📊 Статистика общения:")
            parts.append(f"• Всего сообщений: {dialog_count}")
            parts.append(f"• Текущий режим: {self.character_mode or 'default'}")
            
            # Последняя активность
            last_msg = max(self.chat_history, key=lambda x: x.timestamp) if self.chat_history else None
            if last_msg:
                last_time = last_msg.timestamp.strftime("%d.%m.%Y %H:%M")
                parts.append(f"• Последняя активность: {last_time}")
        
        if len(parts) <= 1:
            return "🤔 Базовая информация пока отсутствует"
            
        return "\n".join(parts)