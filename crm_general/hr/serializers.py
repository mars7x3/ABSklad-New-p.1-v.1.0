
from rest_framework import serializers

from account.models import MyUser, StaffMagazine


class HRStaffListSerializer(serializers.ModelSerializer):
    class Meta:
        model = MyUser
        fields = ('email', 'id', 'status', 'name', 'is_active')

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        employee = instance.magazines.filter(is_active=True).first()
        rep['employee_status'] = employee.status if employee else None
        return rep


class HRStaffDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = MyUser
        fields = ('email', 'id', 'status', 'name', 'is_active')

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        rep['employee_status'] = instance.magazines.filter(is_active=True).first().status
        rep['magazines'] = HRStaffMagazineSerializer(instance.magazines, many=True, context=self.context).data
        return rep


class HRStaffMagazineSerializer(serializers.ModelSerializer):
    class Meta:
        model = StaffMagazine
        fields = '__all__'

    def create(self, validated_data):
        magazine = StaffMagazine.objects.filter(user=validated_data['user'], is_active=True).first()
        if magazine:
            magazine.is_active = False
            magazine.save()
        magazine = StaffMagazine.objects.create(**validated_data)

        return magazine

