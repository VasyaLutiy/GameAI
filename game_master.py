import logging
import json
from typing import Optional, Dict
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from db_manager import DatabaseManager
from achievements import AchievementManager
from game_logic import GameLogic

class GameMaster:
    def __init__(self, db: DatabaseManager):
        self.db = db
        self.logger = logging.getLogger(__name__)
        self.achievement_manager = AchievementManager(db)
        self.game_logic = GameLogic(db)
        
        # Таблицы по умолчанию
        self.users_table = "users"
        self.scenes_table = "scenes"
        self.user_states_table = "user_states"

    async def get_current_scene(self, user_id: int) -> Optional[Dict]:
        """Получает текущую сцену для пользователя"""
        try:
            query = f"SELECT state FROM {self.user_states_table} WHERE user_id = %s"
            result = self.db.execute_query(query, (user_id,))
            
            if not result:
                return None
            
            scene_id = int(result[0][0])
            return self.game_logic.get_scene(scene_id)
        except Exception as e:
            self.logger.error(f"Error getting current scene: {e}")
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
            options = json.loads(scene['options']) if isinstance(scene['options'], str) else scene['options']
            for option_id, option_text in options.items():
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
        if scene and not scene.get('is_death_scene'):
            keyboard = []
            options = json.loads(scene['options']) if isinstance(scene['options'], str) else scene['options']
            for option_id, option_text in options.items():
                keyboard.append([InlineKeyboardButton(option_text, callback_data=f"choice_{option_id}")])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(
                f"🎮 Продолжаем игру...\n\n{scene['description']}", 
                reply_markup=reply_markup
            )
        else:
            await update.message.reply_text(
                "❌ Не найдено сохраненной игры или ваш персонаж погиб.\n"
                "Используйте /play чтобы начать новую игру."
            )

    async def cmd_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /status"""
        user_id = update.effective_user.id
        self.logger.info(f"User {user_id} requested status")
        
        scene = await self.get_current_scene(user_id)
        if scene:
            status_text = (
                "📊 Статус вашей игры:\n\n"
                f"🎯 Текущая сцена: {scene['id']}\n"
                f"📝 Описание: {scene['description'][:100]}...\n"
            )
            if scene.get('is_death_scene'):
                status_text += "\n💀 Ваш персонаж погиб. Используйте /play для новой игры."
            elif scene.get('npc_interaction'):
                status_text += f"\n👥 Текущее взаимодействие: {scene['npc_interaction']}"
            
            await update.message.reply_text(status_text)
        else:
            await update.message.reply_text(
                "❌ У вас нет активной игры.\n"
                "Используйте /play чтобы начать новую игру."
            )

    async def cmd_achievements(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /achievements"""
        user_id = update.effective_user.id
        self.logger.info(f"User {user_id} requested achievements")
        
        achievements = self.achievement_manager.get_user_achievements(user_id)
        progress = self.achievement_manager.get_achievement_progress(user_id)
        
        if achievements:
            message = "🏆 Ваши достижения:\n\n"
            for ach in achievements:
                # Преобразуем текстовые иконки в эмодзи
                icon = {
                    '[GAME]': '🎮',
                    '[MAP]': '🗺️',
                    '[SKULL]': '💀',
                    '[DEATH]': '☠️'
                }.get(ach['icon'], '•')
                
                message += f"{icon} {ach['name']} ({ach['points']} очков)\n"
                message += f"  ├ {ach['description']}\n"
                message += f"  └ Получено: {ach['unlocked_at'].strftime('%Y-%m-%d %H:%M')}\n\n"
            
            message += f"\n📊 Прогресс: {progress['unlocked']}/{progress['total']} ({progress['percentage']}%)"
        else:
            message = "У вас пока нет достижений. Играйте больше, чтобы получить их!"
        
        await update.message.reply_text(message)

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
            if not current_scene:
                await query.answer("❌ Ошибка: сцена не найдена")
                return

            success, message, new_scene = self.game_logic.process_choice(
                current_scene['id'], choice_id
            )
            
            if not success:
                await query.answer(message)
                return
            
            # Обновляем состояние пользователя
            update_query = f"""
            UPDATE {self.user_states_table} 
            SET state = %s 
            WHERE user_id = %s
            """
            self.db.execute_query(update_query, (new_scene['id'], user_id))
            
            # Проверяем специальные достижения
            if current_scene.get('npc_interaction'):
                self.achievement_manager.check_achievements(
                    user_id, 
                    "npc_interaction", 
                    {"npc": current_scene['npc_interaction']}
                )
            
            if new_scene.get('is_death_scene'):
                self.achievement_manager.check_achievements(user_id, "death")
            
            # Показываем новую сцену
            keyboard = []
            if not new_scene.get('is_death_scene') and new_scene.get('options'):
                options = json.loads(new_scene['options']) if isinstance(new_scene['options'], str) else new_scene['options']
                for option_id, option_text in options.items():
                    keyboard.append([InlineKeyboardButton(option_text, callback_data=f"choice_{option_id}")])
            
            reply_markup = InlineKeyboardMarkup(keyboard) if keyboard else None
            
            await query.answer()
            message_text = new_scene['description']
            if new_scene.get('is_death_scene'):
                message_text += "\n\n💀 Вы погибли. Используйте /play для новой игры."
                # Проверяем достижение за первую смерть
                self.achievement_manager.check_achievements(user_id, "first_death")
            
            await query.edit_message_text(
                text=message_text,
                reply_markup=reply_markup
            )
                
        except Exception as e:
            self.logger.error(f"Error handling choice: {e}")
            await query.answer("❌ Произошла ошибка при обработке выбора")