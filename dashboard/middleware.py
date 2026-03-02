import logging

from django.db import OperationalError, close_old_connections


logger = logging.getLogger(__name__)


class MySQLConnectionRecoveryMiddleware:
    """Retry safe requests once when MySQL drops a stale connection."""

    RETRY_METHODS = {"GET", "HEAD", "OPTIONS"}
    TRANSIENT_DB_TOKENS = (
        "server has gone away",
        "lost connection to mysql server",
        "connection reset",
        "forcibly closed by the remote host",
    )

    def __init__(self, get_response):
        self.get_response = get_response

    def _is_transient_db_error(self, exc):
        message = str(exc).lower()
        return any(token in message for token in self.TRANSIENT_DB_TOKENS)

    def __call__(self, request):
        close_old_connections()
        try:
            return self.get_response(request)
        except OperationalError as exc:
            if request.method not in self.RETRY_METHODS or not self._is_transient_db_error(exc):
                raise
            logger.warning("Transient MySQL disconnect detected, retrying request once: %s %s", request.method, request.path)
            close_old_connections()
            return self.get_response(request)
        finally:
            close_old_connections()
