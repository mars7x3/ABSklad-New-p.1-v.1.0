from django.shortcuts import render
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from one_c.utils import sync_prod_crud_1c_crm, sync_category_1c_to_crm, sync_dealer_1C_to_back, \
    order_1c_to_crm, sync_1c_money_doc_crud, sync_1c_price_city_crud, sync_1c_user_city_crud, sync_1c_stock_crud, \
    sync_1c_prod_count_crud, sync_1c_prod_price_crud, sync_1c_inventory_crud, sync_1c_movement_crud, sync_1c_return_crud


class SyncProductCRUDView(APIView):
    def post(self, request):
        print(request.data)
        sync_prod_crud_1c_crm(request.data)
        return Response('Success!', status=status.HTTP_200_OK)


class SyncCategoryCRUDView(APIView):
    def post(self, request):
        print(request.data)
        sync_category_1c_to_crm(request.data)
        return Response('Success!', status=status.HTTP_200_OK)


class SyncDealerCRUDView(APIView):
    def post(self, request):
        print(request.data)
        sync_dealer_1C_to_back(request)
        return Response('Success!', status=status.HTTP_200_OK)


class SyncOrderCRUDView(APIView):
    def post(self, request):
        print(request.data)
        order_1c_to_crm(request.data)
        return Response('Success!', status=status.HTTP_200_OK)


class SyncMoneyDocCRUDView(APIView):
    def post(self, request):
        print(request.data)
        is_ok, text = sync_1c_money_doc_crud(request.data)
        if is_ok:
            return Response(text, status=status.HTTP_200_OK)
        return Response(text, status=status.HTTP_400_BAD_REQUEST)


class SyncPriceTypeCRUDView(APIView):
    def post(self, request):
        print(request.data)
        is_ok, text = sync_1c_price_city_crud(request.data)
        if is_ok:
            return Response(text, status=status.HTTP_200_OK)
        return Response(text, status=status.HTTP_400_BAD_REQUEST)


class SyncUserCityCRUDView(APIView):
    def post(self, request):
        print(request.data)
        is_ok, text = sync_1c_user_city_crud(request.data)
        if is_ok:
            return Response(text, status=status.HTTP_200_OK)
        return Response(text, status=status.HTTP_400_BAD_REQUEST)


class SyncStockCRUDView(APIView):
    def post(self, request):
        print(request.data)
        is_ok, text = sync_1c_stock_crud(request.data)
        if is_ok:
            return Response(text, status=status.HTTP_200_OK)
        return Response(text, status=status.HTTP_400_BAD_REQUEST)


class SyncProdCountCRUDView(APIView):
    def post(self, request):
        print(request.data)
        is_ok, text = sync_1c_prod_count_crud(request.data)
        if is_ok:
            return Response(text, status=status.HTTP_200_OK)
        return Response(text, status=status.HTTP_400_BAD_REQUEST)


class SyncProdPriceCRUDView(APIView):
    def post(self, request):
        print(request.data)
        # is_ok, text = sync_1c_prod_price_crud(request.data)
        # if is_ok:
        #     return Response(text, status=status.HTTP_200_OK)
        return Response("text", status=status.HTTP_400_BAD_REQUEST)


class SyncInventoryCRUDView(APIView):
    def post(self, request):
        print(request.data)
        is_ok, text = sync_1c_inventory_crud(request.data)
        if is_ok:
            return Response(text, status=status.HTTP_200_OK)
        return Response("text", status=status.HTTP_400_BAD_REQUEST)


class SyncMovementCRUDView(APIView):
    def post(self, request):
        print(request.data)
        is_ok, text = sync_1c_movement_crud(request.data)
        if is_ok:
            return Response(text, status=status.HTTP_200_OK)
        return Response("text", status=status.HTTP_400_BAD_REQUEST)


class SyncReturnCRUDView(APIView):
    def post(self, request):
        print(request.data)
        is_ok, text = sync_1c_return_crud(request.data)
        if is_ok:
            return Response(text, status=status.HTTP_200_OK)
        return Response("text", status=status.HTTP_400_BAD_REQUEST)

