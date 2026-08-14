import logging
import re
import sys
from typing import Any


class SensitiveDataFilter(logging.Filter):
    """
    Log filter that masks sensitive data such as database passwords,
    tokens, API keys, and authorization headers before output.
    """
    PATTERNS = [
        # postgresql://user:password@host
        (re.compile(r"(postgres(?:ql)?(?:\+psycopg)?://[^:]+:)([^@]+)(@)", re.IGNORECASE), r"\1***\3"),
        # Bearer tokens or generic tokens
        (re.compile(r"(Bearer\s+)[A-Za-z0-9\-_.]+", re.IGNORECASE), r"\1***"),
        # password=..., secret=..., token=...
        (re.compile(r"(['\"]?(?:password|secret|token|auth_token|api_key)['\"]?\s*[:=]\s*['\"])[^'\"]+(['\"])", re.IGNORECASE), r"\1***\2"),
    ]

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            for pattern, repl in self.PATTERNS:
                record.msg = pattern.sub(repl, record.msg)
        if record.args:
            sanitized_args = []
            for arg in record.args:
                if isinstance(arg, str):
                    for pattern, repl in self.PATTERNS:
                        arg = pattern.sub(repl, arg)
                sanitized_args.append(arg)
            record.args = tuple(sanitized_args)
        return True


def setup_logging(log_level: str = "INFO", debug: bool = False) -> None:
    """
    Configures application-wide structured and safe logging.
    """
    level = logging.DEBUG if debug else getattr(logging, log_level.upper(), logging.INFO)

    log_format = "%(asctime)s - %(levelname)s - [%(name)s] - %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"

    # Root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Remove existing handlers to avoid duplicates
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(logging.Formatter(fmt=log_format, datefmt=date_format))
    console_handler.addFilter(SensitiveDataFilter())

    root_logger.addHandler(console_handler)

    # Suppress verbose external loggers
    logging.getLogger("uvicorn.access").setLevel(logging.INFO)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING if not debug else logging.INFO)
    logging.getLogger("alembic").setLevel(logging.INFO)
