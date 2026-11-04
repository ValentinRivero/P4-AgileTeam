from django.contrib import admin
from .models import Project, Task, Tag, ProjectMembership, SecurityLog

admin.site.register(Project)
admin.site.register(Task)
admin.site.register(Tag)
admin.site.register(ProjectMembership)
admin.site.register(SecurityLog)