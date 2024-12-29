from datetime import datetime
from sqlalchemy import Column, Integer, Text, DateTime, ForeignKey, MetaData, Table

def upgrade(migrate_engine):
    meta = MetaData(bind=migrate_engine)
    
    # Создаем таблицу dialog_summaries
    dialog_summaries = Table(
        'dialog_summaries', meta,
        Column('id', Integer, primary_key=True),
        Column('user_id', Integer, ForeignKey('users.id'), nullable=False),
        Column('summary_text', Text, nullable=False),
        Column('start_message_id', Integer, ForeignKey('chat_history.id')),
        Column('end_message_id', Integer, ForeignKey('chat_history.id')),
        Column('level', Integer, default=1),
        Column('created_at', DateTime, default=datetime.utcnow),
    )
    
    # Создаем таблицу
    dialog_summaries.create()

def downgrade(migrate_engine):
    meta = MetaData(bind=migrate_engine)
    
    # Удаляем таблицу
    dialog_summaries = Table('dialog_summaries', meta)
    dialog_summaries.drop()