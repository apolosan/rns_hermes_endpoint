#!/usr/bin/env bash
# Hermes for Reticulum — background runner
# Usage: ./start.sh [stop|status|restart]

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="${PROJECT_DIR:-$SCRIPT_DIR}"
VENV="${VENV:-$PROJECT_DIR/venv}"
PIDFILE="${PIDFILE:-$PROJECT_DIR/.lxmf/reticulum.pid}"
LOGFILE="${LOGFILE:-$PROJECT_DIR/.lxmf/reticulum.log}"
ENVFILE="${ENVFILE:-$PROJECT_DIR/.env}"

start() {
    if [ -f "$PIDFILE" ] && kill -0 "$(cat "$PIDFILE")" 2>/dev/null; then
        echo "Already running (PID $(cat "$PIDFILE"))"
        return 0
    fi

    if [ ! -f "$ENVFILE" ]; then
        echo "Missing $ENVFILE — copy config/env.example to .env first"
        exit 1
    fi

    mkdir -p "$(dirname "$PIDFILE")" "$(dirname "$LOGFILE")"

    echo "Starting Hermes for Reticulum..."
    cd "$PROJECT_DIR"

    set -a
    # shellcheck source=/dev/null
    . "$ENVFILE"
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
