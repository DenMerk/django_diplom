"""
URL configuration for orders project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from goods.views import PartnerUpdate, LoginAPIView, RegisterAPIView, ProductViewSet, BasketViewSet, \
    OrderConfirmationViewSet, OrderAPIView, OrderMetaViewSet, OrderChangeStatusViewSet, OrderHistoryViewSet
from rest_framework.routers import DefaultRouter


router = DefaultRouter()
router.register(r'products', ProductViewSet, basename='products')
router.register(r'basket', BasketViewSet, basename='basket')
router.register(r'confirmation', OrderConfirmationViewSet, basename='confirmation')
router.register(r'orders', OrderMetaViewSet, basename='orders')
router.register(r'order_status', OrderChangeStatusViewSet, basename='order_status')
router.register(r'order_history', OrderHistoryViewSet, basename='order_history')

urlpatterns = [
    path("admin/", admin.site.urls),
    path('export/', PartnerUpdate.as_view()),
    path('entry/', LoginAPIView.as_view()),
    path('entry/<pk>/', LoginAPIView.as_view()),
    path('register/', RegisterAPIView.as_view()),
    path('order/<pk>/', OrderAPIView.as_view()),


] + router.urls
