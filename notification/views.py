import json

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from notification.models import Subscription


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def subscribe(request):
    subscription_data = json.loads(request.body)
    if Subscription.objects.filter(user=request.user, subscription_info=subscription_data).exists():
        return Response(status=204)

    Subscription(user=request.user, subscription_info=subscription_data).save()
    return Response({"message": "Subscription added successfully"}, status=201)


@api_view(['POST'])
def unsubscribe(request):
    subscription_data = json.loads(request.body)
    query = Subscription.objects.filter(subscription_info=subscription_data)
    if not query.exists():
        return Response(status=404)
    query.delete()
    return Response(status=204)
