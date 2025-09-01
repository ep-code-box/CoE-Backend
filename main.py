"""
CoE Backend API Server
FastAPI 기반 AI 에이전트 백엔드 서버
"""

import logging
import logging.handlers
import os
from pathlib import Path

# 로깅 설정을 먼저 구성
def setup_logging():
    """로깅 설정을 구성합니다."""
    log_dir = "/app/logs" if os.path.exists("/app/logs") else "./logs"
    Path(log_dir).mkdir(parents=True, exist_ok=True)
    
    # 루트 로거 설정
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    
    # 파일 핸들러 추가
    file_handler = logging.handlers.RotatingFileHandler(
        f"{log_dir}/app.log",
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.INFO)
    
    # 포맷터 설정
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(formatter)
    
    # 핸들러 추가
    root_logger.addHandler(file_handler)
    
    # 시작 로그 기록
    logging.info("=== CoE Backend Starting ===")
    logging.info(f"Log directory: {log_dir}")

# 로깅 설정
setup_logging()

from core.app_factory import create_app

# 애플리케이션 생성
app = create_app()

if __name__ == "__main__":
    from core.server import run_server
    run_server()
