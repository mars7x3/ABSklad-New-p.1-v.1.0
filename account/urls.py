from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from .views import *

router = DefaultRouter()
router.register('dealer-store-crud', DealerStoreCRUDView, basename="dealer-store-crud")
router.register('dealer/balance/plus/list', BalancePlusListView)  # balance list
router.register('dealer/transaction/history/list', BalanceHistoryListView)
router.register('dealer/profile/change', ChangeProfileView)  # change dealer profile

urlpatterns = [
    path('user/login/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('user/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),

    path('dealer/me-info/', DealerMeInfoView.as_view()),  # dealer me info
    path('dealer/my-balance/', DealerBalanceView.as_view()),  # dealer balance
    path('dealer/stocks-list/', DealerStockInfoView.as_view()),  # dealer stocks list

    path('dealer/notification/u/', NotificationReadView.as_view()),  # notification is_read
    path('dealer/notification/info/', NotificationCountView.as_view()),  # notification info

    path('dealer/send-code/', ForgotPwdView.as_view()),  # forgot pwd
    path('dealer/pwd/verify-code/', VerifyCodeView.as_view()),  # verify code
    path('dealer/pwd/change/', ChangePwdView.as_view()),  # change pwd

    path('dealer/balance/plus/', BalancePlusView.as_view()),  # balance plus

    path('', include(router.urls)),
]
