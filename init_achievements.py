import logging
from db_manager import DatabaseManager
from achievements import AchievementManager

# Настройка логирования
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def init_default_achievements():
    """Инициализация базовых достижений"""
    db = DatabaseManager()
    achievement_manager = AchievementManager(db)
    
    print("Connected to database")
    print("Initializing achievements table...")
    
    # Базовые достижения
    achievements = [
        {
            "name": "Начало пути",
            "description": "Начните свое первое приключение",
            "icon": "[*]",
            "points": 10
        },
        {
            "name": "Первое прохождение",
            "description": "Успешно завершите любой квест",
            "icon": "[#]",
            "points": 50
        },
        {
            "name": "Искатель приключений",
            "description": "Исследуйте 5 разных локаций",
            "icon": "[M]",
            "points": 25
        },
        {
            "name": "Храбрая душа",
            "description": "Переживите свою первую игровую смерть",
            "icon": "[X]",
            "points": 15
        },
        {
            "name": "Мастер диалога",
            "description": "Откройте все варианты диалога в одной сцене",
            "icon": "[T]",
            "points": 20
        },
        {
            "name": "Коллекционер",
            "description": "Соберите все предметы в одном квесте",
            "icon": "[B]",
            "points": 30
        },
        {
            "name": "Первооткрыватель",
            "description": "Найдите секретную локацию",
            "icon": "[?]",
            "points": 40
        },
        {
            "name": "Стратег",
            "description": "Примите 10 разных решений в одном прохождении",
            "icon": "[!]",
            "points": 35
        },
        {
            "name": "Легенда",
            "description": "Завершите все доступные квесты",
            "icon": "[L]",
            "points": 100
        },
        {
            "name": "Спидраннер",
            "description": "Пройдите квест менее чем за 5 минут",
            "icon": "[S]",
            "points": 45
        }
    ]
    
    # Добавление достижений в базу данных
    print("\nДобавление достижений:")
    for achievement in achievements:
        print(f"\nДобавление достижения '{achievement['name']}'...")
        achievement_id = achievement_manager.add_achievement(
            name=achievement["name"],
            description=achievement["description"],
            icon=achievement["icon"],
            points=achievement["points"]
        )
        if achievement_id:
            print(f"✓ Успешно добавлено достижение ID:{achievement_id}")
        else:
            print(f"✗ Ошибка при добавлении достижения '{achievement['name']}'")

    print("\nПроверка добавленных достижений...")
    query = "SELECT id, name, icon, points FROM achievements ORDER BY id;"
    results = db.execute_query(query)
    if results:
        print("\nСписок достижений в базе данных:")
        for row in results:
            print(f"ID:{row[0]} | {row[2]} {row[1]} ({row[3]} очков)")
    else:
        print("✗ Ошибка при получении списка достижений")

if __name__ == "__main__":
    print("=== Инициализация достижений ===")
    init_default_achievements()
    print("\n=== Инициализация завершена ===")