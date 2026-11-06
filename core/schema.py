import graphene
from django.db.models import QuerySet
from graphene_django import DjangoObjectType
from graphql import GraphQLError

from .models import Project, Tag, Task
from .serializers import TaskSerializer
from .services import MembershipService, NotificationService


class TagType(DjangoObjectType):
    class Meta:
        model = Tag
        fields = ("id", "name")


class TaskType(DjangoObjectType):
    class Meta:
        model = Task
        fields = (
            "id",
            "title",
            "description",
            "priority",
            "status",
            "due_date",
            "tags",
            "project",
        )
        convert_choices_to_enum = False


class ProjectType(DjangoObjectType):
    class Meta:
        model = Project
        fields = ("id", "name", "description", "tasks")


def tasks_visible_for(user) -> QuerySet[Task]:
    if not user.is_authenticated:
        return Task.objects.none()
    return Task.objects.filter(project__memberships__user=user).distinct()


class Query(graphene.ObjectType):
    all_projects = graphene.List(ProjectType)
    task = graphene.Field(TaskType, id=graphene.ID(required=True))
    tasks_by_status = graphene.List(
        TaskType, status=graphene.String(required=True)
    )

    def resolve_all_projects(root, info):
        user = info.context.user
        if not user.is_authenticated:
            return Project.objects.none()
        return MembershipService.projects_for(user).prefetch_related("tasks")

    def resolve_task(root, info, id):
        return tasks_visible_for(info.context.user).filter(pk=id).first()

    def resolve_tasks_by_status(root, info, status):
        return tasks_visible_for(info.context.user).filter(status=status)


class CreateTask(graphene.Mutation):
    class Arguments:
        project_id = graphene.ID(required=True)
        title = graphene.String(required=True)
        priority = graphene.String(default_value="media")

    task = graphene.Field(TaskType)
    ok = graphene.Boolean()

    def mutate(root, info, project_id, title, priority):
        user = info.context.user
        if not user.is_authenticated:
            raise GraphQLError("Autenticación requerida.")

        serializer = TaskSerializer(
            data={"project": project_id, "title": title, "priority": priority}
        )
        if not serializer.is_valid():
            errors = {
                field: [str(error) for error in messages]
                for field, messages in serializer.errors.items()
            }
            raise GraphQLError(f"Datos inválidos: {errors}")

        if not MembershipService.is_admin(
            user, serializer.validated_data["project"]
        ):
            raise GraphQLError("Solo un admin del proyecto puede crear tareas en él.")

        task = serializer.save(owner=user)
        NotificationService.notify_task_created(task)
        return CreateTask(task=task, ok=True)


class UpdateTaskStatus(graphene.Mutation):
    class Arguments:
        id = graphene.ID(required=True)
        status = graphene.String(required=True)

    task = graphene.Field(TaskType)
    ok = graphene.Boolean()

    def mutate(root, info, id, status):
        user = info.context.user
        if not user.is_authenticated:
            raise GraphQLError("Autenticación requerida.")

        task = tasks_visible_for(user).filter(pk=id).first()
        if task is None:
            raise GraphQLError("Tarea no encontrada o no pertenece a tus proyectos.")
        if not MembershipService.is_admin(user, task.project):
            raise GraphQLError("Solo un admin del proyecto puede actualizar tareas.")

        serializer = TaskSerializer(task, data={"status": status}, partial=True)
        if not serializer.is_valid():
            errors = {
                field: [str(error) for error in messages]
                for field, messages in serializer.errors.items()
            }
            raise GraphQLError(f"Datos inválidos: {errors}")

        task = serializer.save()
        NotificationService.notify_task_updated(task)
        return UpdateTaskStatus(task=task, ok=True)


class Mutation(graphene.ObjectType):
    create_task = CreateTask.Field()
    update_task_status = UpdateTaskStatus.Field()


schema = graphene.Schema(query=Query, mutation=Mutation)
