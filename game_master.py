from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, CallbackQueryHandler, ContextTypes
from db_manager import DatabaseManager
import logging
import json

class GameMaster:
    def __init__(self, db: DatabaseManager):
        self.db = db
        self.logger = logging.getLogger(__name__)
        from achievements import AchievementManager
        self.achievement_manager = AchievementManager(db)

    async def get_current_scene(self, user_id: int) -> dict:
        """Получает текущую сцену для пользователя"""
        try:
            # Получаем текущее состояние пользователя
            query = "SELECT state FROM user_states WHERE user_id = %s"
            result = self.db.execute_query(query, (user_id,))
            
            if not result:
                # Если состояния нет, начинаем с первой сцены
                return self.get_scene(1)
            
            scene_id = int(result[0][0])
            return self.get_scene(scene_id)
        except Exception as e:
            self.logger.error(f"Error getting current scene: {e}")
            return None

    def get_scene(self, scene_id: int) -> dict:
        """Получает сцену по ID"""
        query = """
        SELECT id, parent, description, options 
        FROM scenes 
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
        query = """
        INSERT INTO user_states (user_id, state) 
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
        
        # Получаем текущую сцену пользователя
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
        
        # Получаем информацию о текущем прогрессе
        query = """
        SELECT us.state, s.description, u.created_at
        FROM user_states us
        JOIN users u ON u.user_id = us.user_id
        LEFT JOIN scenes s ON s.id = CAST(us.state AS SIGNED)
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
        
        # Удаляем текущее состояние игры
        query = "DELETE FROM user_states WHERE user_id = %s"
        result = self.db.execute_query(query, (user_id,))
        
        if result is not None:
            # Сохраняем информацию о сбросе в сессии
            session_query = """
            INSERT INTO user_sessions (user_id, session_key, session_value, expires_at)
            VALUES (%s, 'game_reset', 'Game reset by user', DATE_ADD(NOW(), INTERVAL 1 MONTH))
            """
            self.db.execute_query(session_query, (user_id,))
            
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
            # Получаем ID выбранной сцены из callback_data
            choice_id = int(query.data.split('_')[1])
            self.logger.info(f"User {user_id} made choice: {choice_id}")
            
            # Получаем текущую сцену перед обновлением
            current_scene = await self.get_current_scene(user_id)
            
            # Обновляем состояние пользователя
            update_query = """
            UPDATE user_states 
            SET state = %s 
            WHERE user_id = %s
            """
            self.db.execute_query(update_query, (choice_id, user_id))
            
            # Проверяем различные условия для достижений
            if current_scene:
                # Проверяем, является ли сцена "смертельной"
                if "death" in current_scene.get('description', '').lower():
                    self.achievement_manager.check_achievements(user_id, "death")
                
                # Проверяем завершение квеста
                if not current_scene.get('options'):
                    self.achievement_manager.check_achievements(user_id, "game_complete")
                
                # Проверяем исследование новых локаций
                self.achievement_manager.check_achievements(user_id, "explore_location", 
                    {"location_id": choice_id})
            
            # Получаем новую сцену
            new_scene = await self.get_current_scene(user_id)
            if new_scene:
                # Создаем клавиатуру с новыми опциями
                keyboard = []
                for option_id, option_text in new_scene['options'].items():
                    keyboard.append([InlineKeyboardButton(option_text, callback_data=f"choice_{option_id}")])
                
                reply_markup = InlineKeyboardMarkup(keyboard) if keyboard else None
                
                # Отвечаем на callback и обновляем сообщение
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