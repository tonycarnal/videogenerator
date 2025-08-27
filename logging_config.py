import logging
import logging.config
import os
import sys
import structlog

def setup_logging():
    """
    Configures the logging for the application using structlog.
    """
    log_level = os.environ.get("LOG_LEVEL", "INFO").upper()
    log_to_file = os.environ.get("LOG_TO_FILE", "False").lower() == "true"

    # Base logging configuration
    logging.config.dictConfig({
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "json": {
                "()": structlog.stdlib.ProcessorFormatter,
                "processor": structlog.processors.JSONRenderer(),
            },
            "console": {
                "()": structlog.stdlib.ProcessorFormatter,
                "processor": structlog.dev.ConsoleRenderer(),
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "console",
                "stream": sys.stdout,
            },
        },
        "loggers": {
            "": {
                "handlers": ["console"],
                "level": log_level,
                "propagate": True,
            },
        }
    })

    # Add file handler if enabled
    if log_to_file:
        file_handler = logging.FileHandler("app.log")
        file_handler.setFormatter(logging.Formatter("%(message)s"))
        
        # Get the root logger and add the file handler
        root_logger = logging.getLogger()
        root_logger.addHandler(file_handler)

    # Configure structlog
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
