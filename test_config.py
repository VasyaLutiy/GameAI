# Конфигурация тестовой базы данных (используем ту же базу данных)
DB_CONFIG = {
    'host': '172.17.0.1',
    'user': 'user1',
    'password': 'v@1oZ0FN0Y3FgwYX>qzgKcuX',
    'database': 'game1'
}

# Префикс для тестовых таблиц
TEST_TABLE_PREFIX = 'test_'

# SQL для создания тестовых таблиц
TEST_TABLES = [
    f"""
    CREATE TABLE IF NOT EXISTS {TEST_TABLE_PREFIX}users (
        user_id BIGINT PRIMARY KEY,
        username VARCHAR(255),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    f"""
    CREATE TABLE IF NOT EXISTS {TEST_TABLE_PREFIX}scenes (
        id INT PRIMARY KEY AUTO_INCREMENT,
        parent INT,
        description TEXT NOT NULL,
        options JSON,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    f"""
    CREATE TABLE IF NOT EXISTS {TEST_TABLE_PREFIX}user_states (
        user_id BIGINT PRIMARY KEY,
        state VARCHAR(50) NOT NULL,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES {TEST_TABLE_PREFIX}users(user_id) ON DELETE CASCADE
    )
    """
]

# Тестовые данные для сцен
TEST_SCENES = [
    f"""
    INSERT INTO {TEST_TABLE_PREFIX}scenes (id, description, options) 
    VALUES (1, 'Начальная сцена', '{{"2": "Пойти налево", "3": "Пойти направо"}}')
    """,
    f"""
    INSERT INTO {TEST_TABLE_PREFIX}scenes (id, parent, description, options)
    VALUES (2, 1, 'Вы пошли налево', '{{"4": "Вернуться", "5": "Продолжить"}}')
    """,
    f"""
    INSERT INTO {TEST_TABLE_PREFIX}scenes (id, parent, description, options)
    VALUES (3, 1, 'Вы пошли направо', '{{"4": "Вернуться", "6": "Продолжить"}}')
    """
]