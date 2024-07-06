import json
import logging
from typing import Literal

from django.conf import settings
from django.core.cache import caches
from django.core.serializers.json import DjangoJSONEncoder
from django.utils import timezone
from django.utils.dateformat import DateFormat

from notification.utils import send_web_push_notification


NOTIFY_PREFIX = "notify-"  # without ':' required!


def build_cache_key(user_id, view, action, prefix=settings.ONE_C_TASK_DATA_PREFIX) -> str:
    return f'{prefix}:{user_id}:{view}:{action}:{int(timezone.now().timestamp())}'


def rebuild_cache_key(key: str):
    prefix, user_id, view, action, ts = key.split(":")
    return {
        "prefix": prefix,
        "user_id": user_id,
        "view": view,
        "action": action,
        "timestamp": ts
    }


def set_form_data(user_id: int, data: dict, view_name: str, action: Literal['create', 'update', 'delete']) -> str:
    cache = caches[settings.ONE_C_TASK_CACHE]
    cache_key = build_cache_key(user_id, view_name, action)

    try:
        data = json.dumps(data, cls=DjangoJSONEncoder)
    except Exception as e:
        logging.error(f"JSON dumps error on body: {data}")
        raise e

    cache.set(cache_key, data, settings.ONE_C_TASK_DATA_EXPIRE)
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


def get_from_cache(key: str):
    cache = caches[settings.ONE_C_TASK_CACHE]
    data = cache.get(key)
    cache.close()
    if data:
        return json.loads(data)


def delete_from_cache(key) -> None:
    cache = caches[settings.ONE_C_TASK_CACHE]
    cache.delete(key)
    cache.close()


def get_all_user_data_keys(user_id: int):
    cache = caches[settings.ONE_C_TASK_CACHE]
    keys = cache.keys(f'{settings.ONE_C_TASK_DATA_PREFIX}:{user_id}:*')
    cache.close()
    return keys


def get_user_notifications(user_id: int):
    cache = caches[settings.ONE_C_TASK_CACHE]
    keys = cache.keys(f'{NOTIFY_PREFIX}{settings.ONE_C_TASK_DATA_PREFIX}:{user_id}:*')
    items = cache.get_many(keys)
    cache.close()
    return items


def get_title_by_action(action: str) -> str:
    match action:
        case 'create':
            return 'cоздание'
        case 'update':
            return 'обновление'
        case _:
            return 'удаление'


def send_web_notif(
    form_data_key: str,
    title: str,
    message: str,
    status: Literal["failure", "success"],
):
    key_data = rebuild_cache_key(form_data_key)

    key = f"{NOTIFY_PREFIX}{form_data_key}"
    message_data = {
        "title": title,
        "message": message,
        "action": key_data["action"],
        "status": status,
        "time": DateFormat(timezone.now()).format('D, j M., H:i')
    }

    cache = caches[settings.ONE_C_TASK_CACHE]
    expire = settings.ONE_C_TASK_DATA_EXPIRE if status == "failure" else 300
    cache.set(key, json.dumps(message_data), expire)
    cache.close()

    send_web_push_notification(
        user_id=key_data["user_id"],
        title=title,
        msg=message,
        data={"open_url": settings.ONE_C_TASK_URL % key},
        message_type="task_message",
    )
