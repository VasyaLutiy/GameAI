import mysql.connector
from mysql.connector import Error
import logging

class DatabaseManager:
    def __init__(self, config=None):
        if config is None:
            self.host = "172.17.0.1"
            self.database = "game1"
            self.user = "user1"
            self.password = "v@1oZ0FN0Y3FgwYX>qzgKcuX"
        else:
            self.host = config.get('host', 'localhost')
            self.database = config.get('database', 'game1')
            self.user = config.get('user', 'root')
            self.password = config.get('password', 'root')
        
        self.connection = None
        self.logger = logging.getLogger(__name__)

    def connect(self):
        try:
            if self.connection is None or not self.connection.is_connected():
                self.logger.info(f"Connecting to MySQL database {self.database} at {self.host}")
                self.connection = mysql.connector.connect(
                    host=self.host,
                    database=self.database,
                    user=self.user,
                    password=self.password
                )
                if self.connection.is_connected():
                    db_info = self.connection.get_server_info()
                    cursor = self.connection.cursor()
                    cursor.execute("SELECT DATABASE()")
                    db_name = cursor.fetchone()[0]
                    cursor.close()
                    self.logger.info(f"Connected to MySQL Server version {db_info}")
                    self.logger.info(f"Connected to database: {db_name}")
                    return True
                else:
                    self.logger.error("Failed to verify database connection")
                    return False
        except Error as e:
            self.logger.error(f"Error connecting to MySQL: {e}")
            self.logger.error(f"Connection params: host={self.host}, database={self.database}, user={self.user}")
            return False

    def disconnect(self):
        if self.connection and self.connection.is_connected():
            self.connection.close()
            self.logger.info("MySQL connection closed")

    def execute_query(self, query, params=None):
        cursor = None
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                if not self.connection or not self.connection.is_connected():
                    if not self.connect():
                        self.logger.error("Failed to connect to database")
                        retry_count += 1
                        continue

                cursor = self.connection.cursor()
                self.logger.debug(f"Executing query: {query}")
                self.logger.debug(f"Parameters: {params}")
                break
            except mysql.connector.Error as e:
                self.logger.error(f"Connection error (attempt {retry_count + 1}): {e}")
                self.connection = None
                retry_count += 1
                if retry_count == max_retries:
                    raise
        
        if retry_count == max_retries:
            self.logger.error("Max retries reached, giving up")
            return None

        try:
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

        except mysql.connector.Error as e:
            self.logger.error(f"Error executing query: {e}")
            self.logger.error(f"Query: {query}")
            if params:
                self.logger.error(f"Parameters: {params}")
            return None
        finally:
            if cursor:
                try:
                    cursor.close()
                except:
                    pass

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