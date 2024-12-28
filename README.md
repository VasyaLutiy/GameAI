# Василиса - Telegram бот-ассистент

Многофункциональный Telegram бот с различными характерами и системой напоминаний.

## Возможности

- 🎭 Разные характеры общения:
  - Default - традиционная Василиса
  - Cyber - Василиса.exe в стиле киберпанк
  - Sassy - дерзкая Василиса

- ⏰ Система напоминаний:
  - Создание напоминаний в естественной форме
  - Просмотр списка активных напоминаний
  - Автоматические уведомления

## Установка и запуск

1. Клонировать репозиторий:
```bash
git clone [URL репозитория]
cd [имя папки]
```

2. Установить зависимости:
```bash
pip install -r requirements.txt
```

3. Создать файл конфигурации `character_profiles.json`

4. Запустить бота:
```bash
./bot_control.sh start
```

## Использование

- `/start` - Начать диалог
- `/help` - Показать справку
- `/mode [тип]` - Сменить характер (default/cyber/sassy)
- Создать напоминание: "Напомни в 15:30 про встречу"
- Просмотреть напоминания: "мои напоминания"

## Управление ботом

Используйте скрипт `bot_control.sh`:
- `./bot_control.sh start` - Запустить бота
- `./bot_control.sh stop` - Остановить бота
- `./bot_control.sh restart` - Перезапустить бота
- `./bot_control.sh status` - Проверить статус

## Лицензия

MIT