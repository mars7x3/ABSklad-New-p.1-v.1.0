from rest_framework import generics, filters, permissions
from rest_framework.response import Response

from crm_general.permissions import IsStaff
from .filters import GroupedByStockDateFilter
from .models import PurchaseStat, StockStat
from .serializers import StockStatSerializer


class StockGroupedStatsAPIView(generics.ListAPIView):
    permission_classes = (permissions.IsAuthenticated, IsStaff)
    queryset = PurchaseStat.objects.all()
    serializer_class = StockStatSerializer
    filter_backends = (GroupedByStockDateFilter, filters.OrderingFilter)
    ordering_fields = ("stock_title", "stat_date", "incoming_bank_amount", "incoming_cash_amount",
                       "sales_products_count", "sales_amount", "sales_count", "sales_users_count", "sales_avg_check",
                       "dealers_incoming_funds", "dealers_products_count", "dealers_amount", "dealers_avg_check",
                       "products_amount", "products_user_count", "products_avg_check")

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
