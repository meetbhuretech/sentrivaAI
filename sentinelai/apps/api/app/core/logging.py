import logging
import re
import sys

from app.core.config import get_settings

# Patterns treated as secrets — redacted before log emit.
# Bearer tokens first so "Authorization: Bearer <jwt>" is fully covered.
_BEARER_PATTERN = re.compile(r"(?i)(authorization\s*:\s*)?bearer\s+[a-z0-9\-._~+/]+=*")
_KEY_VALUE_SECRET_PATTERN = re.compile(
    r"(?i)(api[_-]?key|token|password|secret|authorization)\s*[:=]\s*([^\s,;]+)"
)


class RedactingFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = redact_secrets(record.msg)
        if record.args:
            if isinstance(record.args, dict):
                record.args = {k: redact_secrets(str(v)) for k, v in record.args.items()}
            elif isinstance(record.args, tuple):
                record.args = tuple(
                    redact_secrets(str(a)) if not isinstance(a, int | float) else a
                    for a in record.args
                )
        return True


def redact_secrets(text: str) -> str:
    redacted = _BEARER_PATTERN.sub("***REDACTED***", text)
    redacted = _KEY_VALUE_SECRET_PATTERN.sub(r"\1=***REDACTED***", redacted)
    return redacted


def setup_logging() -> None:
    settings = get_settings()
    root = logging.getLogger()
    root.handlers.clear()
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s [%(name)s] %(message)s")
    )
    handler.addFilter(RedactingFilter())
    root.addHandler(handler)
    root.setLevel(settings.log_level.upper())
