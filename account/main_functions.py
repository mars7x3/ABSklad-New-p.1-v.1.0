def notifications_info(user):
    notifications = user.notifications.filter(is_read=False)
    chat_notifications = notifications.filter(status='chat')
    ab_notifications = notifications.exclude(status='chat')
    last_msg_chat = chat_notifications.first()
    last_msg_abs = ab_notifications.first()

    response_data = {"total_count": notifications.count()}
    if last_msg_chat:
        response_data['chat_notifications'] = {
            "count": chat_notifications.count(),
            "text": last_msg_chat.description,
            "time": last_msg_chat.created_at
        }
    if last_msg_abs:
        response_data['abs_notifications'] = {
            "count": ab_notifications.count(),
            "text": last_msg_abs.description,
            "time": last_msg_abs.created_at
        }

    return response_data
