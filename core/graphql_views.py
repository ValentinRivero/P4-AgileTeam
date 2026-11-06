from django.contrib.auth.models import AnonymousUser
from graphene_django.views import GraphQLView
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.authentication import JWTAuthentication


class JWTGraphQLView(GraphQLView):
    def dispatch(self, request, *args, **kwargs):
        request.user = AnonymousUser()
        try:
            result = JWTAuthentication().authenticate(request)
        except AuthenticationFailed:
            result = None
        if result is not None:
            request.user, _ = result
        return super().dispatch(request, *args, **kwargs)
