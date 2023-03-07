from django.urls import path, include
from rest_framework.routers import DefaultRouter
from api import views


router = DefaultRouter()
router.register('api/products', views.ProductViewSet)
router.register('api/brands', views.BrandViewSet)
router.register('api/users', views.UserViewSet)
router.register('api/categories', views.CategoryViewSet)
router.register('api/images', views.ImageViewSet)
router.register('api/banks', views.BankViewSet)
router.register('api/orders', views.OrderViewSet, basename='orders')
router.register('api/accounts', views.AccountViewSet, basename='accounts')
router.register('api/transfers', views.TransferViewSet)
router.register('api/reviews', views.ReviewViewSet)
router.register('api/messages', views.MessageViewSet)
router.register('api/variants', views.VariantViewSet)
router.register('api/sizes', views.SizeViewSet)
router.register('api/size_chart', views.SizeChartViewSet)


urlpatterns = [
    path('webhook', views.WebHooks.as_view(), name='webhook'),
    path('', include(router.urls)),
    ]
