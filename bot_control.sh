#!/bin/bash

BOT_SCRIPT="telegram_bot.py"
PID_FILE="bot.pid"
LOG_FILE="bot.log"

start() {
    if [ -f "$PID_FILE" ]; then
        echo "Bot is already running (PID: $(cat $PID_FILE))"
    else
        echo "Starting bot..."
        python3 $BOT_SCRIPT > $LOG_FILE 2>&1 &
        echo $! > $PID_FILE
        echo "Bot started with PID: $(cat $PID_FILE)"
    fi
}

stop() {
    if [ -f "$PID_FILE" ]; then
        echo "Stopping bot..."
        kill $(cat $PID_FILE)
        rm $PID_FILE
        echo "Bot stopped"
    else
        echo "Bot is not running"
    fi
}

restart() {
    stop
    sleep 2
    start
}

case "$1" in
    start)
        start
        ;;
    stop)
        stop
        ;;
    restart)
        restart
        ;;
    *)
        echo "Usage: $0 {start|stop|restart}"
        exit 1
        ;;
esac