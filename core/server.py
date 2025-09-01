import os
import logging.config
import uvicorn
from dotenv import load_dotenv
from core.logging_config import LOGGING_CONFIG

logger = logging.getLogger(__name__)

class ServerRunner:
    """서버 실행을 담당하는 클래스"""
    
    def __init__(self):
        self.host = "0.0.0.0"
        self.port = 8000
        self.is_development = False
    
    def load_environment(self):
        """환경 변수 로드 및 설정"""
        load_dotenv()
        self.is_development = os.getenv("APP_ENV") == "development"
        port_env = os.getenv("PORT")
        if port_env:
            self.port = int(port_env)
    
    def get_reload_dirs(self):
        """개발 모드에서 감시할 디렉토리 목록"""
        return [
            "api", "config", "core", "routers", 
            "services", "flows", "tools", "utils"
        ]
    
    def get_reload_excludes(self):
        """개발 모드에서 제외할 디렉토리/파일 목록"""
        return [
            ".*", ".py[cod]", "__pycache__", ".env", 
            ".venv", ".git", "output", "gitsync"
        ]
    
    def run(self):
        """서버 실행"""
        self.load_environment()
        
        logging.config.dictConfig(LOGGING_CONFIG)
        
        logger.info(f"🚀 Starting server in {'development (hot-reload enabled)' if self.is_development else 'production'} mode.")
        logger.info(f"📍 Server will be available at http://{self.host}:{self.port}")
        
        uvicorn.run(
            "main:app",
            host=self.host,
            port=self.port,
            reload=self.is_development,
            reload_dirs=self.get_reload_dirs() if self.is_development else None,
            reload_excludes=self.get_reload_excludes() if self.is_development else None,
            access_log=True,
            log_config=LOGGING_CONFIG
        )

def run_server():
    """서버 실행 함수"""
    runner = ServerRunner()
    runner.run()

if __name__ == "__main__":
    run_server()