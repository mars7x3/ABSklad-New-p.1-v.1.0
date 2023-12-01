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


def change_dealer_profile(request):
    code = request.data.get('code')
    phone = request.data.get('phone')
    name = request.data.get('name')
    email = request.data.get('email')
    pwd = request.data.get('pwd')
    image = request.FILES.get('image')
    user = request.user
    dealer_profile = user.dealer_profile
    if name:
        dealer_profile.name = name
    if image:
        dealer_profile.image = image
    if code:
        if code == user.verify_codes.first():
            if phone:
                dealer_profile.phone = phone
            if email:
                user.email = email
            if pwd:
                user.pwd = pwd
                user.set_password(pwd)
        else:
            return False
    user.save()
    dealer_profile.save()
    return True
