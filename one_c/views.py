from django.shortcuts import render
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from one_c.utils import sync_prod_crud_1c_crm


class SyncProductCRUDVIew(APIView):
    def post(self, request):
        sync_prod_crud_1c_crm(request)
        return Response('Success!', status=status.HTTP_200_OK)

