from django.db.models import Sum, F, IntegerField, ExpressionWrapper, DecimalField, Avg
from rest_framework import status
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.views import APIView
from rest_framework.response import Response

from crm_general.accountant.serializers import MyOrderListSerializer
from order.models import MyOrder
from .models import PDS, Stat
from .serializers import PDSSerializer


class PDSByCityView(APIView):
    def get(self, request, *args, **kwargs):
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        cities = self.request.query_params.getlist('cities')

        if cities:
            queryset = PDS.objects.filter(user__dealer_profile__city__in=cities)
        else:
            queryset = PDS.objects.filter(created_at__date__gte=start_date, created_at__date__lte=end_date)

        cities_data = (queryset.values('user__dealer_profile__city__id', 'user__dealer_profile__city__title')
                       .annotate(
                            bank_in=Sum('bank_income'),
                            box_income=Sum('box_office_income'),
                            total_income=Sum('bank_income') + Sum('box_office_income'),
                            avg_check=Avg('bank_income') + Avg('box_office_income'),
                        ))

        total_data = queryset.aggregate(
            total_income=Sum('bank_income') + Sum('box_office_income'),
            total_bank_income=Sum('bank_income'),
            total_box_office_income=Sum('box_office_income'),
            avg_bank_income=Avg('bank_income'),
            avg_box_office_income=Avg('box_office_income')
        )

        total_data['total_avg_check'] = round(total_data['avg_bank_income'] + total_data['avg_box_office_income'])

        total_data.pop('avg_bank_income')
        total_data.pop('avg_box_office_income')

        cities_data_result = list(cities_data)
        cities_data_result.append({'total_data': total_data})

        return Response(cities_data_result, status=status.HTTP_200_OK)


class PDSByCityDetail(APIView):
    def get(self, request, *args, **kwargs):
        city = self.request.query_params.get('city_id')
        queryset = PDS.objects.filter(user__dealer_profile__city=city)
        city_data = queryset.values('user__name').annotate(
            bank_in=Sum('bank_income'),
            box_income=Sum('box_office_income'),
            total_income=Sum('bank_income') + Sum('box_office_income'),
            avg_check=round(Avg('bank_income') + Avg('box_office_income')),
        )

        total_data = queryset.aggregate(
            total_income=Sum('bank_income') + Sum('box_office_income'),
            total_bank_income=Sum('bank_income'),
            total_box_office_income=Sum('box_office_income'),
            total_avg_check=round(Avg('bank_income') + Avg('box_office_income'))
        )
        city_data_result = list(city_data)
        city_data_result.append({'total_data': total_data})
        return Response(city_data_result)


class SalesByCityView(APIView):
    def get(self, request, *args, **kwargs):
        queryset = Stat.objects.all()
        sales_data = queryset.values('user__dealer_profile__city__title').annotate(
            quantity=Sum('count'),
            amount_price=Sum('amount'),
            avg_check=round(Sum('amount') / Sum('count')),
        )
        total_stats = Stat.objects.aggregate(
            total_count=Sum('count'),
            total_amount=Sum('amount')
        )

        sales_data_with_total = list(sales_data)
        sales_data_with_total.append({'total_stats': {'total_count': total_stats['total_count'] or 0,
                                                      'total_amount': total_stats['total_amount'] or 0}})

        return Response(sales_data_with_total)


class LimitOffsetView(APIView):
    def get(self, request):
        orders = MyOrder.objects.all()
        print(orders)
        paginator = LimitOffsetPagination()
        page = paginator.paginate_queryset(orders, request)
        serializer = MyOrderListSerializer(page, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
