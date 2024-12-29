import os
import logging
import signal
from datetime import datetime
import asyncio
import pytz
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from bot_logic import bot

# Настройка логирования
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# Инициализация Василисы с провайдером контекста на основе саммари
CONTEXT_PROVIDER = os.getenv("CONTEXT_PROVIDER", "summary")
bot.context_provider = CONTEXT_PROVIDER
logger.info(f"Инициализация Василисы с провайдером контекста: {CONTEXT_PROVIDER}")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    user = update.effective_user
    logger.info(f"Пользователь {user.id} ({user.full_name}) начал диалог")
    
    try:
        # Загружаем последний контекст для пользователя
        logger.info(f"Loading last context for user {user.id}")
        await bot.context_provider.load_last_context(user.id)
        
        # Получаем список доступных режимов и их описания
        import json
        with open('character_profiles.json', 'r', encoding='utf-8') as f:
            profiles = json.load(f)
        
        # Формируем список режимов
        modes_list = []
        for mode, profile in profiles.items():
            modes_list.append(f"• {mode} - {profile['name']}")
        modes_str = "\n".join(modes_list)
        
        welcome_message = (
            f'Здравствуйте, {user.first_name}! Я {bot.current_profile["name"]}, ваш виртуальный секретарь. '
            'Буду рада помочь вам в организации дел, планировании времени и решении '
            'повседневных задач.\n\n'
            'Используйте /mode для выбора моего характера:\n'
            f'{modes_str}\n\n'
            'Расскажите, что вас беспокоит?'
        )
        
        await update.message.reply_text(welcome_message)
        
    except Exception as e:
        logger.error(f"Error in start command: {e}", exc_info=True)
        await update.message.reply_text(
            f'Здравствуйте, {user.first_name}! Я ваш виртуальный секретарь. '
            'К сожалению, произошла ошибка при загрузке профилей. '
            'Но вы всё равно можете начать диалог со мной.'
        )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /help"""
    # Получаем список доступных режимов
    import json
    with open('character_profiles.json', 'r', encoding='utf-8') as f:
        profiles = json.load(f)
    modes = list(profiles.keys())
    modes_str = '/'.join(modes)
    
    help_text = (
        "🤖 Команды:\n"
        "/start - Начать диалог\n"
        "/help - Это сообщение\n"
        f"/mode [тип] - Сменить мой характер ({modes_str})\n"
        "/profile - Показать ваш профиль и настройки\n"
        "/summary - Показать краткое содержание диалога\n"
        "/stats - Показать статистику общения\n\n"
        "💫 Я могу помочь вам с:\n"
        "🔔 Напоминаниями - просто напишите:\n"
        "   \"Напомни в 15:30 про встречу\"\n"
        "   \"Напоминание на 9:00 принять лекарство\"\n"
        "📅 Организацией дня и планированием\n"
        "📝 Управлением задачами\n"
        "💼 Деловыми советами\n"
        "😌 Борьбой со стрессом\n"
        "🤝 Коммуникацией и встречами\n\n"
        "Просто напишите мне о своей задаче, и я помогу её решить!\n\n"
        "💡 Подсказки:\n"
        "• Я автоматически запоминаю информацию о вас из диалога\n"
        "• Каждые 5 сообщений я создаю саммари диалога\n"
        "• Используйте /summary для просмотра истории общения\n"
        "• Используйте /stats для просмотра статистики\n"
        "• Используйте /profile для просмотра вашего профиля"
    )
    await update.message.reply_text(help_text)

async def mode_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /mode для смены характера"""
    user = update.effective_user
    
    try:
        # Получаем список доступных режимов из файла
        import json
        with open('character_profiles.json', 'r', encoding='utf-8') as f:
            profiles = json.load(f)
        available_modes = list(profiles.keys())
        
        if not context.args:
            modes_str = ", ".join(available_modes)
            await update.effective_message.reply_text(
                f"Пожалуйста, укажите режим: /mode [тип]\n"
                f"Доступные типы: {modes_str}"
            )
            return
            
        mode = context.args[0].lower()
        if mode not in available_modes:
            modes_str = ", ".join(available_modes)
            await update.effective_message.reply_text(
                f"Ошибка: режим '{mode}' не найден.\n"
                f"Доступные режимы: {modes_str}"
            )
            return
            
        logger.info(f"Пользователь {user.id} меняет характер на: {mode}")
        
        # Сохраняем режим в базе данных
        from database import get_db, get_or_create_user
        with get_db() as db:
            db_user = get_or_create_user(
                db,
                telegram_id=user.id,
                username=user.username,
                first_name=user.first_name,
                last_name=user.last_name
            )
            db_user.character_mode = mode
            db.commit()
            logger.info(f"Сохранен character_mode={mode} для пользователя {user.id}")
        
        result = bot.switch_character(mode)
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
    logger.info("Received message update")
    user = update.effective_user
    message_text = update.message.text
    chat_id = update.message.chat_id
    
    logger.info(f"Message details: user_id={user.id}, username={user.username}, full_name={user.full_name}")
    logger.info(f"Message text: {message_text}")
    logger.info(f"Chat ID: {chat_id}")
    
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
        try:
            from database import get_db, save_dialog, get_or_create_user
            
            # Получаем или создаем пользователя и его режим
            with get_db() as db:
                db_user = get_or_create_user(
                    db,
                    telegram_id=user.id,
                    username=user.username,
                    first_name=user.first_name,
                    last_name=user.last_name
                )
                saved_mode = db_user.character_mode or 'default'
                user_id = db_user.id
                
                # Если это первое сообщение пользователя, загружаем контекст
                if len(db_user.chat_history) == 0:
                    logger.info(f"First message from user {user_id}, loading last context")
                    await bot.context_provider.load_last_context(user.id)
                
                # Анализируем сообщение на наличие личной информации
                import re
                msg_lower = message_text.lower()
                
                # Проверяем на имя
                name_patterns = [
                    r'меня зовут\s+([^\n.,!?]+)',
                    r'я\s+([^\n.,!?]+)',
                    r'имя\s+([^\n.,!?]+)'
                ]
                for pattern in name_patterns:
                    name_match = re.search(pattern, msg_lower)
                    if name_match:
                        name = name_match.group(1).strip()
                        if len(name) > 2 and not any(word in name for word in ['есть', 'был', 'буду']):
                            db_user.update_user_info('name', name)
                            logger.info(f"Сохранено имя пользователя: {name}")
                            break
                
                # Проверяем на возраст
                age_patterns = [
                    r'мне (\d+)\s*лет',
                    r'(\d+)\s*года?\s+рождения',
                    r'родился в (\d{4})',
                ]
                for pattern in age_patterns:
                    age_match = re.search(pattern, msg_lower)
                    if age_match:
                        age = age_match.group(1)
                        if pattern.endswith('рождения') or 'родился' in pattern:
                            try:
                                birth_year = int(age)
                                current_year = datetime.now().year
                                age = str(current_year - birth_year)
                            except:
                                continue
                        db_user.update_user_info('age', age)
                        logger.info(f"Сохранен возраст пользователя: {age}")
                        break
                
                # Проверяем на род занятий
                occupation_patterns = [
                    r'работаю\s+([^\n.,!?]+)',
                    r'занимаюсь\s+([^\n.,!?]+)',
                    r'я\s+([^\n.,!?]+(?:программист|разработчик|инженер|специалист|архитектор))',
                    r'моя профессия\s+([^\n.,!?]+)',
                    r'моя работа\s+([^\n.,!?]+)',
                ]
                for pattern in occupation_patterns:
                    occupation_match = re.search(pattern, msg_lower)
                    if occupation_match:
                        occupation = occupation_match.group(1).strip()
                        db_user.update_user_info('occupation', occupation)
                        logger.info(f"Сохранен род занятий: {occupation}")
                        break
                
                # Проверяем на интересы
                interest_patterns = [
                    r'увлекаюсь\s+([^\n.,!?]+)',
                    r'люблю\s+([^\n.,!?]+)',
                    r'интересуюсь\s+([^\n.,!?]+)',
                    r'схожу с ума от\s+([^\n.,!?]+)',
                ]
                for pattern in interest_patterns:
                    interest_match = re.search(pattern, msg_lower)
                    if interest_match:
                        interests = interest_match.group(1).strip()
                        db_user.update_user_info('interests', interests)
                        logger.info(f"Сохранены интересы пользователя: {interests}")
                        break
                
                db.commit()
            
            # Устанавливаем сохраненный режим
            if saved_mode != bot.character_mode:
                bot.switch_character(saved_mode)
                logger.info(f"Восстановлен character_mode={saved_mode} для пользователя {user.id}")
            
            # Получаем ответ от бота
            response = await bot.get_response(message_text, user_id=user.id)
            logger.info(f"Ответ для {user.id}: {response}")
            
            # Сохраняем диалог в новой сессии
            with get_db() as db:
                save_dialog(
                    db,
                    user_id=user_id,
                    message=message_text,
                    response=response,
                    character_mode=bot.character_mode
                )
                db.commit()
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

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /stats для просмотра статистики диалога"""
    user = update.effective_user
    logger.info(f"Пользователь {user.id} запросил статистику")
    
    try:
        from database import get_db, get_or_create_user
        with get_db() as db:
            db_user = get_or_create_user(
                db,
                telegram_id=user.id,
                username=user.username,
                first_name=user.first_name,
                last_name=user.last_name
            )
            
            # Собираем статистику
            total_messages = len(db_user.chat_history)
            summaries = len(db_user.summaries)
            modes_used = set(msg.character_mode for msg in db_user.chat_history)
            current_mode = db_user.character_mode or 'default'
            
            # Находим самый активный режим
            mode_counts = {}
            for msg in db_user.chat_history:
                mode_counts[msg.character_mode] = mode_counts.get(msg.character_mode, 0) + 1
            most_used_mode = max(mode_counts.items(), key=lambda x: x[1])[0] if mode_counts else current_mode
            
            # Форматируем ответ
            response = (
                "📊 Статистика диалога\n\n"
                f"💬 Всего сообщений: {total_messages}\n"
                f"📝 Создано саммари: {summaries}\n"
                f"🎭 Использовано режимов: {len(modes_used)}\n"
                f"👑 Любимый режим: {most_used_mode}\n"
                f"🎯 Текущий режим: {current_mode}\n"
            )
            
            # Добавляем информацию о последней активности
            if db_user.chat_history:
                last_msg = max(db_user.chat_history, key=lambda x: x.timestamp)
                last_time = last_msg.timestamp.strftime("%d.%m.%Y %H:%M")
                response += f"⏰ Последняя активность: {last_time}\n"
            
            await update.message.reply_text(response)
    except Exception as e:
        logger.error(f"Ошибка при получении статистики: {e}")
        await update.message.reply_text(
            "Произошла ошибка при получении статистики. Попробуйте позже."
        )

async def summary_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /summary для просмотра саммари диалога"""
    user = update.effective_user
    logger.info(f"Пользователь {user.id} запросил саммари")
    
    try:
        from database import get_db, get_or_create_user
        with get_db() as db:
            db_user = get_or_create_user(
                db,
                telegram_id=user.id,
                username=user.username,
                first_name=user.first_name,
                last_name=user.last_name
            )
            
            # Получаем все необходимые данные внутри сессии
            chat_history = list(db_user.chat_history)
            summaries = list(db_user.summaries)
            user_info = db_user.get_user_info()
            current_mode = db_user.character_mode or 'default'
            
            # Форматируем саммари для лучшей читаемости
            summary_parts = []
            
            # Добавляем информацию о пользователе
            summary_parts.append("👤 О пользователе:")
            if user_info:
                if 'name' in user_info:
                    summary_parts.append(f"• Имя: {user_info['name']}")
                if 'age' in user_info:
                    summary_parts.append(f"• Возраст: {user_info['age']}")
                if 'occupation' in user_info:
                    summary_parts.append(f"• Род занятий: {user_info['occupation']}")
            else:
                summary_parts.append("• Информация пока не указана")
            summary_parts.append("")
            
            # Добавляем статистику диалога
            summary_parts.append("📊 Статистика диалога:")
            summary_parts.append(f"• Всего сообщений: {len(chat_history)}")
            summary_parts.append(f"• Создано саммари: {len(summaries)}")
            
            # Добавляем информацию о режимах
            modes_used = set(msg.character_mode for msg in chat_history)
            summary_parts.append(f"• Использовано режимов: {len(modes_used)}")
            if modes_used:
                summary_parts.append(f"• Режимы: {', '.join(modes_used)}")
            summary_parts.append(f"• Текущий режим: {current_mode}")
            
            # Добавляем временные рамки
            if chat_history:
                first_msg = min(chat_history, key=lambda x: x.timestamp)
                last_msg = max(chat_history, key=lambda x: x.timestamp)
                summary_parts.append(f"• Первое сообщение: {first_msg.timestamp.strftime('%d.%m.%Y %H:%M')}")
                summary_parts.append(f"• Последнее сообщение: {last_msg.timestamp.strftime('%d.%m.%Y %H:%M')}")
            summary_parts.append("")
            
            # Добавляем последние сообщения
            if chat_history:
                summary_parts.append("📝 Последние сообщения:")
                recent_messages = chat_history[-5:]  # Берем последние 5 сообщений
                for msg in recent_messages:
                    summary_parts.append(f"[{msg.timestamp.strftime('%H:%M:%S')}] User: {msg.message}")
                    summary_parts.append(f"[{msg.timestamp.strftime('%H:%M:%S')}] Assistant ({msg.character_mode}): {msg.response}")
                    summary_parts.append("-" * 40)
            else:
                summary_parts.append("📝 История диалога пока пуста")
            
            response = "\n".join(summary_parts)
            await update.message.reply_text(response)
            
    except Exception as e:
        logger.error(f"Error in summary command: {e}", exc_info=True)
        logger.error("Stack trace:", exc_info=True)
        await update.message.reply_text(
            "Произошла ошибка при получении саммари. Попробуйте позже."
        )

async def profile_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /profile для просмотра профиля"""
    user = update.effective_user
    logger.info(f"Пользователь {user.id} запросил профиль")
    
    try:
        from database import get_db, get_or_create_user
        with get_db() as db:
            # Анализируем историю диалогов для обновления профиля
            await bot.context_provider.extract_user_profile_from_history(user.id)
            
            # Получаем пользователя в новой сессии после обновления профиля
            db_user = get_or_create_user(
                db,
                telegram_id=user.id,
                username=user.username,
                first_name=user.first_name,
                last_name=user.last_name
            )
            
            # Получаем всю необходимую информацию внутри сессии
            profile = db_user.get_user_profile()
            mode = db_user.character_mode or 'default'
            user_info = db_user.get_user_info()
            
            # Формируем расширенный ответ
            response_parts = [
                "👤 === Профиль пользователя ===",
                profile
            ]
            
            # Добавляем характер и стиль общения, если есть
            character_traits = user_info.get('character_traits', '').split(', ') if user_info.get('character_traits') else []
            communication_style = user_info.get('communication_style', '').split(', ') if user_info.get('communication_style') else []
            
            if character_traits or communication_style:
                response_parts.append("\n🎭 Характер и стиль общения:")
                if character_traits:
                    response_parts.append("• Черты характера: " + ", ".join(character_traits))
                if communication_style:
                    response_parts.append("• Стиль общения: " + ", ".join(communication_style))
            
            # Добавляем технические детали
            response_parts.extend([
                "\n⚙️ Технические детали:",
                f"• Текущий режим: {mode}",
                f"• Telegram ID: {user.id}",
                f"• Username: @{user.username}"
            ])
            
            # Отправляем ответ
            await update.message.reply_text("\n".join(response_parts))
            
    except Exception as e:
        logger.error(f"Ошибка при получении профиля: {e}")
        logger.error("Stack trace:", exc_info=True)
        await update.message.reply_text(
            "Произошла ошибка при получении профиля. Попробуйте позже."
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
        application.add_handler(CommandHandler("profile", profile_command))
        application.add_handler(CommandHandler("summary", summary_command))
        application.add_handler(CommandHandler("stats", stats_command))
        
        # Добавляем обработчик текстовых сообщений
        application.add_handler(MessageHandler(
            filters.TEXT & ~filters.COMMAND, 
            handle_message
        ))
        
        # Добавляем обработчик ошибок
        application.add_error_handler(error_handler)
        
        # Запускаем бота
        logger.info(f"Бот запущен и готов к работе. Текущий режим: {bot.character_mode}")
        application.run_polling(drop_pending_updates=True)
        
    except Exception as e:
        logger.error(f"Ошибка при запуске бота: {e}")
        raise e

if __name__ == "__main__":
    run_bot()
