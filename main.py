"""
CoE Backend API Server
FastAPI 기반 AI 에이전트 백엔드 서버
"""
import logging.config
from core.logging_config import LOGGING_CONFIG
from core.app_factory import create_app
from core.server import run_server

# 로깅 설정 적용
logging.config.dictConfig(LOGGING_CONFIG)
logger = logging.getLogger(__name__)

# 애플리케이션 생성
logger.info("Creating FastAPI app...")
app = create_app()
logger.info("FastAPI app created successfully.")


if __name__ == "__main__":
    logger.info("Starting server...")
    run_server()