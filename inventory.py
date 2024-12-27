import logging
from typing import Dict, List, Optional
from datetime import datetime
import json

class Item:
    def __init__(self, id: int, name: str, description: str, type: str, 
                 icon: str = None, properties: Dict = None):
        self.id = id
        self.name = name
        self.description = description
        self.type = type
        self.icon = icon or self._get_default_icon(type)
        self.properties = properties or {}
    
    def _get_default_icon(self, type: str) -> str:
        return {
            'weapon': '⚔️',
            'armor': '🛡️',
            'potion': '🧪',
            'key': '🔑',
            'quest': '📜'
        }.get(type, '📦')
    
    def to_dict(self) -> Dict:
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'type': self.type,
            'icon': self.icon,
            'properties': self.properties
        }

class InventoryManager:
    def __init__(self, db_manager):
        self.db = db_manager
        self.logger = logging.getLogger(__name__)
        self._init_items()

    def _init_items(self):
        """Инициализация базовых предметов"""
        basic_items = [
            {
                'name': 'Ржавый меч',
                'description': 'Старый, но все еще острый меч',
                'type': 'weapon',
                'properties': json.dumps({'damage': 5, 'durability': 100})
            },
            {
                'name': 'Кожаная броня',
                'description': 'Простая, но надежная защита',
                'type': 'armor',
                'properties': json.dumps({'defense': 3, 'weight': 5})
            },
            {
                'name': 'Зелье лечения',
                'description': 'Восстанавливает здоровье',
                'type': 'potion',
                'properties': json.dumps({'heal': 20, 'instant': True})
            }
        ]
        
        for item in basic_items:
            query = """
            INSERT IGNORE INTO items (name, description, type, properties)
            VALUES (%s, %s, %s, %s)
            """
            self.db.execute_query(query, (
                item['name'], 
                item['description'], 
                item['type'], 
                item['properties']
            ))

    def add_item(self, user_id: int, item_id: int, quantity: int = 1) -> bool:
        """Добавление предмета в инвентарь"""
        try:
            query = """
            INSERT INTO inventory (user_id, item_id, quantity)
            VALUES (%s, %s, %s)
            ON DUPLICATE KEY UPDATE quantity = quantity + VALUES(quantity)
            """
            self.db.execute_query(query, (user_id, item_id, quantity))
            self.logger.info(f"Added {quantity} of item {item_id} to user {user_id}")
            return True
        except Exception as e:
            self.logger.error(f"Error adding item: {e}")
            return False

    def remove_item(self, user_id: int, item_id: int, quantity: int = 1) -> bool:
        """Удаление предмета из инвентаря"""
        try:
            # Проверяем текущее количество
            check_query = """
            SELECT quantity FROM inventory
            WHERE user_id = %s AND item_id = %s
            """
            result = self.db.execute_query(check_query, (user_id, item_id))
            
            if not result:
                return False
                
            current_quantity = result[0][0]
            if current_quantity < quantity:
                return False
            
            if current_quantity == quantity:
                delete_query = """
                DELETE FROM inventory
                WHERE user_id = %s AND item_id = %s
                """
                self.db.execute_query(delete_query, (user_id, item_id))
            else:
                update_query = """
                UPDATE inventory
                SET quantity = quantity - %s
                WHERE user_id = %s AND item_id = %s
                """
                self.db.execute_query(update_query, (quantity, user_id, item_id))
            
            self.logger.info(f"Removed {quantity} of item {item_id} from user {user_id}")
            return True
        except Exception as e:
            self.logger.error(f"Error removing item: {e}")
            return False

    def get_inventory(self, user_id: int) -> List[Dict]:
        """Получение инвентаря пользователя"""
        query = """
        SELECT i.*, inv.quantity, inv.obtained_at
        FROM inventory inv
        JOIN items i ON inv.item_id = i.id
        WHERE inv.user_id = %s
        ORDER BY i.type, i.name
        """
        try:
            results = self.db.execute_query(query, (user_id,))
            inventory = []
            for row in results:
                item = Item(
                    id=row[0],
                    name=row[1],
                    description=row[2],
                    type=row[3],
                    icon=row[4],
                    properties=json.loads(row[5]) if row[5] else {}
                )
                inventory.append({
                    'item': item.to_dict(),
                    'quantity': row[6],
                    'obtained_at': row[7]
                })
            return inventory
        except Exception as e:
            self.logger.error(f"Error getting inventory: {e}")
            return []

    def get_item(self, item_id: int) -> Optional[Item]:
        """Получение информации о предмете"""
        query = "SELECT * FROM items WHERE id = %s"
        try:
            result = self.db.execute_query(query, (item_id,))
            if result:
                row = result[0]
                return Item(
                    id=row[0],
                    name=row[1],
                    description=row[2],
                    type=row[3],
                    icon=row[4],
                    properties=json.loads(row[5]) if row[5] else {}
                )
            return None
        except Exception as e:
            self.logger.error(f"Error getting item: {e}")
            return None

    def has_item(self, user_id: int, item_id: int, quantity: int = 1) -> bool:
        """Проверка наличия предмета у пользователя"""
        query = """
        SELECT quantity FROM inventory
        WHERE user_id = %s AND item_id = %s
        """
        try:
            result = self.db.execute_query(query, (user_id, item_id))
            return result and result[0][0] >= quantity
        except Exception as e:
            self.logger.error(f"Error checking item: {e}")
            return False