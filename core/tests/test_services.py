from datetime import date

import pytest
from rest_framework.exceptions import ValidationError

from core.models import Project, Task
from core.services import HolidayService, TaskService


@pytest.mark.django_db
def test_mark_completed_cambia_el_status():
    project = Project.objects.create(name="Demo")
    task = Task.objects.create(project=project, title="Test", due_date=date(2030, 1, 10))

    TaskService.mark_completed(task)
    task.refresh_from_db()

    assert task.status == "completada"


@pytest.mark.django_db
def test_mark_completed_sin_fecha_limite_falla():
    project = Project.objects.create(name="Demo")
    task = Task.objects.create(project=project, title="Sin fecha")

    with pytest.raises(ValidationError):
        TaskService.mark_completed(task)


def test_is_holiday_usa_la_lista_de_feriados():
    assert HolidayService.is_holiday(date(2030, 5, 25)) is True
    assert HolidayService.is_holiday(date(2030, 5, 26)) is False
