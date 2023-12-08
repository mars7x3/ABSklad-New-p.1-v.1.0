from rest_framework import serializers

from account.models import ManagerProfile
from crm_general.serializers import BaseProfileSerializer
from general_service.models import City
from general_service.serializers import CitySerializer


class RopManagerSerializer(BaseProfileSerializer):
    city = CitySerializer(many=False, read_only=True)
    city_id = serializers.PrimaryKeyRelatedField(
        queryset=City.objects.filter(is_active=True),
        write_only=True,
        required=True
    )

    class Meta:
        model = ManagerProfile
        fields = ("user", "city", "city_id")
        user_status = "manager"

    def validate(self, attrs):
        city = attrs.get("city_id")
        if city:
            if city not in self.context['rop_profile'].cities:
                raise serializers.ValidationError({"city_id": "Не найдено или не доступно!"})

            attrs['city'] = city
        return attrs



