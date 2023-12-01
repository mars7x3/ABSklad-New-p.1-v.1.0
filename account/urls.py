from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from .views import *

router = DefaultRouter()
router.register('dealer/store/crud', DealerStoreCRUDView)
router.register('dealer/balance/list', BalanceHistoryListView)  # balance list

urlpatterns = [
    path('user/login/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('user/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),

    path('dealer/me-info/', DealerMeInfoView.as_view()),  # dealer me info
    path('dealer/balance/', DealerBalanceView.as_view()),  # dealer balance
    path('dealer/stocks-list/', DealerStockInfoView.as_view()),  # dealer stocks list

    path('dealer/notification/u/', NotificationReadView.as_view()),  # notification is_read
    path('dealer/notification/count/', NotificationCountView.as_view()),  # notification info

    path('dealer/pwd/forgot/', ForgotPwdView.as_view()),  # forgot pwd
    path('dealer/pwd/verify-code/', VerifyCodeView.as_view()),  # verify code
    path('dealer/pwd/change/', ChangePwdView.as_view()),  # change pwd

    path('dealer/profile/change/', ChangeProfileView.as_view()),  # change dealer profile
    path('dealer/send-code/', SendCodeView.as_view()),  # send code to email or phone

    path('dealer/balance/plus/', BalancePlusView.as_view()),  # balance plus






    path('', include(router.urls)),
]