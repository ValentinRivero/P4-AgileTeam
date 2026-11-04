import logging

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.utils import timezone
from rest_framework.exceptions import ValidationError
import requests
from django.core.cache import cache
from .models import Project, ProjectMembership, Task
from .repositories import TaskRepository

logger = logging.getLogger(__name__)


class TaskService:
    @staticmethod
    def mark_completed(task: Task) -> Task:
        if not task.due_date:
            raise ValidationError(
                "No se puede marcar una tarea como completada sin fecha límite registrada."
            )
        task.status = "completada"
        task.save(update_fields=["status"])
        return task

    @staticmethod
    def tasks_overdue(queryset=None):
        if queryset is None:
            queryset = TaskRepository.get_queryset()
        today = timezone.now().date()
        return queryset.filter(due_date__lt=today).exclude(status="completada")


class HolidayService:
    API_URL = "https://date.nager.at/api/v3/PublicHolidays/{year}/AR"
 
    @classmethod
    def get_holidays(cls, year: int) -> list[str]:
        cache_key = f"holidays_{year}"
        cached = cache.get(cache_key)
        if cached is not None:
            return cached
        try:
            response = requests.get(cls.API_URL.format(year=year), timeout=5)
            response.raise_for_status()
            dates = [item["date"] for item in response.json()]
            cache.set(cache_key, dates, timeout=60 * 60 * 24)  # 24 horas
        except (requests.RequestException, ValueError, KeyError):
            dates = []
            cache.set(cache_key, dates, timeout=60 * 5)  # si falló, reintentamos en 5 minutos
        return dates
 
    @classmethod
    def is_holiday(cls, some_date) -> bool:
        return str(some_date) in cls.get_holidays(some_date.year)

class MembershipService:
    @staticmethod
    def is_member(user, project) -> bool:
        return ProjectMembership.objects.filter(project=project, user=user).exists()
 
    @staticmethod
    def is_admin(user, project) -> bool:
        return ProjectMembership.objects.filter(project=project, user=user, role="admin").exists()
 
    @staticmethod
    def projects_for(user):
        return Project.objects.filter(memberships__user=user).distinct().order_by("id")


class NotificationService:
    @staticmethod
    def notify_task_created(task):
        NotificationService._send(task.project_id, {
            "event": "task_created",
            "task_id": task.id,
            "title": task.title,
        })

    @staticmethod
    def notify_task_updated(task):
        NotificationService._send(task.project_id, {
            "event": "task_updated",
            "task_id": task.id,
            "title": task.title,
            "status": task.status,
        })

    @staticmethod
    def notify_task_completed(task):
        NotificationService._send(task.project_id, {
            "event": "task_completed",
            "task_id": task.id,
            "title": task.title,
        })

    @staticmethod
    def _send(project_id, payload):
        channel_layer = get_channel_layer()
        try:
            async_to_sync(channel_layer.group_send)(
                f"project_{project_id}",
                {
                    "type": "task_notification",  # nombre del método en TaskNotificationConsumer
                    "payload": payload,
                },
            )
        except Exception:
            # La tarea ya quedó guardada: si Redis falla solo se registra en el log
            logger.exception("No se pudo enviar la notificación en tiempo real")