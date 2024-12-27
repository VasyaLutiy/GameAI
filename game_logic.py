import random
import logging
from typing import Dict, List, Tuple, Optional
from db_manager import DatabaseManager

class GameLogic:
    def __init__(self, db: DatabaseManager):
        self.db = db
        self.logger = logging.getLogger(__name__)

    def get_scene(self, scene_id: int) -> Optional[Dict]:
        """Получает сцену по ID с дополнительной информацией"""
        query = """
        SELECT id, description, options, is_death_scene, correct_path, 
               step_number, parent_choice, npc_interaction
        FROM scenes 
        WHERE id = %s
        """
        result = self.db.execute_query(query, (scene_id,))
        if not result:
            return None
        
        scene_data = result[0]
        return {
            'id': scene_data[0],
            'description': scene_data[1],
            'options': scene_data[2],
            'is_death_scene': bool(scene_data[3]),
            'correct_path': bool(scene_data[4]),
            'step_number': scene_data[5],
            'parent_choice': scene_data[6],
            'npc_interaction': scene_data[7]
        }

    def get_next_scenes(self, current_scene_id: int) -> List[Dict]:
        """Получает все возможные следующие сцены"""
        query = """
        SELECT id, description, options, is_death_scene, correct_path
        FROM scenes 
        WHERE parent = %s
        ORDER BY id
        """
        result = self.db.execute_query(query, (current_scene_id,))
        if not result:
            return []
        
        return [{
            'id': row[0],
            'description': row[1],
            'options': row[2],
            'is_death_scene': bool(row[3]),
            'correct_path': bool(row[4])
        } for row in result]

    def process_choice(self, scene_id: int, choice: int) -> Tuple[bool, str, Dict]:
        """Обрабатывает выбор игрока"""
        current_scene = self.get_scene(scene_id)
        if not current_scene:
            return False, "Сцена не найдена", {}

        if current_scene['is_death_scene']:
            return False, "Это конец пути", {}

        next_scenes = self.get_next_scenes(scene_id)
        if not next_scenes:
            return False, "Нет доступных вариантов", {}

        # Находим сцену, соответствующую выбору
        query = """
        SELECT id, description, options, is_death_scene, correct_path
        FROM scenes 
        WHERE parent = %s AND choice = %s
        """
        self.logger.debug(f"Processing choice {choice} for scene {scene_id}")
        result = self.db.execute_query(query, (scene_id, choice))
        if not result:
            self.logger.error(f"No scene found for parent={scene_id} and choice={choice}")
            return False, "Недопустимый выбор", {}
        self.logger.debug(f"Found scene: {result[0]}")

        chosen_scene = {
            'id': result[0][0],
            'description': result[0][1],
            'options': result[0][2],
            'is_death_scene': bool(result[0][3]),
            'correct_path': bool(result[0][4])
        }

        return True, "", chosen_scene

    def get_random_correct_choice(self) -> int:
        """Генерирует случайный правильный выбор (1-5)"""
        return random.randint(1, 5)

    def create_new_scene(self, step_number: int, parent_id: int, 
                        description: str, options: Dict[str, str], 
                        is_death_scene: bool = False, 
                        correct_path: bool = False,
                        parent_choice: int = None,
                        npc_interaction: str = None) -> int:
        """Создает новую сцену"""
        query = """
        INSERT INTO scenes (
            step_number, parent, description, options, 
            is_death_scene, correct_path, parent_choice, 
            npc_interaction
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s
        )
        """
        self.db.execute_query(
            query, 
            (step_number, parent_id, description, 
             options, is_death_scene, correct_path,
             parent_choice, npc_interaction)
        )
        
        # Получаем ID созданной сцены
        result = self.db.execute_query(
            "SELECT LAST_INSERT_ID()"
        )
        return result[0][0] if result else None