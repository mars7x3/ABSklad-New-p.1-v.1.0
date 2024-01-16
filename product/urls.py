from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import *

router = DefaultRouter()
router.register('dealer/review/cd', ReviewCDView)  # create/delete review

router.register('dealer/collection/list', CollectionListView)
router.register('dealer/category/list', CategoryListView)
router.register('dealer/product/list', ProductListView)
router.register('dealer/product/list/hit', HitProductListView)

router.register('product/info', ProductLinkView)


urlpatterns = [
    path('dealer/product/reviews/list/', ReviewListView.as_view()),
    path('dealer/product/price/max-min/', FilterMaxMinView.as_view()),

    path('', include(router.urls)),
]
