"""
Health check handler — проверка работоспособности всех компонентов.
"""
import logging
import os
import time
from typing import Any, Dict

import tornado.web

logger = logging.getLogger(__name__)

_start_time = time.time()


class HealthHandler(tornado.web.RequestHandler):
    """GET /api/health — возвращает статус DB, Redis, uptime."""

    def prepare(self) -> None:
        from src.logging_config import generate_request_id, request_id_var
        req_id = self.request.headers.get("X-Request-ID", generate_request_id())
        request_id_var.set(req_id)
        self.set_header("X-Request-ID", req_id)

    def get(self) -> None:
        checks: Dict[str, Any] = {}
        healthy = True

        checks["app"] = {
            "status": "ok",
            "uptime_seconds": round(time.time() - _start_time, 1),
            "pid": os.getpid(),
        }

        checks["db"] = self._check_db()
        if checks["db"]["status"] != "ok":
            healthy = False

        checks["redis"] = self._check_redis()
        if checks["redis"]["status"] != "ok":
            healthy = False

        status_code = 200 if healthy else 503
        self.set_status(status_code)
        self.write({
            "status": "healthy" if healthy else "degraded",
            "checks": checks,
        })

    def _check_db(self) -> Dict[str, Any]:
        try:
            from db import database
            if database.is_closed():
                database.connect()
            cursor = database.execute_sql("SELECT 1")
            cursor.fetchone()
            return {"status": "ok"}
        except Exception as e:
            logger.error(f"Health check DB failed: {e}")
            return {"status": "error", "message": str(e)}

    def _check_redis(self) -> Dict[str, Any]:
        try:
            import redis
            redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
            r = redis.from_url(redis_url, socket_timeout=2)
            r.ping()
            return {"status": "ok"}
        except ImportError:
            return {"status": "ok", "message": "redis not installed, skipped"}
        except Exception as e:
            logger.error(f"Health check Redis failed: {e}")
            return {"status": "error", "message": str(e)}
