"""Views for tasks app."""

from django.contrib.auth import get_user_model
from django_filters import rest_framework as filters
from rest_framework import generics, permissions, status, viewsets
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response

from .models import Project, Task
from .serializers import (
    RegistrationSerializer,
    AddParticipantSerializer,
    ProjectSerializer,
    TaskSerializer,
    UserSerializer,
)

User = get_user_model()


class UserViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only viewset for users."""

    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]


class TaskFilter(filters.FilterSet):
    """FilterSet for tasks: supports deadline range and basic fields."""

    deadline_gte = filters.DateTimeFilter(field_name="deadline", lookup_expr="gte")
    deadline_lte = filters.DateTimeFilter(field_name="deadline", lookup_expr="lte")

    class Meta:
        model = Task
        fields = ["project", "status", "priority", "assignee"]


class ProjectViewSet(viewsets.ModelViewSet):
    """CRUD for projects; list limited to user's projects."""

    queryset = Project.objects.all()
    serializer_class = ProjectSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Return projects owned by or including the request user as participant."""
        return Project.objects.filter(owner=self.request.user) | Project.objects.filter(
            participants=self.request.user
        )

    def perform_create(self, serializer):
        """Set the request user as project owner on create."""
        serializer.save(owner=self.request.user)

    def update(self, request, *args, **kwargs):
        """Allow update only to project owner."""
        project = self.get_object()
        if project.owner != request.user:
            return Response(
                {"detail": "Only project owner can update the project."},
                status=status.HTTP_403_FORBIDDEN,
            )
        return super().update(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        """Allow partial update only to project owner."""
        project = self.get_object()
        if project.owner != request.user:
            return Response(
                {"detail": "Only project owner can update the project."},
                status=status.HTTP_403_FORBIDDEN,
            )
        return super().partial_update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        """Allow delete only to project owner."""
        project = self.get_object()
        if project.owner != request.user:
            return Response(
                {"detail": "Only project owner can delete the project."},
                status=status.HTTP_403_FORBIDDEN,
            )
        return super().destroy(request, *args, **kwargs)


class ProjectParticipantsView(generics.GenericAPIView):
    """List, add and remove participants for a project.

    - GET: list participants
    - POST: add participant (owner only)
    - DELETE: remove participant (owner only)
    """

    permission_classes = [permissions.IsAuthenticated]
    serializer_class = AddParticipantSerializer
    queryset = Project.objects.all()

    def get(self, request, pk):
        """Return project participants (owner or participant only)."""
        project = self.get_object()
        if not (
            project.owner == request.user
            or project.participants.filter(pk=request.user.pk).exists()
        ):
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        serializer = UserSerializer(project.participants.all(), many=True)
        return Response(serializer.data)

    def post(self, request, pk):
        """Add a participant to the project (owner only)."""
        project = self.get_object()
        if project.owner != request.user:
            return Response(
                {"detail": "Only project owner can add participants."},
                status=status.HTTP_403_FORBIDDEN,
            )
        serializer = AddParticipantSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user_id = serializer.validated_data["user_id"]
        try:
            user = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return Response(
                {"error": "User not found"}, status=status.HTTP_404_NOT_FOUND
            )
        project.participants.add(user)
        return Response({"status": "added"}, status=status.HTTP_201_CREATED)

    def delete(self, request, pk, user_id):
        """Remove a participant from the project (owner only)."""
        project = self.get_object()
        if project.owner != request.user:
            return Response(
                {"detail": "Only project owner can remove participants."},
                status=status.HTTP_403_FORBIDDEN,
            )
        try:
            user = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return Response(
                {"error": "User not found"}, status=status.HTTP_404_NOT_FOUND
            )
        if user == project.owner:
            return Response({"detail": "Cannot remove owner."}, status=400)
        project.participants.remove(user)
        return Response(status=status.HTTP_204_NO_CONTENT)


class TaskViewSet(viewsets.ModelViewSet):
    """CRUD for tasks with permission checks for create/partial_update/destroy."""

    queryset = Task.objects.all()
    serializer_class = TaskSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_class = TaskFilter

    def get_queryset(self):
        """Return tasks for projects where request user is owner or participant."""
        return Task.objects.filter(
            project__owner=self.request.user
        ) | Task.objects.filter(project__participants=self.request.user)

    def perform_create(self, serializer):
        """Allow creation only if request user is project owner or participant."""
        project = serializer.validated_data["project"]
        if not (
            project.owner == self.request.user
            or project.participants.filter(pk=self.request.user.pk).exists()
        ):
            raise PermissionDenied("Only project participants can create tasks")
        serializer.save(author=self.request.user)

    def destroy(self, request, *args, **kwargs):
        """Allow deletion only to task author or project owner."""
        task = self.get_object()
        if not (task.author == request.user or task.project.owner == request.user):
            return Response(
                {"detail": "Only task author or project owner can delete this task."},
                status=status.HTTP_403_FORBIDDEN,
            )
        return super().destroy(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        """Minimal permission checks for partial updates of a task."""
        task = self.get_object()

        # Owner can change anything
        if task.project.owner == request.user:
            return super().partial_update(request, *args, **kwargs)

        # Assignee can change only status and priority
        if task.assignee == request.user:
            allowed = {"status", "priority"}
            if set(request.data.keys()) - allowed:
                return Response(
                    {"error": f"Assignee can only update {sorted(allowed)}"},
                    status=status.HTTP_403_FORBIDDEN,
                )
            return super().partial_update(request, *args, **kwargs)

        # Author can change only description
        if task.author == request.user:
            allowed = {"description"}
            if set(request.data.keys()) - allowed:
                return Response(
                    {"error": f"Author can only update {sorted(allowed)}"},
                    status=status.HTTP_403_FORBIDDEN,
                )
            return super().partial_update(request, *args, **kwargs)

        # By default forbid
        return Response(
            {"detail": "You do not have permission to perform this action."},
            status=status.HTTP_403_FORBIDDEN,
        )


class RegistrationView(generics.GenericAPIView):
    """Minimal endpoint to register new users."""

    serializer_class = RegistrationSerializer
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        """Create a new user account."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)
