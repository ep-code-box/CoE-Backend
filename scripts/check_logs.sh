#!/bin/bash

# 로그 파일 상태 확인 스크립트

echo "🔍 Checking log files status..."

# 로그 디렉토리 확인
if [ -d "/app/logs" ]; then
    echo "✅ Log directory exists: /app/logs"
    ls -la /app/logs/
else
    echo "❌ Log directory does not exist: /app/logs"
fi

# 개별 로그 파일 확인
log_files=("app.log" "access.log" "error.log")

for log_file in "${log_files[@]}"; do
    if [ -f "/app/logs/$log_file" ]; then
        size=$(du -h "/app/logs/$log_file" | cut -f1)
        echo "✅ $log_file exists (size: $size)"
    else
        echo "❌ $log_file does not exist"
    fi
done

# 최근 로그 내용 확인 (마지막 10줄)
echo ""
echo "📄 Recent log content (last 10 lines):"
if [ -f "/app/logs/app.log" ]; then
    echo "--- app.log ---"
    tail -10 /app/logs/app.log
fi

if [ -f "/app/logs/error.log" ]; then
    echo "--- error.log ---"
    tail -10 /app/logs/error.log
fi
