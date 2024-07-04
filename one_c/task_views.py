import json

from celery.result import AsyncResult
from rest_framework import mixins
from rest_framework.decorators import api_view, permission_classes
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.viewsets import GenericViewSet

from absklad_commerce.celery import app as celery_app
from one_c.cache_utils import (
    set_form_data, rebuild_cache_key, delete_from_cache,
    set_launch_task, get_launch_task_id, get_user_notifications, get_from_cache, NOTIFY_PREFIX
)


def _check_task_key(task_key, request_user_id) -> dict:
    try:
        key_data = rebuild_cache_key(task_key)
    except ValueError:
        raise ValidationError({"detail": "Invalid key"})

    if str(key_data["user_id"]) != str(request_user_id):
        raise PermissionDenied()
    return key_data


class OneCCreateTaskMixin:
    create_task = None

    def create(self, request, *args, **kwargs):
        assert self.create_task
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(status=204)

    def perform_create(self, serializer):
        cache_key = self._save_validated_data(serializer.validated_data)
        self._run_task(self.create_task, cache_key)


class OneCUpdateTaskMixin:
    update_task = None

    def update(self, request, *args, **kwargs):
        assert self.update_task
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(status=204)

    def perform_update(self, serializer):
        validated_data = serializer.validated_data
        validated_data["id"] = serializer.instance.id
        cache_key = self._save_validated_data(validated_data)
        self._run_task(self.update_task, cache_key)


class OneCDestroyTaskMixin:
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response(status=204)

    def perform_destroy(self, instance):
        instance.is_active = False
        instance.save()


class OneCTaskGenericMixin:
    def _save_validated_data(self, data):
        return set_form_data(
            self.request.user.id,
            data=data,
            view_name=self.get_view_name(),
            action=self.action,
        )

    @staticmethod
    def _get_task_args(cache_key):
        return (cache_key,)

    def _run_task(self, task, cache_key):
        task = task.apply_async(args=self._get_task_args(cache_key))
        set_launch_task(cache_key, task.task_id)


class OneCTaskGenericViewSet(OneCTaskGenericMixin, GenericViewSet):
    permission_classes = [IsAuthenticated]  # required!


class OneCActionView(
    OneCCreateTaskMixin,
    OneCUpdateTaskMixin,
    OneCTaskGenericViewSet
):
    pass


class OneCModelView(
    mixins.RetrieveModelMixin,
    mixins.ListModelMixin,
    OneCCreateTaskMixin,
    OneCUpdateTaskMixin,
    OneCDestroyTaskMixin,
    OneCTaskGenericViewSet
):
    pass


class OneCTaskGenericAPIView(OneCTaskGenericMixin, GenericAPIView):
    permission_classes = [IsAuthenticated]  # required!


class OneCTaskActionAPIView(
    OneCCreateTaskMixin,
    OneCUpdateTaskMixin,
    OneCTaskGenericAPIView
):
    pass


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def tasks_list_view(request):
    data = get_user_notifications(request.user.id)
    if not data:
        return Response(status=404)

    items = []
    for key, value in data.items():
        item = json.loads(value)
        item["key"] = key
        items.append(item)

    return Response(items)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def task_detail_view(request, task_key):
    rebuild_key = _check_task_key(task_key, request.user.id)

    if rebuild_key["prefix"].startswith(NOTIFY_PREFIX):
        task_key = task_key.replace(NOTIFY_PREFIX, "")

    form_data = get_from_cache(task_key)
    if not form_data:
        return Response(status=404)
    return Response(form_data)


@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
def task_destroy_view(request, task_key):
    rebuild_key = _check_task_key(task_key, request.user.id)

    if not rebuild_key["prefix"].startswith(NOTIFY_PREFIX):
        raise ValidationError({"detail": "Invalid key"})

    delete_from_cache(task_key)
    delete_from_cache(task_key.replace(NOTIFY_PREFIX, ""))
    return Response(status=204)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def task_repeat_view(request, task_key):
    _check_task_key(task_key, request.user.id)

    if task_key.startswith(NOTIFY_PREFIX):
        task_key = task_key.replace(NOTIFY_PREFIX, "")

    task_id = get_launch_task_id(task_key)
    if not task_id:
        delete_from_cache(task_key)
        return Response(status=404)

    result = AsyncResult(task_id, app=celery_app)
    match result.state:
        case 'PENDING':
            return Response({"detail": "Задача уже запущена"}, status=400)
        case _:
            result.revoke()
            delete_from_cache(f"{NOTIFY_PREFIX}{task_key}")
            celery_app.send_task(result.name, args=result.args, kwargs=result.kwargs)
    return Response(status=204)
