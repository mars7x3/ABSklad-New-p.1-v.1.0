async def validate_user_active(user):
    return user.is_active


async def validate_is_manager(user):
    return user.is_manager


async def validate_is_dealer(user):
    return user.is_dealer
