from django.urls import path

from notification import views

urlpatterns = [
    path('subscribe/', views.subscribe, name='subscribe'),
]
