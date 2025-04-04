from django.db.models import Q
from django.utils import timezone
from rest_framework import status

from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import GenericViewSet
from rest_framework.mixins import ListModelMixin, RetrieveModelMixin, UpdateModelMixin, DestroyModelMixin, \
    CreateModelMixin
from rest_framework.permissions import IsAuthenticated

from account.models import DealerStatus, CRMNotification, MyUser, Notification, DealerProfile
from product.serializers import ProductSizeSerializer
from promotion.models import Banner, Story, Motivation, Discount
from .serializers import MarketerProductSerializer, MarketerProductListSerializer, MarketerCollectionSerializer, \
    MarketerCategorySerializer, BannerSerializer, BannerListSerializer, DealerStatusSerializer, StoryListSerializer, \
    StoryDetailSerializer, ShortProductSerializer, CRMNotificationSerializer, MotivationSerializer, \
    DiscountSerializer, HitProductSerializer, AutoNotificationSerializer
from ..models import CRMTask, AutoNotification
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
        queryset = self.get_queryset()
        active_status = self.request.query_params.get('status')
        search = self.request.query_params.get('search')
        category_slug = self.request.query_params.get('category_slug')
        collection_slug = self.request.query_params.get('collection_slug')
        if active_status == 'active':
            queryset = queryset.filter(is_active=True)
        elif active_status == 'inactive':
            queryset = queryset.filter(is_active=False)

        if category_slug:
            queryset = queryset.filter(category__slug=category_slug)

        if collection_slug:
            queryset = queryset.filter(collection__slug=collection_slug)

        if search:
            queryset = queryset.filter(title__icontains=search)

        serializer = self.get_serializer(queryset, many=True, context=self.get_renderer_context())
        return Response(serializer.data, status=status.HTTP_200_OK)

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
    serializer_class = MarketerCollectionSerializer

    # def list(self, request, *args, **kwargs):
    #     queryset = self.queryset
    #     c_status = self.request.query_params.get('status')
    #     search = self.request.query_params.get('search')
    #
    #     if c_status == 'active':
    #         queryset = queryset.filter(is_active=True)
    #     elif c_status == 'inactive':
    #         queryset = queryset.filter(is_active=False)
    #
    #     if search:
    #         queryset = queryset.filter(title__icontains=search)
    #
    #     serializer = ShortProductSerializer(queryset, many=True, context=self.get_renderer_context())
    #     return Response(serializer.data, status=status.HTTP_200_OK)


class MarketerCategoryModelViewSet(ListModelMixin,
                                   RetrieveModelMixin,
                                   CreateModelMixin,
                                   UpdateModelMixin,
                                   GenericViewSet):
    queryset = Category.objects.filter(is_active=True)
    permission_classes = [IsAuthenticated, IsMarketer]
    serializer_class = MarketerCategorySerializer

    def get_serializer_context(self):
        if self.detail:
            return {'request': self.request, 'retrieve': True}
        return {'request': self.request}

    def get_queryset(self):
        collection_slug = self.request.query_params.get('collection_slug')
        queryset = Category.objects.filter(is_active=True)
        if collection_slug:
            return queryset.filter(products__collection__slug=collection_slug).distinct()
        else:
            return queryset


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
    queryset = Banner.objects.prefetch_related('products').all()
    permission_classes = [IsAuthenticated, IsMarketer]
    serializer_class = BannerListSerializer
    retrieve_serializer_class = BannerSerializer
    pagination_class = ProductPagination

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
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
        products = AsiaProduct.objects.filter(category=category_id, is_active=True)
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
        queryset = self.get_queryset()
        active_status = self.request.query_params.get('status')
        search = self.request.query_params.get('search')
        start_time = self.request.query_params.get('start_time')
        end_time = self.request.query_params.get('end_time')
        if active_status == 'active':
            queryset = queryset.filter(is_active=True)
        elif active_status == 'inactive':
            queryset = queryset.filter(is_active=False)

        if start_time and end_time:
            queryset = queryset.filter(start_date__gte=start_time, end_date__lte=end_time)

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
        queryset = self.get_queryset()
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
        naive_time = timezone.localtime().now()
        today = timezone.make_aware(naive_time)
        motivations = Motivation.objects.filter(start_date__gte=today)
        serializer = MotivationSerializer(motivations, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(methods=['GET'], detail=False, url_path='actions')
    def get_actions(self, request):
        naive_time = timezone.localtime().now()
        today = timezone.make_aware(naive_time)
        actions = Discount.objects.filter(start_date__gte=today)
        serializer = DiscountSerializer(actions, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class MarketerProductHitsListView(ListModelMixin, GenericViewSet):
    queryset = AsiaProduct.objects.filter(is_hit=True).order_by('-updated_at')
    permission_classes = [IsAuthenticated, IsMarketer]
    serializer_class = HitProductSerializer


class MarketerNotificationView(APIView):
    permission_classes = [IsAuthenticated, IsMarketer]

    def get(self, request):
        user = self.request.user
        tasks_count = CRMTask.objects.filter(status='created', executors=user).count()

        data = {
            'tasks_count': tasks_count,
        }

        return Response(data, status=status.HTTP_200_OK)


class AutoNotificationViewSet(ListModelMixin,
                              UpdateModelMixin,
                              RetrieveModelMixin,
                              CreateModelMixin,
                              GenericViewSet):
    queryset = AutoNotification.objects.all()
    permission_classes = [IsAuthenticated, IsMarketer]
    serializer_class = AutoNotificationSerializer

    @action(methods=['GET'], detail=False, url_path='object-statuses')
    def get_obj_statuses(self, request):
        balance = self.request.query_params.get('balance')
        order = self.request.query_params.get('order')
        if order:
            object_statuses = [value for value, display in AutoNotification.OBJ_STATUS]
        elif balance:
            object_statuses = ['created', 'rejected', 'success']
        else:
            object_statuses = []

        return Response(object_statuses, status.HTTP_200_OK)

    def list(self, request, *args, **kwargs):
        query_param = self.request.query_params.get('status')
        queryset = self.get_queryset()
        if query_param:
            queryset = queryset.filter(status=query_param)
        serializer = self.get_serializer(queryset, many=True)

        return Response(serializer.data)
