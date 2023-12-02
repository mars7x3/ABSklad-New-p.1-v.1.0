from typing import Any

from django.contrib.auth import get_user_model
from django.core.exceptions import ObjectDoesNotExist

from account.models import DealerProfile


def convert_to_int(page, default: int):
    try:
        return abs(int(page))
    except (ValueError, TypeError):
        return default


def get_limit_and_offset(req_data: dict[str, Any], max_page_size: int, default_page_size: int = 10):
    page = convert_to_int(req_data.get('page'), 1)
    limit = convert_to_int(req_data.get('page_size'), default_page_size)
    if limit > max_page_size:
        limit = max_page_size

    offset = limit * page if page > 1 else 0
    return limit, offset


def get_chat_receivers(chat):
    dealer = chat.dealer
    receivers = [dealer.username]

    profile = get_dealer_profile(dealer)
    if not profile or not profile.city:
        return receivers

    manager_usernames = list(
        get_user_model().objects.filter(
            status='manager',
            staff_profile__city=profile.city
        ).values_list("username", flat=True)
    )
    receivers += manager_usernames
    return receivers


def get_dealer_profile(user) -> DealerProfile | None:
    try:
        return user.dealer_profile
    except ObjectDoesNotExist:
        return


def get_manager_profile(user) -> DealerProfile | None:
    try:
        return user.staff_profile
    except ObjectDoesNotExist:
        return


def get_dealer_name(chat):
    dealer = chat.dealer
    profile = get_dealer_profile(dealer)
    if profile:
        return profile.name
    return dealer.get_full_name() or dealer.email
