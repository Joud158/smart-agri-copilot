from __future__ import annotations

import json
import logging
from typing import Any


def configure_logging(service_name: str) -> logging.Logger:
    logger = logging.getLogger(service_name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(message)s"))
        logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False
    return logger


def log_event(logger: logging.Logger, event: str, **payload: Any) -> None:
    record = {"event": event, **payload}
    logger.info(json.dumps(record, ensure_ascii=False, default=str))
