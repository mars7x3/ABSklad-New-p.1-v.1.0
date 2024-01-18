from django.shortcuts import render
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from one_c.utils import sync_prod_crud_1c_crm, sync_category_crm_to_1c, sync_category_1c_to_crm


class SyncProductCRUDVIew(APIView):
    def post(self, request):
        sync_prod_crud_1c_crm(request)
        return Response('Success!', status=status.HTTP_200_OK)


class SyncCategoryCRUDVIew(APIView):
    def post(self, request):
        sync_category_1c_to_crm(request)
        return Response('Success!', status=status.HTTP_200_OK)


"""
- Артикул добавить в синхронизацию товара.
vendor_code

Список ПДС

"""
a = {
    "status": "Без нал",
    "is_active": 1,
    "user": "guid контрагента",
    "amount": 10000,
    "cash_box": "guid кассы",
    "uid": "guid документа",
    "created_at": "2023-12-24 24:00:00"
}