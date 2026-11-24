import logging
import os


class SecretFilter(logging.Filter):
    """Remove configured secrets from formatted messages before handlers emit them."""
    def filter(self, record: logging.LogRecord) -> bool:
        message = record.getMessage()
        for key, value in os.environ.items():
            if value and len(value) >= 4 and any(part in key.upper() for part in ("SECRET", "PASSWORD", "API_KEY", "TOKEN")):
                message = message.replace(value, "[REDACTED]")
        record.msg, record.args = message, ()
        return True


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if not any(isinstance(f, SecretFilter) for f in logger.filters):
        logger.addFilter(SecretFilter())
    return logger
