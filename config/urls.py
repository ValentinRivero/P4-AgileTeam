from django.contrib import admin
from django.urls import path, include
from rest_framework_simplejwt.views import TokenRefreshView
from core.views import RegisterView, SocialLoginJWTView, ThrottledTokenObtainPairView

urlpatterns = [
path("admin/", admin.site.urls),
path("api/", include("core.urls")),
path("api-auth/", include("rest_framework.urls")),
path("api/register/", RegisterView.as_view(), name="register"),
path("accounts/", include("allauth.urls")),
path("api/auth/social/jwt/", SocialLoginJWTView.as_view(), name="social_jwt"),
path("api/token/", ThrottledTokenObtainPairView.as_view(), name="token_obtain_pair"),
path("api/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
]