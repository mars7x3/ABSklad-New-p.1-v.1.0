from django.core.validators import MinValueValidator
from rest_framework import serializers

from order.models import MainOrder
from product.models import AsiaProduct


class OrderPartialSentSerializer(serializers.Serializer):
    order_id = serializers.PrimaryKeyRelatedField(
        queryset=MainOrder.objects.all(),
        write_only=True,
        required=True,
        many=False
    )
    products = serializers.DictField(
        child=serializers.IntegerField(validators=[MinValueValidator(1)]),
        allow_empty=False,
        required=True
    )

    def validate(self, attrs):
        order = attrs["order_id"]
        attrs["order_id"] = order.id

        product_ids = [int(p_id) for p_id in attrs["products"].keys()]
        if AsiaProduct.objects.filter(id__in=product_ids).count() != len(product_ids):
            raise serializers.ValidationError({"products": "Some product id does not exists!"})

        queryset = order.products.filter(ab_product_id__in=product_ids).values_list("ab_product_id", "count")
        for product_id, count in queryset:
            if attrs["products"][str(product_id)] > count:
                raise serializers.ValidationError(
                    {"products": 'Wrong product count data for an order shipment', "product_id": product_id}
                )
        return attrs
