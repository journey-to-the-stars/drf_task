from django.utils import timezone
from django.contrib.auth import get_user_model
from rest_framework import serializers
from .models import Project, Task

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    """Простой сериализатор для пользователя."""

    class Meta:
        model = User
        fields = ("id", "username", "email", "first_name", "last_name")


class RegistrationSerializer(serializers.ModelSerializer):
    """Простой сериализатор для регистрации пользователей."""

    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ("id", "username", "email", "password")

    def create(self, validated_data):
        return User.objects.create_user(
            username=validated_data["username"],
            email=validated_data.get("email", ""),
            password=validated_data["password"],
        )


class AddParticipantSerializer(serializers.Serializer):
    """Сериализатор для добавления участника в проект."""

    user_id = serializers.IntegerField()


class ProjectSerializer(serializers.ModelSerializer):
    """Проект: владелец read-only, участники как список id."""

    owner = UserSerializer(read_only=True)
    participants = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(), many=True, required=False
    )

    class Meta:
        model = Project
        fields = (
            "id",
            "name",
            "description",
            "owner",
            "participants",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("created_at", "updated_at")

    def create(self, validated_data):
        participants = validated_data.pop("participants", [])
        # owner may be provided via serializer.save(owner=...)
        owner = validated_data.pop("owner", None)
        request = self.context.get("request")
        if owner is None and request is not None:
            owner = request.user
        project = Project.objects.create(owner=owner, **validated_data)
        # добавляем указанных участников и владельца
        if participants:
            project.participants.set(participants)
        if owner and owner not in project.participants.all():
            project.participants.add(owner)
        return project


class TaskSerializer(serializers.ModelSerializer):
    """Задача: author read-only, assignee как id, project как id."""

    author = UserSerializer(read_only=True)

    class Meta:
        model = Task
        fields = (
            "id",
            "project",
            "title",
            "description",
            "priority",
            "status",
            "deadline",
            "author",
            "assignee",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("created_at", "updated_at")

    def validate_deadline(self, value):
        if value and value < timezone.now():
            raise serializers.ValidationError("Deadline cannot be in the past")
        return value

    def validate(self, data):
        # Простая проверка: если указан assignee, он должен быть в participants проекта
        assignee = data.get("assignee")
        project = data.get("project") or getattr(self.instance, "project", None)
        if assignee and project:
            if not project.participants.filter(pk=assignee.pk).exists():
                raise serializers.ValidationError(
                    {"assignee": "User must be a participant of the project"}
                )
        return data

    def create(self, validated_data):
        request = self.context.get("request")
        validated_data["author"] = request.user
        return super().create(validated_data)
