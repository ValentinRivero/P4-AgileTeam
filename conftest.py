import pytest
from django.contrib.auth.models import User
from rest_framework.test import APIClient

from core.models import Project, ProjectMembership
from core.services import HolidayService


@pytest.fixture(autouse=True)
def entorno_de_test(settings, monkeypatch):
    # Sin Redis: el channel layer vive en memoria durante los tests
    settings.CHANNEL_LAYERS = {"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}}
    # Sin internet: la API de feriados devuelve una lista fija
    monkeypatch.setattr(HolidayService, "get_holidays", classmethod(lambda cls, year: [f"{year}-05-25"]))
    # Sin límites de peticiones
    settings.REST_FRAMEWORK = {**settings.REST_FRAMEWORK, "DEFAULT_THROTTLE_CLASSES": []}


@pytest.fixture
def ana(db):
    return User.objects.create_user(username="ana", password="clave12345")


@pytest.fixture
def beto(db):
    return User.objects.create_user(username="beto", password="clave12345")


@pytest.fixture
def proyecto(ana, beto):
    project = Project.objects.create(name="Proyecto de Ana")
    ProjectMembership.objects.create(project=project, user=ana, role="admin")
    ProjectMembership.objects.create(project=project, user=beto, role="miembro")
    return project


@pytest.fixture
def cliente():
    return APIClient()
