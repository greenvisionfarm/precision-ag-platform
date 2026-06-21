"""
Handler для аудит-журнала — список последних изменений.
"""
import json
import logging

from src.models.field import AuditLog
from src.middleware.auth import AuthenticatedRequestHandler, require_auth
from src.utils.db_utils import db_connection

logger = logging.getLogger(__name__)


class AuditLogHandler(AuthenticatedRequestHandler):
    """GET /api/audit-logs — последние записи аудит-журнала."""

    @require_auth
    def get(self) -> None:
        try:
            limit = min(int(self.get_argument("limit", 50)), 200)

            with db_connection():
                logs = (
                    AuditLog.select()
                    .where(AuditLog.company == self.current_user.company)
                    .order_by(AuditLog.created_at.desc())
                    .limit(limit)
                )

                result = []
                for log in logs:
                    result.append({
                        "id": log.id,
                        "user_email": log.user_email,
                        "action": log.action,
                        "entity_type": log.entity_type,
                        "entity_id": log.entity_id,
                        "entity_name": log.entity_name,
                        "details": json.loads(log.details) if log.details else None,
                        "created_at": log.created_at.isoformat() if log.created_at else None,
                    })

                self.write({"logs": result})
        except Exception as e:
            logger.error(f"Audit log list error: {e}")
            self.set_status(500)
            self.write({"error": str(e)})
