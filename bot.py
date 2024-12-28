import os
import logging
import signal
from datetime import datetime
import asyncio
import pytz
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from test_vasilia import VasilisaLLM

# Настройка логирования
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# Инициализация Василисы с выбранным провайдером контекста
# Можно изменить на "vector" когда будет реализован векторный провайдер
CONTEXT_PROVIDER = os.getenv("CONTEXT_PROVIDER", "simple_json")
vasilia = VasilisaLLM(context_provider=CONTEXT_PROVIDER)
logger.info(f"Инициализация Василисы с провайдером контекста: {CONTEXT_PROVIDER}")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    user = update.effective_user
    logger.info(f"Пользователь {user.id} ({user.full_name}) начал диалог")
    
    welcome_message = (
        f'Здравствуйте, {user.first_name}! Я {vasilia.current_profile["name"]}, ваш виртуальный секретарь. '
        'Буду рада помочь вам в организации дел, планировании времени и решении '
        'повседневных задач.\n\n'
        'Используйте /mode для выбора моего характера:\n'
        '• default - традиционная Василиса\n'
        '• cyber - Василиса.exe в стиле киберпанк\n'
        '• sassy - дерзкая Василиса\n\n'
        'Расскажите, что вас беспокоит?'
    )
    
    await update.message.reply_text(welcome_message)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /help"""
    help_text = (
        "🤖 Команды:\n"
        "/start - Начать диалог\n"
        "/help - Это сообщение\n"
        "/mode [тип] - Сменить мой характер (default/cyber/sassy)\n\n"
        "💫 Я могу помочь вам с:\n"
        "🔔 Напоминаниями - просто напишите:\n"
        "   \"Напомни в 15:30 про встречу\"\n"
        "   \"Напоминание на 9:00 принять лекарство\"\n"
        "📅 Организацией дня и планированием\n"
        "📝 Управлением задачами\n"
        "💼 Деловыми советами\n"
        "😌 Борьбой со стрессом\n"
        "🤝 Коммуникацией и встречами\n\n"
        "Просто напишите мне о своей задаче, и я помогу её решить!"
    )
    await update.message.reply_text(help_text)

async def mode_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /mode для смены характера"""
    user = update.effective_user
    
    try:
        if not context.args:
            available_modes = ", ".join(vasilia.character_profiles.keys())
            await update.effective_message.reply_text(
                f"Пожалуйста, укажите режим: /mode [тип]\n"
                f"Доступные типы: {available_modes}"
            )
            return
            
        mode = context.args[0].lower()
        logger.info(f"Пользователь {user.id} меняет характер на: {mode}")
        
        result = vasilia.switch_character(mode)
        await update.effective_message.reply_text(result)
    except Exception as e:
        logger.error(f"Ошибка при смене режима: {e}")
        await update.effective_message.reply_text(
            "Произошла ошибка при смене режима. Пожалуйста, попробуйте еще раз."
        )

async def show_reminders(telegram_id: int, chat_id: int) -> str:
    """Получает список активных напоминаний пользователя"""
    from database import get_db, get_active_reminders, get_or_create_user
    
    try:
        with get_db() as db:
            # Получаем или создаем пользователя
            db_user = get_or_create_user(db, telegram_id=telegram_id)
            logger.info(f"Checking reminders for user_id={db_user.id} (telegram_id={telegram_id})")
            reminders = get_active_reminders(db, db_user.id)
            logger.info(f"Found {len(reminders)} active reminders")
            if not reminders:
                return "У вас пока нет активных напоминаний."
            
            response = "📅 Ваши активные напоминания:\n\n"
            for reminder in reminders:
                # Форматируем дату в удобный вид
                formatted_time = reminder.datetime.astimezone(pytz.timezone('Europe/Moscow')).strftime("%d.%m.%Y %H:%M")
                response += f"• {formatted_time}: {reminder.title}\n"
            return response
    except Exception as e:
        logger.error(f"Ошибка при получении напоминаний: {e}")
        return "Произошла ошибка при получении списка напоминаний."

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик текстовых сообщений"""
    user = update.effective_user
    message_text = update.message.text
    chat_id = update.message.chat_id
    
    logger.info(f"Сообщение от {user.id} ({user.full_name}): {message_text}")
    
    try:
        # Проверяем запрос на просмотр напоминаний
        if any(phrase in message_text.lower() for phrase in ["покажи напоминания", "мои напоминания", "список напоминаний"]):
            logger.info(f"User {user.id} requested reminders list")
            try:
                response = await show_reminders(user.id, chat_id)
                logger.info(f"Response for reminders: {response}")
                await update.message.reply_text(response)
            except Exception as e:
                logger.error(f"Error showing reminders: {str(e)}", exc_info=True)
                await update.message.reply_text("Произошла ошибка при получении списка напоминаний. Попробуйте позже.")
            return
            
        # Проверяем на команду создания напоминания
        if "напомни" in message_text.lower() or "напоминание" in message_text.lower():
            logger.info("Обрабатываем запрос на создание напоминания")
            # Пытаемся извлечь время из сообщения
            import re
            from datetime import datetime, timedelta
            import pytz
            
            # Ищем время в формате ЧЧ:ММ
            time_match = re.search(r"(\d{1,2})[:-](\d{2})", message_text)
            if time_match:
                hours, minutes = map(int, time_match.groups())
                logger.info(f"Найдено время: {hours}:{minutes}")
                
                # Проверяем корректность времени
                if not (0 <= hours <= 23 and 0 <= minutes <= 59):
                    await update.message.reply_text(
                        "Пожалуйста, укажите корректное время в формате ЧЧ:ММ (например, 15:30)"
                    )
                    return
                
                # Создаем дату напоминания
                now = datetime.now(pytz.timezone("Europe/Moscow"))
                reminder_time = now.replace(hour=hours, minute=minutes, second=0, microsecond=0)
                
                # Если время уже прошло, добавляем день
                if reminder_time <= now:
                    reminder_time += timedelta(days=1)
                    
                logger.info(f"Установлено время напоминания на: {reminder_time}")
                
                # Извлекаем текст напоминания
                title = message_text.lower()
                patterns = [
                    "напомни в", "напоминание на", "напомни", "напоминание",
                    f"{hours}:{minutes:02d}", f"{hours}:{minutes}",
                    "в ", "на "
                ]
                for pattern in patterns:
                    title = title.replace(pattern.lower(), "").strip()
                
                # Восстанавливаем первую букву заглавной
                if title:
                    title = title[0].upper() + title[1:] if len(title) > 1 else title.upper()
                    
                    try:
                        # Создаем напоминание в базе данных
                        from database import get_db, get_or_create_user, create_reminder
                        with get_db() as db:
                            db_user = get_or_create_user(
                                db, 
                                telegram_id=user.id,
                                username=user.username,
                                first_name=user.first_name,
                                last_name=user.last_name
                            )
                            reminder = create_reminder(
                                db,
                                user_id=db_user.id,
                                chat_id=chat_id,
                                title=title,
                                reminder_time=reminder_time
                            )
                            
                            response = f"✅ Хорошо, я напомню вам о \"{title}\" в {reminder.formatted_datetime}"
                            logger.info(f"Создано напоминание для {user.id}: {response}")
                            await update.message.reply_text(response)
                            return
                    except Exception as e:
                        logger.error(f"Ошибка при создании напоминания: {e}")
                        await update.message.reply_text(
                            "Извините, произошла ошибка при создании напоминания. Попробуйте еще раз."
                        )
                        return
                else:
                    await update.message.reply_text(
                        "Пожалуйста, укажите текст напоминания. Например: \"Напомни в 15:30 про встречу\""
                    )
                    return
            else:
                await update.message.reply_text(
                    "Пожалуйста, укажите время в формате ЧЧ:ММ, например:\n"
                    "\"Напомни в 15:30 про встречу\""
                )
                return
        
        # Если это не напоминание, обрабатываем как обычное сообщение
        response = await vasilia.get_response(message_text)
        logger.info(f"Ответ для {user.id}: {response}")
        
        # Сохраняем диалог в историю
        try:
            with get_db() as db:
                save_dialog(
                    db,
                    user_id=user.id,
                    message=message_text,
                    response=response,
                    character_mode=vasilia.character_mode
                )
                logger.info(f"Диалог сохранен для пользователя {user.id}")
        except Exception as e:
            logger.error(f"Ошибка при сохранении диалога: {e}")
        
        await update.message.reply_text(response)
        
    except Exception as e:
        error_message = f"Произошла ошибка: {str(e)}"
        logger.error(f"Ошибка при обработке сообщения от {user.id}: {str(e)}")
        await update.message.reply_text(
            "Прошу прощения, что-то пошло не так. Давайте попробуем ещё раз?"
        )

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик ошибок"""
    logger.error(f"Ошибка при обработке обновления {update}: {context.error}")

def run_bot():
    """Запуск бота"""
    token = "7559282389:AAF4FOrgAygx5Bdx8OHkyvMWuN-zeCbRzGs"
    
    logger.info("Запуск бота...")
    
    try:
        # Инициализируем базу данных
        from database import init_db
        init_db()
        logger.info("База данных инициализирована")
        
        # Создаем приложение
        application = (
            Application.builder()
            .token(token)
            .read_timeout(30)
            .write_timeout(30)
            .connect_timeout(30)
            .pool_timeout(30)
            .build()
        )
        
        # Добавляем обработчики команд
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(CommandHandler("mode", mode_command))
        
        # Добавляем обработчик текстовых сообщений
        application.add_handler(MessageHandler(
            filters.TEXT & ~filters.COMMAND, 
            handle_message
        ))
        
        # Добавляем обработчик ошибок
        application.add_error_handler(error_handler)
        
        # Запускаем бота
        logger.info(f"Бот запущен и готов к работе. Текущий режим: {vasilia.character_mode}")
        
        application.run_polling(drop_pending_updates=True)
        
    except Exception as e:
        logger.error(f"Ошибка при запуске бота: {e}")
        raise e

if __name__ == "__main__":
    run_bot()
