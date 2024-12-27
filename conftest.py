import pytest
import os
import sys
import logging
import mysql.connector

# Настройка логирования
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
from db_manager import DatabaseManager
from test_config import DB_CONFIG, TEST_TABLE_PREFIX, TEST_TABLES, TEST_SCENES

def cleanup_test_tables(db):
    """Удаляет тестовые таблицы если они существуют"""
    tables = [
        f"{TEST_TABLE_PREFIX}user_states",
        f"{TEST_TABLE_PREFIX}users",
        f"{TEST_TABLE_PREFIX}scenes"
    ]
    for table in tables:
        try:
            db.execute_query(f"DROP TABLE IF EXISTS {table}")
        except Exception as e:
            print(f"Error dropping table {table}: {e}")

@pytest.fixture(scope="session", autouse=True)
def setup_test_database():
    """Создает тестовые таблицы"""
    db = DatabaseManager(DB_CONFIG)
    
    # Очищаем старые тестовые таблицы
    cleanup_test_tables(db)
    
    # Создаем тестовые таблицы
    for table_sql in TEST_TABLES:
        try:
            db.execute_query(table_sql)
        except Exception as e:
            raise Exception(f"Failed to create table: {table_sql}. Error: {str(e)}")
    
    # Добавляем тестовые данные
    for scene_sql in TEST_SCENES:
        try:
            db.execute_query(scene_sql)
        except Exception as e:
            raise Exception(f"Failed to insert test data: {scene_sql}. Error: {str(e)}")
    
    yield db
    
    # Очистка после тестов
    cleanup_test_tables(db)