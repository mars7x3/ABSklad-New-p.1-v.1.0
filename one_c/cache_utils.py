import json
from typing import Literal

from django.conf import settings
from django.core.cache import caches


def build_cache_key(user_id, view, action, prefix=settings.ONE_C_TASK_DATA_PREFIX) -> str:
    return f'{prefix}:{user_id}:{view}:{action}'


def rebuild_cache_key(key: str):
    _, user_id, view, action = key.split(":")
    return {
        "user_id": user_id,
        "view": view,
        "action": action
    }


def set_form_data(user_id: int, data: dict, view_name: str, action: Literal['create', 'update', 'delete']) -> str:
    cache = caches[settings.ONE_C_TASK_CACHE]
    cache_key = build_cache_key(user_id, view_name, action)
    cache.set(cache_key, json.dumps(data), settings.ONE_C_TASK_DATA_EXPIRE)
    cache.close()
    return cache_key


LAUNCH_TASK_PREFIX = "launch-task"


def set_launch_task(cache_key, task_id):
    cache = caches[settings.ONE_C_TASK_CACHE]
    task_key = f"{LAUNCH_TASK_PREFIX}:{cache_key}"
    cache.set(task_key, task_id, settings.ONE_C_TASK_DATA_EXPIRE)
    cache.close()
    return cache_key


def get_launch_task_id(cache_key) -> str | None:
    cache = caches[settings.ONE_C_TASK_CACHE]
    task_key = f"{LAUNCH_TASK_PREFIX}:{cache_key}"
    task_id = cache.get(task_key)
    cache.close()
    return task_id


def get_form_data_from_cache(key: str):
    cache = caches[settings.ONE_C_TASK_CACHE]
    data = cache.get(key)
    cache.close()
    if data:
        return json.loads(data)


def delete_from_cache(key) -> None:
    cache = caches[settings.ONE_C_TASK_CACHE]
    cache.delete(key)
    cache.close()


def get_all_user_keys(user_id: int):
    cache = caches[settings.ONE_C_TASK_CACHE]
    keys = cache.keys(f'{settings.ONE_C_TASK_DATA_PREFIX}:{user_id}:*')
    cache.close()
    return keys


def get_title_by_action(action: str) -> str:
    match action:
        case 'create':
            return 'cоздание'
        case 'update':
            return 'обновление'
        case _:
            return 'удаление'
