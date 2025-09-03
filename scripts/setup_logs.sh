#!/bin/bash

# 로그 디렉토리 설정 스크립트
# Docker 컨테이너 내부에서 로그 파일이 제대로 생성되도록 설정

echo "📁 Setting up log directories..."

# 로그 디렉토리 생성
mkdir -p /app/logs

# 권한 설정 (Docker 컨테이너 내부에서)
chmod 755 /app/logs

# 기존 로그 파일 백업
TIMESTAMP=$(date +%Y-%m-%d_%H-%M-%S);
LOG_DIR=/app/logs;
for LOG_FILE in $LOG_DIR/*.log; do
  if [ -f $LOG_FILE ]; then
    BACKUP_FILE=${LOG_FILE}.${TIMESTAMP}.bak;
    mv $LOG_FILE $BACKUP_FILE;
    echo "Backed up $LOG_FILE to $BACKUP_FILE";
  fi;
done;

# 로그 파일 초기화 (빈 파일 생성)
touch /app/logs/app.log
touch /app/logs/access.log
touch /app/logs/error.log

# 권한 설정
chmod 644 /app/logs/*.log

echo "✅ Log directories and files created successfully"
echo "📝 Log files location: /app/logs/"
ls -la /app/logs/
