import mysql.connector
from mysql.connector import Error
import logging

class DatabaseManager:
    def __init__(self):
        self.host = "172.17.0.1"
        self.database = "game1"
        self.user = "user1"
        self.password = "v@1oZ0FN0Y3FgwYX>qzgKcuX"
        self.connection = None
        self.logger = logging.getLogger(__name__)

    def connect(self):
        try:
            if self.connection is None or not self.connection.is_connected():
                self.connection = mysql.connector.connect(
                    host=self.host,
                    database=self.database,
                    user=self.user,
                    password=self.password
                )
                if self.connection.is_connected():
                    self.logger.info("Successfully connected to MySQL database")
                    return True
        except Error as e:
            self.logger.error(f"Error connecting to MySQL: {e}")
            return False

    def disconnect(self):
        if self.connection and self.connection.is_connected():
            self.connection.close()
            self.logger.info("MySQL connection closed")

    def execute_query(self, query, params=None):
        cursor = None
        try:
            if not self.connect():
                raise Exception("Failed to connect to database")
                
            cursor = self.connection.cursor()
            self.logger.debug(f"Executing query: {query}")
            self.logger.debug(f"Parameters: {params}")
            
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            
            # Для DDL-запросов (CREATE, DROP и т.д.)
            if query.strip().upper().startswith(('CREATE', 'DROP', 'ALTER')):
                self.connection.commit()
                return True
            
            # Для DML-запросов (INSERT, UPDATE, DELETE)
            elif query.strip().upper().startswith(('INSERT', 'UPDATE', 'DELETE')):
                self.connection.commit()
                affected_rows = cursor.rowcount
                self.logger.debug(f"Affected rows: {affected_rows}")
                return affected_rows
            
            # Для SELECT и других запросов
            else:
                try:
                    result = cursor.fetchall()
                    self.logger.debug(f"Query result: {result}")
                    return result
                except mysql.connector.Error as e:
                    if e.errno == mysql.connector.errorcode.CR_NO_RESULT_SET:
                        return None
                    raise e
        except Error as e:
            self.logger.error(f"Error executing query: {e}")
            return None
        finally:
            if 'cursor' in locals():
                cursor.close()

    def test_connection(self):
        """Test the database connection and return status"""
        try:
            if self.connect():
                self.logger.info("Database connection test successful")
                return True
            return False
        finally:
            self.disconnect()

# Пример использования:
if __name__ == "__main__":
    # Настройка логирования
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Тест подключения
    db = DatabaseManager()
    db.test_connection()