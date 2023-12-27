from django.utils import timezone
from rest_framework import status

from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet
from rest_framework.mixins import ListModelMixin, RetrieveModelMixin, UpdateModelMixin, DestroyModelMixin, \
    CreateModelMixin
from rest_framework.permissions import IsAuthenticated

from account.models import DealerStatus, CRMNotification, MyUser, Notification
from product.serializers import ProductSizeSerializer
from promotion.models import Banner, Story, Motivation, Discount
from .serializers import MarketerProductSerializer, MarketerProductListSerializer, MarketerCollectionSerializer, \
    MarketerCategorySerializer, BannerSerializer, BannerListSerializer, DealerStatusSerializer, StoryListSerializer, \
    StoryDetailSerializer, ShortProductSerializer, CRMNotificationSerializer, MotivationSerializer, \
    DiscountSerializer, MarketerCRMTaskResponseSerializer
from ..models import CRMTaskResponse
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
        active_status = self.request.query_params.get('status')
        search = self.request.query_params.get('search')
        if active_status == 'active':
            queryset = queryset.filter(is_active=True)
        elif active_status == 'inactive':
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
                                     CreateModelMixin,
                                     UpdateModelMixin,
                                     GenericViewSet):
    queryset = Collection.objects.all()
    permission_classes = [IsAuthenticated, IsMarketer]
    pagination_class = ProductPagination
    serializer_class = MarketerCollectionSerializer

    def list(self, request, *args, **kwargs):
        queryset = self.queryset
        c_status = self.request.query_params.get('status')
        search = self.request.query_params.get('search')

        if c_status == 'active':
            queryset = queryset.filter(is_active=True)
        elif c_status == 'inactive':
            queryset = queryset.filter(is_active=False)

        if search:
            queryset = queryset.filter(title__icontains=search)
        paginator = GeneralPurposePagination()
        page = paginator.paginate_queryset(queryset, request)
        serializer = self.get_serializer(page, many=True, context=self.get_renderer_context()).data
        return paginator.get_paginated_response(serializer)


class MarketerCategoryModelViewSet(ListModelMixin,
                                   RetrieveModelMixin,
                                   CreateModelMixin,
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

    def get_queryset(self):
        collection_slug = self.request.query_params.get('collection_slug')
        if collection_slug:
            return self.queryset.filter(products__collection__slug=collection_slug).distinct()
        else:
            return self.queryset


class ProductSizeView(DestroyModelMixin,
                      GenericViewSet):
    queryset = ProductSize.objects.all()
    permission_classes = [IsAuthenticated, IsMarketer]
    serializer_class = ProductSizeSerializer


class MarketerBannerModelViewSet(ListModelMixin,
                                 RetrieveModelMixin,
                                 UpdateModelMixin,
                                 CreateModelMixin,
                                 GenericViewSet):
    queryset = Banner.objects.prefetch_related('cities', 'products').all()
    permission_classes = [IsAuthenticated, IsMarketer]
    serializer_class = BannerListSerializer
    retrieve_serializer_class = BannerSerializer
    pagination_class = ProductPagination

    def list(self, request, *args, **kwargs):
        queryset = self.queryset
        active_status = self.request.query_params.get('status')
        search = self.request.query_params.get('search')
        start_date = self.request.query_params.get('start_time')
        end_date = self.request.query_params.get('end_time')

        if active_status == 'active':
            queryset = queryset.filter(is_active=True)
        elif active_status == 'inactive':
            queryset = queryset.filter(is_active=False)

        if start_date and end_date:
            queryset = queryset.filter(created_at__gte=start_date, created_at__lte=end_date)

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
        category_id = self.request.query_params.get('category_id')
        products = AsiaProduct.objects.filter(category=category_id)
        serializer = ShortProductSerializer(products, many=True, context=self.get_renderer_context())
        return Response(serializer.data, status=status.HTTP_200_OK)


class MarketerDealerStatusListView(ListModelMixin, GenericViewSet):
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
        active_status = self.request.query_params.get('status')
        search = self.request.query_params.get('search')
        if active_status == 'active':
            queryset = queryset.filter(is_active=True)
        elif active_status == 'inactive':
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

    @action(methods=['GET'], detail=False, url_path='groups')
    def get_groups(self, request):
        users = DealerStatus.objects.all()
        serializer = DealerStatusSerializer(users, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class MarketerTaskView(ListModelMixin,
                       RetrieveModelMixin,
                       UpdateModelMixin,
                       GenericViewSet):
    queryset = CRMTaskResponse.objects.all()
    permission_classes = [IsAuthenticated, IsMarketer]
    serializer_class = MarketerCRMTaskResponseSerializer
    pagination_class = GeneralPurposePagination

    def get_queryset(self):
        return self.queryset.filter(executor=self.request.user.id)

    def get_serializer_context(self):
        if self.detail:
            return {'request': self.request, 'retrieve': True}
        return {'request': self.request}

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        is_done = self.request.query_params.get('is_done')
        search = self.request.query_params.get('search')
        if is_done == 'true':
            queryset = queryset.filter(is_done=True)
        if is_done == 'false':
            queryset = queryset.filter(is_done=False)

        if search:
            queryset = queryset.filter(task__title__icontains=search)
        paginator = GeneralPurposePagination()
        page = paginator.paginate_queryset(queryset, request)
        serializer = self.get_serializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)
