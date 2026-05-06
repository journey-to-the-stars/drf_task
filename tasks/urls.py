"""URL configuration for tasks app."""

from django.urls import include, path
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .views import (
    ProjectParticipantsView,
    ProjectViewSet,
    TaskViewSet,
    UserViewSet,
    RegistrationView,
)

router = DefaultRouter()
router.register(r"projects", ProjectViewSet, basename="project")
router.register(r"tasks", TaskViewSet, basename="task")
router.register(r"users", UserViewSet, basename="user")

urlpatterns = [
    path("", include(router.urls)),
    path(
        "projects/<int:pk>/participants/",
        ProjectParticipantsView.as_view(),
        name="project-participants",
    ),
    path("auth/token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("auth/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("auth/register/", RegistrationView.as_view(), name="auth_register"),
]
