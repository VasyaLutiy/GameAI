from db_manager import DatabaseManager

def init_database():
    db = DatabaseManager()
    
    # SQL запрос для создания таблицы пользователей
    create_table_query = """
    CREATE TABLE IF NOT EXISTS users (
        user_id BIGINT PRIMARY KEY,
        username VARCHAR(255),
        first_name VARCHAR(255),
        last_name VARCHAR(255),
        registration_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """
    
    # Создаем таблицу
    result = db.execute_query(create_table_query)
    if result is not None:
        print("Table 'users' created successfully")
    else:
        print("Error creating table 'users'")

if __name__ == "__main__":
    init_database()