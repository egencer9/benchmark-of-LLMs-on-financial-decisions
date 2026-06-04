#!/bin/bash
# =============================================
# LLM BENCHMARK - STARTUP SCRIPT
# Her iki sunucuyu terminal kapansa bile
# arka planda çalışır hale getirir.
# Kullanım: bash start.sh
# Durdurmak: bash stop.sh
# =============================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="$SCRIPT_DIR/logs"
PID_DIR="$SCRIPT_DIR/logs/pids"

mkdir -p "$LOG_DIR" "$PID_DIR"

API_PID_FILE="$PID_DIR/api.pid"
FRONTEND_PID_FILE="$PID_DIR/frontend.pid"

# --- Mevcut process'leri kontrol et ---
if [ -f "$API_PID_FILE" ] && kill -0 "$(cat "$API_PID_FILE")" 2>/dev/null; then
    echo "⚠️  API sunucusu zaten çalışıyor (PID: $(cat "$API_PID_FILE")). Durdurmak için bash stop.sh"
else
    echo "🚀 API sunucusu başlatılıyor (port 8000)..."
    nohup "$SCRIPT_DIR/venv/bin/python" "$SCRIPT_DIR/src/api.py" \
        > "$LOG_DIR/api_server.log" 2>&1 &
    echo $! > "$API_PID_FILE"
    echo "   ✅ API PID: $(cat "$API_PID_FILE") | Log: logs/api_server.log"
fi

if [ -f "$FRONTEND_PID_FILE" ] && kill -0 "$(cat "$FRONTEND_PID_FILE")" 2>/dev/null; then
    echo "⚠️  Frontend zaten çalışıyor (PID: $(cat "$FRONTEND_PID_FILE")). Durdurmak için bash stop.sh"
else
    echo "🚀 Frontend başlatılıyor (port 5173)..."
    nohup npm --prefix "$SCRIPT_DIR/frontend" run dev \
        > "$LOG_DIR/frontend.log" 2>&1 &
    echo $! > "$FRONTEND_PID_FILE"
    echo "   ✅ Frontend PID: $(cat "$FRONTEND_PID_FILE") | Log: logs/frontend.log"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  🌐 Uygulama: http://localhost:5173"
echo "  🔧 API:      http://localhost:8000"
echo "  📄 Loglar:   logs/api_server.log"
echo "               logs/frontend.log"
echo "  🛑 Durdurmak için: bash stop.sh"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
