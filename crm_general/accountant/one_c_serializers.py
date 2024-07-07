from rest_framework import serializers

from account.models import BalancePlus


class BalancePlusModerationSerializer(serializers.Serializer):
    balance_id = serializers.PrimaryKeyRelatedField(
        queryset=BalancePlus.objects.filter(is_moderation=False),
        many=False,
        required=True,
        write_only=True
    )
    is_success = serializers.BooleanField(required=True, write_only=True)
    type_status = serializers.CharField(required=True, write_only=True)

    def validate(self, attrs):
        attrs["balance_id"] = attrs["balance_id"].id
        match attrs["type_status"]:
            case 'cash':
                attrs['status'] = 'Нал'
            case _:
                attrs['status'] = 'Без нал'
        return attrs
