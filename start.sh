#!/bin/bash
# Hermes for Reticulum — background runner
# Usage: ./start.sh [stop|status]

PROJECT_DIR="/opt/data/rns_hermes_endpoint"
VENV="$PROJECT_DIR/venv"
PIDFILE="/opt/data/.lxmf/reticulum.pid"
LOGFILE="/opt/data/.lxmf/reticulum.log"
ENVFILE="$PROJECT_DIR/.env"

start() {
    if [ -f "$PIDFILE" ] && kill -0 "$(cat "$PIDFILE")" 2>/dev/null; then
        echo "Already running (PID $(cat "$PIDFILE"))"
        return 0
    fi

    echo "Starting Hermes for Reticulum..."
    cd "$PROJECT_DIR"

    # Source env and ensure HOME is correct for Reticulum config lookup
    set -a
    . "$ENVFILE"
    HOME=/opt/data
    export HOME
    set +a

    nohup "$VENV/bin/hermes-reticulum" run \
        >> "$LOGFILE" 2>&1 &
    echo $! > "$PIDFILE"
    echo "Started (PID $!). Log: $LOGFILE"
}

stop() {
    if [ ! -f "$PIDFILE" ]; then
        echo "Not running"
        return 0
    fi

    PID=$(cat "$PIDFILE")
    if kill -0 "$PID" 2>/dev/null; then
        echo "Stopping PID $PID..."
        kill "$PID"
        sleep 2
        kill -0 "$PID" 2>/dev/null && kill -9 "$PID"
        echo "Stopped"
    else
        echo "Process $PID not running"
    fi
    rm -f "$PIDFILE"
}

status() {
    if [ -f "$PIDFILE" ] && kill -0 "$(cat "$PIDFILE")" 2>/dev/null; then
        echo "Running (PID $(cat "$PIDFILE"))"
        tail -5 "$LOGFILE" 2>/dev/null
    else
        echo "Not running"
    fi
}

case "${1:-start}" in
    start)  start ;;
    stop)   stop ;;
    status) status ;;
    restart) stop; sleep 1; start ;;
    *) echo "Usage: $0 {start|stop|status|restart}" ;;
esac
