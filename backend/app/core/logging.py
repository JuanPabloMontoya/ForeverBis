"""Small JSON logging configuration using the Python standard library."""

import json
import logging
from datetime import UTC, datetime
from typing import Any


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        entry: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(timespec="milliseconds"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            entry["exception"] = self.formatException(record.exc_info)
        for key in ("path", "method", "status_code"):
            if hasattr(record, key):
                entry[key] = getattr(record, key)
        return json.dumps(entry, ensure_ascii=False)


def configure_logging(level: str) -> None:
    root = logging.getLogger()
    root.setLevel(level)
    if not any(getattr(handler, "_forever_bis_json", False) for handler in root.handlers):
        handler = logging.StreamHandler()
        handler.setFormatter(JsonFormatter())
        handler._forever_bis_json = True  # type: ignore[attr-defined]
        root.addHandler(handler)
