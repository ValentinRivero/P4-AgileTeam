from datetime import date
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import AccessToken

from core.models import Project, ProjectMembership, Task


@override_settings(
    CHANNEL_LAYERS={"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}}
)
class GraphQLAPITests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(username="admin", password="test-pass")
        self.member = User.objects.create_user(username="member", password="test-pass")
        self.project = Project.objects.create(name="Proyecto compartido")
        ProjectMembership.objects.create(
            project=self.project, user=self.admin, role="admin"
        )
        ProjectMembership.objects.create(
            project=self.project, user=self.member, role="miembro"
        )
        self.task = Task.objects.create(project=self.project, title="Tarea original")
        self.client = APIClient()

    def authenticate(self, user):
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {AccessToken.for_user(user)}"
        )

    def test_queries_return_only_projects_and_tasks_visible_to_user(self):
        query = """
            query {
                allProjects {
                    name
                    tasks { title }
                }
            }
        """

        response = self.client.post("/graphql/", {"query": query}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["data"]["allProjects"], [])

        self.authenticate(self.member)
        response = self.client.post("/graphql/", {"query": query}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json()["data"]["allProjects"],
            [{"name": "Proyecto compartido", "tasks": [{"title": "Tarea original"}]}],
        )

        self.client.credentials()
        other_project = Project.objects.create(name="Privado")
        other_task = Task.objects.create(project=other_project, title="Oculta")
        self.authenticate(self.member)
        response = self.client.post(
            "/graphql/",
            {"query": f'query {{ task(id: "{other_task.id}") {{ title }} }}'},
            format="json",
        )
        self.assertEqual(response.json()["data"]["task"], None)

    @patch("core.schema.NotificationService.notify_task_created")
    def test_create_task_requires_admin_and_reuses_serializer_and_notification(
        self, notify_task_created
    ):
        mutation = """
            mutation {
                createTask(projectId: "%s", title: "GraphQL task", priority: "alta") {
                    ok
                    task { title priority }
                }
            }
        """ % self.project.id

        self.authenticate(self.member)
        response = self.client.post(
            "/graphql/", {"query": mutation}, format="json"
        )
        self.assertIn("errors", response.json())
        self.assertFalse(Task.objects.filter(title="GraphQL task").exists())

        self.authenticate(self.admin)
        invalid_mutation = mutation.replace('priority: "alta"', 'priority: "urgente"')
        response = self.client.post(
            "/graphql/", {"query": invalid_mutation}, format="json"
        )
        self.assertIn("errors", response.json())
        self.assertFalse(Task.objects.filter(title="GraphQL task").exists())

        response = self.client.post(
            "/graphql/", {"query": mutation}, format="json"
        )
        self.assertEqual(response.json()["data"]["createTask"]["ok"], True)
        task = Task.objects.get(title="GraphQL task")
        notify_task_created.assert_called_once_with(task)

    @patch("core.schema.NotificationService.notify_task_updated")
    def test_update_task_status_requires_admin_and_emits_update_notification(
        self, notify_task_updated
    ):
        mutation = """
            mutation {
                updateTaskStatus(id: "%s", status: "completada") {
                    ok
                    task { id status }
                }
            }
        """ % self.task.id

        self.authenticate(self.admin)
        response = self.client.post(
            "/graphql/", {"query": mutation}, format="json"
        )
        self.assertIn("errors", response.json())
        self.task.refresh_from_db()
        self.assertEqual(self.task.status, "pendiente")

        self.task.due_date = date(2099, 1, 1)
        self.task.save(update_fields=["due_date"])
        self.authenticate(self.member)
        response = self.client.post(
            "/graphql/", {"query": mutation}, format="json"
        )
        self.assertIn("errors", response.json())
        self.task.refresh_from_db()
        self.assertEqual(self.task.status, "pendiente")

        self.authenticate(self.admin)
        response = self.client.post(
            "/graphql/", {"query": mutation}, format="json"
        )
        self.assertEqual(response.json()["data"]["updateTaskStatus"]["ok"], True)
        self.task.refresh_from_db()
        self.assertEqual(self.task.status, "completada")
        notify_task_updated.assert_called_once_with(self.task)
