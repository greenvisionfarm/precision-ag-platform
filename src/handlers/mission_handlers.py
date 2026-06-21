"""
Handlers для миссий дронов (CRUD операции).
"""
import json
import logging

from src.models.field import Field, Mission
from src.middleware.auth import AuthenticatedRequestHandler, require_auth
from src.services.kmz_service import generate_lawnmower_path, calculate_optimal_heading
from src.utils.db_utils import db_connection

logger = logging.getLogger(__name__)


class MissionListHandler(AuthenticatedRequestHandler):
    """GET /api/field/{field_id}/missions — список миссий поля."""

    @require_auth
    def get(self, field_id: int) -> None:
        try:
            with db_connection():
                field = Field.select().where(
                    (Field.id == field_id) & (Field.company == self.current_user.company)
                ).first()
                if not field:
                    self.set_status(404)
                    self.write({"error": "Поле не найдено"})
                    return

                missions = Mission.select().where(
                    Mission.field == field
                ).order_by(Mission.created_at.desc())

                result = []
                for m in missions:
                    result.append({
                        "id": m.id,
                        "name": m.name,
                        "height": m.height,
                        "overlap_h": m.overlap_h,
                        "overlap_w": m.overlap_w,
                        "direction": m.direction,
                        "notes": m.notes,
                        "created_at": m.created_at.isoformat() if m.created_at else None,
                    })

                self.write({"missions": result})
        except Exception as e:
            logger.error(f"Mission list error: {e}")
            self.set_status(500)
            self.write({"error": str(e)})


class MissionCreateHandler(AuthenticatedRequestHandler):
    """POST /api/field/{field_id}/missions — создать миссию."""

    @require_auth
    def post(self, field_id: int) -> None:
        try:
            with db_connection():
                field = Field.select().where(
                    (Field.id == field_id) & (Field.company == self.current_user.company)
                ).first()
                if not field:
                    self.set_status(404)
                    self.write({"error": "Поле не найдено"})
                    return

                body = json.loads(self.request.body)

                mission = Mission.create(
                    field=field,
                    company=self.current_user.company,
                    name=body.get('name'),
                    height=body.get('height', 100),
                    overlap_h=body.get('overlap_h', 80),
                    overlap_w=body.get('overlap_w', 70),
                    direction=body.get('direction'),
                    notes=body.get('notes'),
                )

                self.write({"id": mission.id, "status": "created"})
        except Exception as e:
            logger.error(f"Mission create error: {e}")
            self.set_status(500)
            self.write({"error": str(e)})


class MissionDetailHandler(AuthenticatedRequestHandler):
    """GET /api/field/{field_id}/missions/{mission_id} — детали миссии с путём."""

    @require_auth
    def get(self, field_id: int, mission_id: int) -> None:
        try:
            with db_connection():
                field = Field.select().where(
                    (Field.id == field_id) & (Field.company == self.current_user.company)
                ).first()
                if not field:
                    self.set_status(404)
                    self.write({"error": "Поле не найдено"})
                    return

                mission = Mission.select().where(
                    (Mission.id == mission_id) & (Mission.field == field)
                ).first()
                if not mission:
                    self.set_status(404)
                    self.write({"error": "Миссия не найдена"})
                    return

                direction = mission.direction if mission.direction is not None else calculate_optimal_heading(field.geometry_wkt)

                waypoints = generate_lawnmower_path(
                    field.geometry_wkt,
                    int(mission.height),
                    int(mission.overlap_w),
                    direction
                )

                path_coords = [[lat, lon] for lon, lat in waypoints]

                self.write({
                    "id": mission.id,
                    "name": mission.name,
                    "height": mission.height,
                    "overlap_h": mission.overlap_h,
                    "overlap_w": mission.overlap_w,
                    "direction": mission.direction,
                    "notes": mission.notes,
                    "created_at": mission.created_at.isoformat() if mission.created_at else None,
                    "path": path_coords,
                    "waypoint_count": len(waypoints),
                    "optimal_direction": direction,
                })
        except Exception as e:
            logger.error(f"Mission detail error: {e}")
            self.set_status(500)
            self.write({"error": str(e)})


class MissionDeleteHandler(AuthenticatedRequestHandler):
    """DELETE /api/field/{field_id}/missions/{mission_id} — удалить миссию."""

    @require_auth
    def delete(self, field_id: int, mission_id: int) -> None:
        try:
            with db_connection():
                mission = Mission.select().where(
                    (Mission.id == mission_id) &
                    (Mission.field == field_id) &
                    (Mission.company == self.current_user.company)
                ).first()
                if not mission:
                    self.set_status(404)
                    self.write({"error": "Миссия не найдена"})
                    return

                mission.delete_instance()
                self.write({"status": "deleted"})
        except Exception as e:
            logger.error(f"Mission delete error: {e}")
            self.set_status(500)
            self.write({"error": str(e)})


class MissionPreviewHandler(AuthenticatedRequestHandler):
    """POST /api/field/{field_id}/missions/preview — предпросмотр пути без сохранения."""

    @require_auth
    def post(self, field_id: int) -> None:
        try:
            with db_connection():
                field = Field.select().where(
                    (Field.id == field_id) & (Field.company == self.current_user.company)
                ).first()
                if not field:
                    self.set_status(404)
                    self.write({"error": "Поле не найдено"})
                    return

                body = json.loads(self.request.body)
                height = body.get('height', 100)
                overlap_h = body.get('overlap_h', 80)
                overlap_w = body.get('overlap_w', 70)
                direction = body.get('direction')

                if direction is None:
                    direction = calculate_optimal_heading(field.geometry_wkt)

                waypoints = generate_lawnmower_path(
                    field.geometry_wkt,
                    int(height),
                    int(overlap_w),
                    direction
                )

                path_coords = [[lat, lon] for lon, lat in waypoints]

                self.write({
                    "path": path_coords,
                    "waypoint_count": len(waypoints),
                    "optimal_direction": direction,
                })
        except Exception as e:
            logger.error(f"Mission preview error: {e}")
            self.set_status(500)
            self.write({"error": str(e)})
