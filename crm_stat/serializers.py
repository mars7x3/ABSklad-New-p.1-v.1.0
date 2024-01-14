from rest_framework import serializers


class StockStatSerializer(serializers.Serializer):
    stock_title = serializers.CharField()
    stat_date = serializers.DateField()
    stock_id = serializers.IntegerField()

    incoming_bank_amount = serializers.DecimalField(decimal_places=2, max_digits=20, default=0)
    incoming_cash_amount = serializers.DecimalField(decimal_places=2, max_digits=20, default=0)

    sales_products_count = serializers.IntegerField(default=0)
    sales_amount = serializers.DecimalField(decimal_places=2, max_digits=20, default=0)
    sales_count = serializers.IntegerField(default=0)
    sales_users_count = serializers.IntegerField(default=0)
    sales_avg_check = serializers.DecimalField(decimal_places=2, max_digits=20, default=0)

    dealers_incoming_funds = serializers.DecimalField(decimal_places=2, max_digits=20, default=0)
    dealers_products_count = serializers.IntegerField(default=0)
    dealers_amount = serializers.DecimalField(max_digits=20, decimal_places=2, default=0)
    dealers_avg_check = serializers.DecimalField(max_digits=20, decimal_places=2, default=0)

    products_amount = serializers.DecimalField(max_digits=20, decimal_places=2, default=0)
    products_user_count = serializers.IntegerField(default=0)
    products_avg_check = serializers.DecimalField(max_digits=20, decimal_places=2, default=0)
