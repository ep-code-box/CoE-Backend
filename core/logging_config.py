
# Uvicorn's default format for access logs, with slight modification for clarity
# See: https://github.com/encode/uvicorn/blob/master/uvicorn/logging.py
ACCESS_LOG_FORMAT = '%(levelname)s: %(asctime)s - %(client_addr)s - "%(request_line)s" %(status_code)s'

LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False, # Keep existing loggers like uvicorn's
    "formatters": {
        "default": {
            "()": "uvicorn.logging.DefaultFormatter",
            "fmt": "%(levelname)s:     %(asctime)s - %(name)s - %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
        "access": {
            "()": "uvicorn.logging.AccessFormatter",
            "fmt": ACCESS_LOG_FORMAT,
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
    },
    "handlers": {
        "default": {
            "formatter": "default",
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stdout",
        },
        "access": {
            "formatter": "access",
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stdout",
        },
        "file": {
            "formatter": "default",
            "class": "logging.handlers.TimedRotatingFileHandler",
            "filename": "app.log",
            "when": "midnight",
            "backupCount": 7,
        },
    },
    "loggers": {
        "": { # Root logger
            "handlers": ["default", "file"],
            "level": "DEBUG",
            "propagate": False
        },
        "uvicorn.error": {
            "level": "DEBUG",
            "handlers": ["default", "file"],
            "propagate": False
        },
        "uvicorn.access": {
            "handlers": ["access", "file"],
            "level": "DEBUG",
            "propagate": False,
        },
        "uvicorn": {
            "handlers": ["default", "file"],
            "level": "DEBUG",
            "propagate": False
        }
    },
}