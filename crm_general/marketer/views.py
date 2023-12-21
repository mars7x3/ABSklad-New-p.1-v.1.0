from django.utils import timezone
from rest_framework import status

from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet, GenericViewSet
from rest_framework.mixins import ListModelMixin, RetrieveModelMixin, UpdateModelMixin, DestroyModelMixin, \
    CreateModelMixin
from rest_framework.permissions import IsAuthenticated

from account.models import DealerStatus, CRMNotification, MyUser, Notification
from product.serializers import ProductSizeSerializer
from promotion.models import Banner, Story, Motivation, Discount
from .serializers import MarketerProductSerializer, MarketerProductListSerializer, MarketerCollectionSerializer, \
    MarketerCategorySerializer, BannerSerializer, BannerListSerializer, DealerStatusSerializer, StoryListSerializer, \
    StoryDetailSerializer, ShortProductSerializer, CRMNotificationSerializer, MotivationSerializer, \
    ParticipantsSerializer, DiscountSerializer
from ..paginations import ProductPagination, GeneralPurposePagination
from product.models import AsiaProduct, Collection, Category, ProductSize
from .permissions import IsMarketer


class MarketerProductRUViewSet(ListModelMixin, RetrieveModelMixin, UpdateModelMixin, GenericViewSet):
    queryset = AsiaProduct.objects.all().select_related('collection')
    serializer_class = MarketerProductListSerializer
    retrieve_serializer_class = MarketerProductSerializer
    permission_classes = [IsAuthenticated, IsMarketer]
    pagination_class = ProductPagination

    def list(self, request, *args, **kwargs):
        queryset = self.queryset
        status = self.request.query_params.get('status')
        search = self.request.query_params.get('search')
        if status == 'active':
            queryset = queryset.filter(is_active=True)
        elif status == 'inactive':
            queryset = queryset.filter(is_active=False)

        if search:
            queryset = queryset.filter(title__icontains=search)

        paginator = ProductPagination()
        page = paginator.paginate_queryset(queryset, request)
        serializer = self.get_serializer(page, many=True, context=self.get_renderer_context()).data
        return paginator.get_paginated_response(serializer)

    def get_serializer_class(self):
        if self.detail:
            return self.retrieve_serializer_class
        return self.serializer_class


class MarketerCollectionModelViewSet(ListModelMixin,
                                     RetrieveModelMixin,
                                     UpdateModelMixin,
                                     GenericViewSet):
    queryset = Collection.objects.all()
    permission_classes = [IsAuthenticated, IsMarketer]
    pagination_class = ProductPagination
    serializer_class = MarketerCollectionSerializer


class MarketerCategoryModelViewSet(ListModelMixin,
                                   RetrieveModelMixin,
                                   UpdateModelMixin,
                                   GenericViewSet):
    queryset = Category.objects.all()
    permission_classes = [IsAuthenticated, IsMarketer]
    pagination_class = ProductPagination
    serializer_class = MarketerCategorySerializer

    def get_serializer_context(self):
        if self.detail:
            return {'request': self.request, 'retrieve': True}
        return {'request': self.request}


class ProductSizeDestroyView(DestroyModelMixin, GenericViewSet):
    queryset = ProductSize.objects.all()
    permission_classes = [IsAuthenticated, IsMarketer]
    serializer_class = ProductSizeSerializer


class MarketerBannerModelViewSet(ListModelMixin,
                                 RetrieveModelMixin,
                                 UpdateModelMixin,
                                 GenericViewSet):
    queryset = Banner.objects.prefetch_related('cities', 'products').all()
    permission_classes = [IsAuthenticated, IsMarketer]
    serializer_class = BannerListSerializer
    retrieve_serializer_class = BannerSerializer
    pagination_class = ProductPagination

    def list(self, request, *args, **kwargs):
        queryset = self.queryset
        status = self.request.query_params.get('status')
        search = self.request.query_params.get('search')

        if status == 'active':
            queryset = queryset.filter(is_active=True)
        elif status == 'inactive':
            queryset = queryset.filter(is_active=False)

        if search:
            queryset = queryset.filter(title__icontains=search)
        paginator = GeneralPurposePagination()
        page = paginator.paginate_queryset(queryset, request)
        serializer = self.get_serializer(page, many=True, context=self.get_renderer_context()).data
        return paginator.get_paginated_response(serializer)

    def get_serializer_class(self):
        if self.detail:
            return self.retrieve_serializer_class
        return self.serializer_class

    @action(methods=['GET'], detail=False, url_path='products/add')
    def get_products_for_banner(self, request, *args, **kwargs):
        banner_products = Banner.objects.values_list('products')
        products = AsiaProduct.objects.exclude(id__in=banner_products)
        paginator = GeneralPurposePagination()
        page = paginator.paginate_queryset(products, request)
        serializer = ShortProductSerializer(page, many=True, context=self.get_renderer_context())
        return paginator.get_paginated_response(serializer.data)


class DealerStatusListView(ListModelMixin, GenericViewSet):
    queryset = DealerStatus.objects.all()
    permission_classes = [IsAuthenticated, IsMarketer]
    serializer_class = DealerStatusSerializer


class MarketerStoryViewSet(ListModelMixin,
                           RetrieveModelMixin,
                           CreateModelMixin,
                           UpdateModelMixin,
                           GenericViewSet):
    queryset = Story.objects.all()
    permission_classes = [IsAuthenticated, IsMarketer]
    serializer_class = StoryListSerializer
    retrieve_serializer_class = StoryDetailSerializer

    def list(self, request, *args, **kwargs):
        queryset = self.queryset
        status = self.request.query_params.get('status')
        search = self.request.query_params.get('search')
        if status == 'active':
            queryset = queryset.filter(is_active=True)
        elif status == 'inactive':
            queryset = queryset.filter(is_active=False)

        if search:
            try:
                id_value = int(search)
                queryset = queryset.filter(id=id_value)
            except ValueError:
                queryset = queryset.filter(title__icontains=search)
        paginator = GeneralPurposePagination()
        page = paginator.paginate_queryset(queryset, request)
        serializer = self.get_serializer(page, many=True, context=self.get_renderer_context())
        return paginator.get_paginated_response(serializer.data)

    def get_serializer_class(self):
        if self.detail:
            return self.retrieve_serializer_class
        return self.serializer_class


class CRMNotificationView(ListModelMixin,
                          RetrieveModelMixin,
                          UpdateModelMixin,
                          CreateModelMixin,
                          GenericViewSet):
    queryset = CRMNotification.objects.all()
    permission_classes = [IsAuthenticated, IsMarketer]
    serializer_class = CRMNotificationSerializer
    pagination_class = GeneralPurposePagination

    def list(self, request, *args, **kwargs):
        queryset = self.queryset
        total_push = Notification.objects.filter(is_push=True).count()
        total_read = Notification.objects.filter(is_read=True).count()
        search = self.request.query_params.get('search')

        if search:
            queryset = queryset.filter(title__icontains=search)

        paginator = GeneralPurposePagination()
        page = paginator.paginate_queryset(queryset, request)
        serializer = self.get_serializer(page, many=True, context=self.get_renderer_context())
        response_data = {'results': serializer.data, 'total_push': total_push, 'total_read': total_read}

        return paginator.get_paginated_response(response_data)

    @action(methods=['GET'], detail=False, url_path='motivations')
    def get_motivations(self, request):
        motivations = Motivation.objects.filter(start_date__gte=timezone.now())
        serializer = MotivationSerializer(motivations, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(methods=['GET'], detail=False, url_path='actions')
    def get_actions(self, request):
        actions = Discount.objects.filter(start_date__gte=timezone.now())
        serializer = DiscountSerializer(actions, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(methods=['GET'], detail=False, url_path='participants')
    def get_participants(self, request):
        users = MyUser.objects.filter(status='dealer')
        serializer = ParticipantsSerializer(users, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
