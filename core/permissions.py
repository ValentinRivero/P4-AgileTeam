from rest_framework import permissions
from .services import MembershipService
from .models import SecurityLog

class IsProjectAdminOrReadOnly(permissions.BasePermission):
    """
    Cualquier miembro del proyecto puede leer.
    Solo un admin del proyecto puede modificar (editar/borrar).
    Sirve tanto para Task (obj.project) como para Project (obj).
    """

    def has_object_permission(self, request, view, obj):
        project = obj.project if hasattr(obj, "project") else obj
        
        if request.method in permissions.SAFE_METHODS:  # GET, HEAD, OPTIONS
            return MembershipService.is_member(request.user, project)
        
        es_admin = MembershipService.is_admin(request.user, project)

        if not es_admin:
            ip = request.META.get("REMOTE_ADDR")
            SecurityLog.objects.create(
                user=request.user,
                action="permission_denied",
                detail=f"Intento de modificación denegado en el proyecto {project.id}",
                ip_address=ip
            )
            
        return es_admin