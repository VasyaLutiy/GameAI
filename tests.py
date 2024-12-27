import pytest
import json
from unittest.mock import Mock, AsyncMock, patch
from telegram import Update, User, Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from db_manager import DatabaseManager
from game_master import GameMaster
from test_config import TEST_TABLE_PREFIX

# Переопределяем GameMaster для использования тестовых таблиц
class TestGameMaster(GameMaster):
    def __init__(self, db: DatabaseManager):
        super().__init__(db)
        self.users_table = f"{TEST_TABLE_PREFIX}users"
        self.scenes_table = f"{TEST_TABLE_PREFIX}scenes"
        self.user_states_table = f"{TEST_TABLE_PREFIX}user_states"

    async def get_current_scene(self, user_id: int) -> dict:
        """Получает текущую сцену для пользователя"""
        try:
            query = f"SELECT state FROM {self.user_states_table} WHERE user_id = %s"
            result = self.db.execute_query(query, (user_id,))
            
            if not result:
                return None
            
            scene_id = int(result[0][0])
            return self.get_scene(scene_id)
        except Exception as e:
            self.logger.error(f"Error getting current scene: {e}")
            return None

    def get_scene(self, scene_id: int) -> dict:
        """Получает сцену по ID"""
        query = f"""
        SELECT id, parent, description, options 
        FROM {self.scenes_table} 
        WHERE id = %s
        """
        result = self.db.execute_query(query, (scene_id,))
        if result:
            scene_data = result[0]
            return {
                'id': scene_data[0],
                'parent': scene_data[1],
                'description': scene_data[2],
                'options': json.loads(scene_data[3]) if scene_data[3] else {}
            }
        return None

    async def cmd_play(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /play"""
        user_id = update.effective_user.id
        self.logger.info(f"User {user_id} started new game")
        
        # Сбрасываем состояние пользователя на начальную сцену
        query = f"""
        INSERT INTO {self.user_states_table} (user_id, state) 
        VALUES (%s, '1')
        ON DUPLICATE KEY UPDATE state = '1'
        """
        self.db.execute_query(query, (user_id,))
        
        # Проверяем достижение за начало игры
        self.achievement_manager.check_achievements(user_id, "game_start")
        
        # Получаем и показываем первую сцену
        scene = await self.get_current_scene(user_id)
        if scene:
            keyboard = []
            for option_id, option_text in scene['options'].items():
                keyboard.append([InlineKeyboardButton(option_text, callback_data=f"choice_{option_id}")])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(
                f"🎮 Новая игра начинается!\n\n{scene['description']}", 
                reply_markup=reply_markup
            )
        else:
            await update.message.reply_text("❌ Ошибка при запуске игры. Попробуйте позже.")

    async def cmd_continue(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /continue"""
        user_id = update.effective_user.id
        self.logger.info(f"User {user_id} continues game")
        
        scene = await self.get_current_scene(user_id)
        if scene:
            keyboard = []
            for option_id, option_text in scene['options'].items():
                keyboard.append([InlineKeyboardButton(option_text, callback_data=f"choice_{option_id}")])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(
                f"🎮 Продолжаем игру...\n\n{scene['description']}", 
                reply_markup=reply_markup
            )
        else:
            await update.message.reply_text(
                "❌ Не найдено сохраненной игры. Используйте /play чтобы начать новую игру."
            )

    async def cmd_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /status"""
        user_id = update.effective_user.id
        self.logger.info(f"User {user_id} requested status")
        
        query = f"""
        SELECT us.state, s.description, u.created_at
        FROM {self.user_states_table} us
        JOIN {self.users_table} u ON u.user_id = us.user_id
        LEFT JOIN {self.scenes_table} s ON s.id = CAST(us.state AS SIGNED)
        WHERE us.user_id = %s
        """
        result = self.db.execute_query(query, (user_id,))
        
        if result and result[0][0]:
            scene_id, current_scene, start_date = result[0]
            status_text = (
                "📊 Статус вашей игры:\n\n"
                f"🎯 Текущая сцена: {scene_id}\n"
                f"📝 Описание: {current_scene[:100]}...\n"
                f"📅 Начало игры: {start_date.strftime('%Y-%m-%d %H:%M')}\n"
            )
            await update.message.reply_text(status_text)
        else:
            await update.message.reply_text(
                "❌ У вас нет активной игры.\n"
                "Используйте /play чтобы начать новую игру."
            )

    async def cmd_reset(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /reset"""
        user_id = update.effective_user.id
        self.logger.info(f"User {user_id} requested game reset")
        
        query = f"DELETE FROM {self.user_states_table} WHERE user_id = %s"
        result = self.db.execute_query(query, (user_id,))
        
        if result is not None:
            await update.message.reply_text(
                "🔄 Игра успешно сброшена!\n"
                "Используйте /play чтобы начать новую игру."
            )
        else:
            await update.message.reply_text(
                "❌ Произошла ошибка при сбросе игры.\n"
                "Пожалуйста, попробуйте позже."
            )

    async def handle_choice(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик выбора опции в игре"""
        query = update.callback_query
        user_id = query.from_user.id
        
        try:
            choice_id = int(query.data.split('_')[1])
            self.logger.info(f"User {user_id} made choice: {choice_id}")
            
            current_scene = await self.get_current_scene(user_id)
            
            update_query = f"""
            UPDATE {self.user_states_table} 
            SET state = %s 
            WHERE user_id = %s
            """
            self.db.execute_query(update_query, (choice_id, user_id))
            
            if current_scene:
                if "death" in current_scene.get('description', '').lower():
                    self.achievement_manager.check_achievements(user_id, "death")
                
                if not current_scene.get('options'):
                    self.achievement_manager.check_achievements(user_id, "game_complete")
                
                self.achievement_manager.check_achievements(user_id, "explore_location", 
                    {"location_id": choice_id})
            
            new_scene = await self.get_current_scene(user_id)
            if new_scene:
                keyboard = []
                for option_id, option_text in new_scene['options'].items():
                    keyboard.append([InlineKeyboardButton(option_text, callback_data=f"choice_{option_id}")])
                
                reply_markup = InlineKeyboardMarkup(keyboard) if keyboard else None
                
                await query.answer()
                await query.edit_message_text(
                    text=new_scene['description'],
                    reply_markup=reply_markup
                )
            else:
                await query.answer("❌ Ошибка при загрузке сцены")
                
        except Exception as e:
            self.logger.error(f"Error handling choice: {e}")
            await query.answer("❌ Произошла ошибка при обработке выбора")

@pytest.fixture
def db_manager():
    from test_config import DB_CONFIG
    db = DatabaseManager(DB_CONFIG)
    # Очищаем тестовые данные перед каждым тестом
    db.execute_query(f"DELETE FROM {TEST_TABLE_PREFIX}user_states WHERE user_id = 12345")
    db.execute_query(f"DELETE FROM {TEST_TABLE_PREFIX}users WHERE user_id = 12345")
    # Добавляем тестового пользователя
    db.execute_query(f"INSERT INTO {TEST_TABLE_PREFIX}users (user_id, username) VALUES (12345, 'test_user')")
    return db

@pytest.fixture
def game_master(db_manager):
    return TestGameMaster(db_manager)

@pytest.fixture
def mock_update():
    update = Mock(spec=Update)
    # Настройка effective_user
    update.effective_user = Mock(spec=User)
    update.effective_user.id = 12345
    
    # Настройка message
    update.message = Mock(spec=Message)
    update.message.reply_text = AsyncMock()
    
    # Настройка callback_query
    update.callback_query = Mock(spec=CallbackQuery)
    update.callback_query.from_user = Mock(spec=User)
    update.callback_query.from_user.id = 12345
    update.callback_query.answer = AsyncMock()
    update.callback_query.edit_message_text = AsyncMock()
    
    return update

@pytest.fixture
def context():
    return Mock(spec=ContextTypes.DEFAULT_TYPE)

@pytest.mark.asyncio
async def test_cmd_play_new_game(game_master, mock_update, context):
    """Тест начала новой игры"""
    await game_master.cmd_play(mock_update, context)
    
    # Проверяем, что состояние игрока установлено на начальную сцену
    query = f"SELECT state FROM {TEST_TABLE_PREFIX}user_states WHERE user_id = 12345"
    result = game_master.db.execute_query(query)
    assert result[0][0] == '1'
    
    # Проверяем, что сообщение было отправлено
    mock_update.message.reply_text.assert_called_once()
    assert "Новая игра начинается!" in mock_update.message.reply_text.call_args[0][0]

@pytest.mark.asyncio
async def test_cmd_continue_no_game(game_master, mock_update, context):
    """Тест продолжения игры когда нет сохранения"""
    # Убеждаемся, что нет сохраненного состояния
    db_query = f"DELETE FROM {TEST_TABLE_PREFIX}user_states WHERE user_id = 12345"
    game_master.db.execute_query(db_query)
    
    # Настраиваем мок
    mock_update.message.reply_text = AsyncMock()
    
    await game_master.cmd_continue(mock_update, context)
    
    mock_update.message.reply_text.assert_awaited_once()
    args = mock_update.message.reply_text.call_args[0][0]
    assert "Не найдено сохраненной игры" in args

@pytest.mark.asyncio
async def test_cmd_status_no_game(game_master, mock_update, context):
    """Тест проверки статуса когда нет активной игры"""
    await game_master.cmd_status(mock_update, context)
    
    mock_update.message.reply_text.assert_called_once()
    assert "У вас нет активной игры" in mock_update.message.reply_text.call_args[0][0]

@pytest.mark.asyncio
async def test_cmd_reset_game(game_master, mock_update, context):
    """Тест сброса игры"""
    # Сначала создаем игру
    await game_master.cmd_play(mock_update, context)
    
    # Затем сбрасываем
    mock_update.message.reset_mock()
    await game_master.cmd_reset(mock_update, context)
    
    # Проверяем, что состояние удалено
    query = f"SELECT state FROM {TEST_TABLE_PREFIX}user_states WHERE user_id = 12345"
    result = game_master.db.execute_query(query)
    assert len(result) == 0
    
    mock_update.message.reply_text.assert_called_once()
    assert "Игра успешно сброшена" in mock_update.message.reply_text.call_args[0][0]

@pytest.mark.asyncio
async def test_handle_choice(game_master, mock_update, context):
    """Тест обработки выбора в игре"""
    # Начинаем игру
    await game_master.cmd_play(mock_update, context)
    
    # Настраиваем моки для callback_query
    mock_update.callback_query.data = "choice_2"
    mock_update.callback_query.from_user = Mock()
    mock_update.callback_query.from_user.id = 12345
    mock_update.callback_query.answer = AsyncMock()
    mock_update.callback_query.edit_message_text = AsyncMock()
    
    await game_master.handle_choice(mock_update, context)
    
    # Проверяем, что состояние обновилось
    query = f"SELECT state FROM {TEST_TABLE_PREFIX}user_states WHERE user_id = 12345"
    result = game_master.db.execute_query(query)
    assert result[0][0] == '2'
    
    # Проверяем, что были вызваны методы callback_query
    mock_update.callback_query.answer.assert_called_once()
    mock_update.callback_query.edit_message_text.assert_called_once()

@pytest.mark.asyncio
async def test_get_current_scene_new_user(game_master):
    """Тест получения сцены для нового пользователя"""
    # Для нового пользователя без состояния должен возвращаться None
    scene = await game_master.get_current_scene(12345)
    assert scene is None

    # После создания состояния должна возвращаться первая сцена
    query = f"INSERT INTO {TEST_TABLE_PREFIX}user_states (user_id, state) VALUES (12345, '1')"
    game_master.db.execute_query(query)
    
    scene = await game_master.get_current_scene(12345)
    assert scene is not None
    assert scene['id'] == 1

@pytest.mark.asyncio
async def test_achievement_on_game_start(game_master, mock_update, context):
    """Тест получения достижения за начало игры"""
    with patch('achievements.AchievementManager.check_achievements') as mock_check:
        await game_master.cmd_play(mock_update, context)
        mock_check.assert_called_once_with(12345, "game_start")

@pytest.mark.asyncio
async def test_scene_options_format(game_master, mock_update, context):
    """Тест формата опций в сцене"""
    await game_master.cmd_play(mock_update, context)
    scene = await game_master.get_current_scene(12345)
    
    assert isinstance(scene['options'], dict)
    for option_id, option_text in scene['options'].items():
        assert isinstance(option_id, str)
        assert isinstance(option_text, str)

@pytest.mark.asyncio
async def test_invalid_choice(game_master, mock_update, context):
    """Тест обработки некорректного выбора"""
    await game_master.cmd_play(mock_update, context)
    
    # Симулируем некорректный выбор
    mock_update.callback_query.data = "invalid_choice"
    await game_master.handle_choice(mock_update, context)
    
    # Проверяем, что состояние не изменилось
    query = f"SELECT state FROM {TEST_TABLE_PREFIX}user_states WHERE user_id = 12345"
    result = game_master.db.execute_query(query)
    assert result[0][0] == '1'