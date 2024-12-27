import logging
import sys
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler
from db_manager import DatabaseManager
from game_master import GameMaster
from achievements import AchievementManager

# Инициализация базы данных, игрового мастера и менеджера достижений
db = DatabaseManager()
game_master = GameMaster(db)
achievement_manager = AchievementManager(db)

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Токен бота
TELEGRAM_TOKEN = "7559282389:AAF4FOrgAygx5Bdx8OHkyvMWuN-zeCbRzGs"

# Обработчик команды /start
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    logger.info(f"User {user.id} started the bot")
    
    # Сохраняем информацию о пользователе в базу данных
    insert_query = """
    INSERT INTO users (user_id, username, first_name, last_name)
    VALUES (%s, %s, %s, %s)
    ON DUPLICATE KEY UPDATE
    username = VALUES(username),
    first_name = VALUES(first_name),
    last_name = VALUES(last_name)
    """
    
    try:
        db.execute_query(insert_query, (user.id, user.username, user.first_name, user.last_name))
        logger.info(f"User {user.id} information saved to database")
        await update.message.reply_text(
            f"Привет, {user.first_name}! 👋\n\n"
            "Добро пожаловать в текстовый квест!\n"
            "Используйте /play чтобы начать игру или /help для списка команд."
        )
    except Exception as e:
        logger.error(f"Error saving user data: {e}")
        await update.message.reply_text("Привет! К сожалению, произошла ошибка при сохранении данных.")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info(f"User {update.effective_user.id} requested help")
    help_text = """
🎮 Текстовый квест - Команды:

/play - Начать новую игру
/continue - Продолжить текущую игру
/status - Показать ваш прогресс
/reset - Сбросить игру
/help - Показать это сообщение

📊 Достижения и инвентарь:
/achievements - Показать ваши достижения
/achprogress - Показать прогресс достижений
/inventory - Показать ваш инвентарь

Удачи в прохождении! 🍀
"""
    await update.message.reply_text(help_text)

# Прокси-функции для команд игры
async def play_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await game_master.cmd_play(update, context)

async def continue_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await game_master.cmd_continue(update, context)

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await game_master.cmd_status(update, context)

async def reset_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await game_master.cmd_reset(update, context)

async def inventory_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await game_master.cmd_inventory(update, context)

# Обработчик callback query для кнопок
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await game_master.handle_choice(update, context)

async def achievements_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать достижения пользователя"""
    await game_master.cmd_achievements(update, context)

async def achievement_progress_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать прогресс достижений"""
    user_id = update.effective_user.id
    logger.info(f"User {user_id} requested achievement progress")
    
    progress = achievement_manager.get_achievement_progress(user_id)
    message = f"📊 Прогресс достижений:\n\n"
    message += f"✅ Открыто: {progress['unlocked']} из {progress['total']}\n"
    message += f"📈 Прогресс: {progress['percentage']}%\n"
    
    if progress['percentage'] < 100:
        message += "\nПродолжайте играть, чтобы открыть больше достижений! 🎮"
    else:
        message += "\nПоздравляем! Вы открыли все достижения! 🎉"
    
    await update.message.reply_text(message)

def main():
    logger.info("Bot is starting...")
    
    # Создаем приложение
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    # Добавляем обработчики команд
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("play", play_command))
    application.add_handler(CommandHandler("continue", continue_command))
    application.add_handler(CommandHandler("status", status_command))
    application.add_handler(CommandHandler("reset", reset_command))
    
    # Добавляем обработчики достижений и инвентаря
    application.add_handler(CommandHandler("achievements", achievements_command))
    application.add_handler(CommandHandler("achprogress", achievement_progress_command))
    application.add_handler(CommandHandler("inventory", inventory_command))
    
    # Добавляем обработчик callback query для кнопок
    application.add_handler(CallbackQueryHandler(button_handler))

    # Запускаем бота
    logger.info("Bot is running...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()