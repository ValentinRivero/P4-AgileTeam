import pytest

from core.models import Project, Task


@pytest.mark.django_db
def test_listar_tareas_requiere_autenticacion(cliente):
    response = cliente.get("/api/tasks/")
    assert response.status_code == 401


@pytest.mark.django_db
def test_usuario_solo_ve_tareas_de_sus_proyectos(cliente, ana, proyecto):
    Task.objects.create(project=proyecto, title="Mía")
    otro = Project.objects.create(name="Proyecto ajeno")
    Task.objects.create(project=otro, title="Ajena")

    cliente.force_authenticate(user=ana)
    response = cliente.get("/api/tasks/")

    assert response.status_code == 200
    titulos = [t["title"] for t in response.data["results"]]
    assert titulos == ["Mía"]


@pytest.mark.django_db
def test_admin_puede_crear_tarea(cliente, ana, proyecto):
    cliente.force_authenticate(user=ana)
    response = cliente.post("/api/tasks/", {"project": proyecto.id, "title": "Nueva"}, format="json")
    assert response.status_code == 201


@pytest.mark.django_db
def test_miembro_no_puede_crear_tarea(cliente, beto, proyecto):
    cliente.force_authenticate(user=beto)
    response = cliente.post("/api/tasks/", {"project": proyecto.id, "title": "Nueva"}, format="json")
    assert response.status_code == 403
