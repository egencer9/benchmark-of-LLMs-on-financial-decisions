#!/bin/bash
# =============================================
# LLM BENCHMARK - STOP SCRIPT
# start.sh ile başlatılan sunucuları durdurur.
# Kullanım: bash stop.sh
# =============================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PID_DIR="$SCRIPT_DIR/logs/pids"

API_PID_FILE="$PID_DIR/api.pid"
FRONTEND_PID_FILE="$PID_DIR/frontend.pid"

stop_process() {
    local name="$1"
    local pid_file="$2"

    if [ -f "$pid_file" ]; then
        local pid
        pid=$(cat "$pid_file")
        if kill -0 "$pid" 2>/dev/null; then
            kill "$pid"
            echo "🛑 $name durduruldu (PID: $pid)"
        else
            echo "ℹ️  $name zaten çalışmıyordu."
        fi
        rm -f "$pid_file"
    else
        echo "ℹ️  $name PID dosyası bulunamadı."
    fi
}

stop_process "API Sunucusu" "$API_PID_FILE"
stop_process "Frontend"     "$FRONTEND_PID_FILE"

echo ""
echo "✅ Tüm servisler durduruldu."
