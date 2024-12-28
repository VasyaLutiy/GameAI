import asyncio
from datetime import datetime
import pytz
import logging
from database import get_db, get_active_reminders, mark_reminder_sent

logger = logging.getLogger(__name__)

class ReminderScheduler:
    def __init__(self, bot):
        self.bot = bot
        self.is_running = False
        self.check_interval = 30  # секунд
    
    async def start(self):
        """Запуск планировщика"""
        self.is_running = True
        while self.is_running:
            try:
                await self.check_reminders()
            except Exception as e:
                logger.error(f"Ошибка при проверке напоминаний: {e}")
            await asyncio.sleep(self.check_interval)
    
    async def stop(self):
        """Остановка планировщика"""
        self.is_running = False
    
    async def check_reminders(self):
        """Проверка и отправка напоминаний"""
        now = datetime.now(pytz.UTC)
        
        with get_db() as db:
            active_reminders = get_active_reminders(db, None)  # None для получения всех напоминаний
            
            for reminder in active_reminders:
                if reminder.datetime <= now and not reminder.reminder_sent:
                    try:
                        # Отправляем напоминание
                        await self.bot.send_message(
                            chat_id=reminder.telegram_chat_id,
                            text=f"🔔 Напоминание: {reminder.title}"
                        )
                        
                        # Отмечаем напоминание как отправленное
                        mark_reminder_sent(db, reminder.id)
                        logger.info(f"Отправлено напоминание {reminder.id} пользователю {reminder.user_id}")
                        
                    except Exception as e:
                        logger.error(f"Ошибка при отправке напоминания {reminder.id}: {e}")

async def setup_scheduler(application):
    """Настройка и запуск планировщика"""
    scheduler = ReminderScheduler(application.bot)
    asyncio.create_task(scheduler.start())
    return scheduler