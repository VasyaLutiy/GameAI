"""Миграция для добавления таблицы истории диалогов"""
from sqlalchemy import create_engine, text
import os

def migrate():
    DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///bot_database.db')
    engine = create_engine(DATABASE_URL)
    
    # SQL для создания таблицы chat_history
    create_table_sql = """
    CREATE TABLE IF NOT EXISTS chat_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        message TEXT NOT NULL,
        response TEXT NOT NULL,
        character_mode VARCHAR(50) NOT NULL,
        timestamp DATETIME NOT NULL,
        embedding BLOB,
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    );
    
    -- Индексы для оптимизации запросов
    CREATE INDEX IF NOT EXISTS idx_chat_history_user_id ON chat_history(user_id);
    CREATE INDEX IF NOT EXISTS idx_chat_history_timestamp ON chat_history(timestamp);
    CREATE INDEX IF NOT EXISTS idx_chat_history_character ON chat_history(character_mode);
    """
    
    with engine.connect() as conn:
        # Проверяем, существует ли таблица
        result = conn.execute(text(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='chat_history';"
        ))
        table_exists = result.fetchone() is not None
        
        if not table_exists:
            # Создаем таблицу и индексы
            conn.execute(text(create_table_sql))
            conn.commit()
            print("Таблица chat_history создана успешно")
        else:
            print("Таблица chat_history уже существует")

if __name__ == "__main__":
    migrate()
