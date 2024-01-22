from rest_framework import serializers

from account.models import MyUser
from general_service.models import Stock


class MainDirectorStaffCRUDSerializer(serializers.ModelSerializer):
    class Meta:
        model = MyUser
        fields = ('id', 'username', 'status', 'phone', 'email', 'is_active', 'date_joined', 'image',
                  'updated_at', 'password', 'name')


class MainDirectorStockListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Stock
        exclude = ('uid', 'is_show')

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        rep['city_title'] = instance.city.title if instance.city else '---'
        rep['prod_amount_crm'] = instance.total_sum
        rep['prod_count_crm'] = instance.total_count
        return rep

