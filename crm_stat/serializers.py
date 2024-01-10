from rest_framework import serializers

from .models import PDS, Stat


class PDSSerializer(serializers.ModelSerializer):
    class Meta:
        model = PDS
        fields = '__all__'
