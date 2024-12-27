import logging
from typing import Dict, List, Optional
from datetime import datetime

class Achievement:
    def __init__(self, id: int, name: str, description: str, icon: str, points: int = 0):
        self.id = id
        self.name = name
        self.description = description
        self.icon = icon
        self.points = points

class AchievementManager:
    def __init__(self, db_manager):
        self.db = db_manager
        self.logger = logging.getLogger(__name__)
        self._init_achievements_table()

    def _init_achievements_table(self):
        """Инициализация таблицы достижений"""
        try:
            self.logger.info("Starting table initialization...")
            
            # Проверяем существование таблиц
            check_tables_query = """
            SELECT COUNT(*) 
            FROM information_schema.tables 
            WHERE table_schema = 'game1' 
            AND table_name IN ('achievements', 'user_achievements')
            """
            result = self.db.execute_query(check_tables_query)
            if result and result[0][0] == 2:
                self.logger.info("Achievement tables already exist")
                return True

            # Если таблиц нет, создаем их
            self.logger.info("Creating achievement tables...")
            self.logger.info("Disabling foreign key checks...")
            result = self.db.execute_query("SET FOREIGN_KEY_CHECKS = 0")
            self.logger.debug(f"Foreign key check disable result: {result}")

            # Создаем таблицу достижений
            self.logger.info("Creating achievements table...")
            achievements_table = "CREATE TABLE achievements (id INT NOT NULL AUTO_INCREMENT, name VARCHAR(255) NOT NULL, description TEXT, icon VARCHAR(50), points INT DEFAULT 0, PRIMARY KEY (id)) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci"
            
            try:
                result = self.db.execute_query(achievements_table)
                self.logger.debug(f"Create achievements table result: {result}")
            except Exception as e:
                self.logger.error(f"Error creating achievements table: {e}")
                self.logger.error(f"Query: {achievements_table}")
                raise Exception(f"Failed to create achievements table: {str(e)}")
            self.logger.debug(f"Create achievements table result: {result}")
            
            # Проверяем создание таблицы achievements
            check_query = """
            SELECT COUNT(*) 
            FROM information_schema.tables 
            WHERE table_schema = 'game1' 
            AND table_name = 'achievements'
            """
            check_result = self.db.execute_query(check_query)
            self.logger.debug(f"Check achievements table result: {check_result}")
            
            if not check_result or check_result[0][0] == 0:
                raise Exception("Failed to create achievements table")
                
            # Проверяем структуру таблицы
            desc_result = self.db.execute_query("DESCRIBE achievements")
            self.logger.debug(f"Table structure: {desc_result}")
            if not desc_result:
                raise Exception("Failed to get achievements table structure")
            self.logger.info("Achievements table created successfully")

            # Создаем таблицу пользовательских достижений
            self.logger.info("Creating user_achievements table...")
            user_achievements_table = "CREATE TABLE user_achievements (user_id BIGINT NOT NULL, achievement_id INT NOT NULL, unlocked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, PRIMARY KEY (user_id, achievement_id), FOREIGN KEY (achievement_id) REFERENCES achievements(id) ON DELETE CASCADE) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci"
            
            try:
                result = self.db.execute_query(user_achievements_table)
                self.logger.debug(f"Create user_achievements table result: {result}")
            except Exception as e:
                self.logger.error(f"Error creating user_achievements table: {e}")
                self.logger.error(f"Query: {user_achievements_table}")
                raise Exception(f"Failed to create user_achievements table: {str(e)}")
            
            # Проверяем создание таблицы user_achievements
            check_query = """
            SELECT COUNT(*) 
            FROM information_schema.tables 
            WHERE table_schema = 'game1' 
            AND table_name = 'user_achievements'
            """
            check_result = self.db.execute_query(check_query)
            self.logger.debug(f"Check user_achievements table result: {check_result}")
            
            if not check_result or check_result[0][0] == 0:
                raise Exception("Failed to create user_achievements table")
                
            # Проверяем структуру таблицы
            desc_result = self.db.execute_query("DESCRIBE user_achievements")
            self.logger.debug(f"Table structure: {desc_result}")
            if not desc_result:
                raise Exception("Failed to get user_achievements table structure")
            self.logger.info("User achievements table created successfully")

            # Включаем проверку внешних ключей
            self.logger.info("Enabling foreign key checks...")
            result = self.db.execute_query("SET FOREIGN_KEY_CHECKS = 1")
            self.logger.debug(f"Foreign key check enable result: {result}")
            self.logger.info("Tables created successfully")

            # Проверяем создание таблиц по отдельности
            for table in ['achievements', 'user_achievements']:
                verify_query = f"""
                SELECT COUNT(*) 
                FROM information_schema.tables 
                WHERE table_schema = 'game1' 
                AND table_name = '{table}'
                """
                self.logger.debug(f"Verifying table {table}")
                verify_result = self.db.execute_query(verify_query)
                self.logger.debug(f"Verify result for {table}: {verify_result}")
                
                if not verify_result or verify_result[0][0] == 0:
                    raise Exception(f"Table {table} was not created properly")
                else:
                    self.logger.info(f"Table {table} verified successfully")
            
            # Проверяем структуру таблиц
            self.logger.info("Verifying table structure")
            struct_query = "SHOW CREATE TABLE achievements"
            struct_result = self.db.execute_query(struct_query)
            self.logger.debug(f"Table structure: {struct_result}")
            
            return True
                
        except Exception as e:
            self.logger.error(f"Error initializing achievement tables: {e}")
            raise e

    def add_achievement(self, name: str, description: str, icon: str = "[*]", points: int = 0) -> Optional[int]:
        """Добавление нового достижения"""
        self.logger.debug(f"Adding achievement: name='{name}', desc='{description}', icon='{icon}', points={points}")
        
        insert_query = """
        INSERT INTO achievements (name, description, icon, points)
        VALUES (%s, %s, %s, %s)
        """
        
        try:
            # Выполняем вставку
            insert_result = self.db.execute_query(insert_query, (name, description, icon, points))
            self.logger.debug(f"Insert result: {insert_result}")
            
            # Получаем ID вставленной записи
            id_query = "SELECT LAST_INSERT_ID()"
            id_result = self.db.execute_query(id_query)
            self.logger.debug(f"LAST_INSERT_ID result: {id_result}")
            
            if id_result and id_result[0] and id_result[0][0]:
                achievement_id = id_result[0][0]
                self.logger.info(f"Successfully added achievement: {name} (ID: {achievement_id})")
                return achievement_id
            else:
                self.logger.error("Failed to get inserted achievement ID")
                return None
                
        except Exception as e:
            self.logger.error(f"Error adding achievement: {str(e)}")
            self.logger.error(f"Query: {insert_query}")
            self.logger.error(f"Parameters: name='{name}', desc='{description}', icon='{icon}', points={points}")
            return None

    def unlock_achievement(self, user_id: int, achievement_id: int) -> bool:
        """Разблокировка достижения для пользователя"""
        query = """
        INSERT IGNORE INTO user_achievements (user_id, achievement_id)
        VALUES (%s, %s)
        """
        try:
            self.db.execute_query(query, (user_id, achievement_id))
            self.logger.info(f"Unlocked achievement {achievement_id} for user {user_id}")
            return True
        except Exception as e:
            self.logger.error(f"Error unlocking achievement: {e}")
            return False

    def get_user_achievements(self, user_id: int) -> List[Dict]:
        """Получение списка достижений пользователя"""
        query = """
        SELECT a.*, ua.unlocked_at
        FROM achievements a
        JOIN user_achievements ua ON a.id = ua.achievement_id
        WHERE ua.user_id = %s
        ORDER BY ua.unlocked_at DESC
        """
        try:
            results = self.db.execute_query(query, (user_id,))
            achievements = []
            for row in results:
                achievements.append({
                    'id': row[0],
                    'name': row[1],
                    'description': row[2],
                    'icon': row[3],
                    'points': row[4],
                    'unlocked_at': row[5]
                })
            return achievements
        except Exception as e:
            self.logger.error(f"Error getting user achievements: {e}")
            return []

    def get_achievement_progress(self, user_id: int) -> Dict:
        """Получение прогресса достижений пользователя"""
        total_query = "SELECT COUNT(*) FROM achievements"
        unlocked_query = """
        SELECT COUNT(*) FROM user_achievements
        WHERE user_id = %s
        """
        try:
            total = self.db.execute_query(total_query)[0][0]
            unlocked = self.db.execute_query(unlocked_query, (user_id,))[0][0]
            return {
                'total': total,
                'unlocked': unlocked,
                'percentage': round((unlocked / total * 100) if total > 0 else 0, 2)
            }
        except Exception as e:
            self.logger.error(f"Error getting achievement progress: {e}")
            return {'total': 0, 'unlocked': 0, 'percentage': 0}

    def check_achievements(self, user_id: int, event: str, data: Dict = None):
        """Проверка и разблокировка достижений на основе событий"""
        if event == "game_start":
            self.unlock_achievement(user_id, 1)  # "Начало пути"
        elif event == "game_complete":
            self.unlock_achievement(user_id, 2)  # "Первое прохождение"
        elif event == "death":
            self.unlock_achievement(user_id, 3)  # "Смерть"
        elif event == "first_death":
            self.unlock_achievement(user_id, 4)  # "Первая смерть"