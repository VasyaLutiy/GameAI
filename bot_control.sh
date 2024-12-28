#!/bin/bash

BOT_SCRIPT="bot.py"
PID_FILE="bot.pid"
LOG_FILE="bot.log"
PYTHONPATH="/workspace/test_simple"

start() {
    if [ -f "$PID_FILE" ]; then
        echo "Bot is already running (PID: $(cat $PID_FILE))"
    else
        echo "Starting bot..."
        PYTHONPATH=$PYTHONPATH python3 $BOT_SCRIPT > $LOG_FILE 2>&1 &
        echo $! > $PID_FILE
        echo "Bot started with PID: $(cat $PID_FILE)"
        echo "Use 'tail -f $LOG_FILE' to view logs"
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

status() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat $PID_FILE)
        if ps -p $PID > /dev/null; then
            echo "Bot is running (PID: $PID)"
            echo "Last 5 log entries:"
            tail -n 5 $LOG_FILE
        else
            echo "PID file exists but bot is not running. Cleaning up..."
            rm $PID_FILE
        fi
    else
        echo "Bot is not running"
    fi
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
    status)
        status
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|status}"
        exit 1
        ;;
esac