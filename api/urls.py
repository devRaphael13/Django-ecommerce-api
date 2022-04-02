from django.urls import path, include
from rest_framework.routers import DefaultRouter
from api import views


router = DefaultRouter()
router.register('api/products', views.ProductViewSet)
router.register('api/brands', views.BrandViewSet)
router.register('api/users', views.UserViewSet)
router.register('api/categories', views.CategoryViewSet)
router.register('api/images', views.ImageViewSet)
router.register('api/bank', views.BankViewSet)
router.register('api/order', views.OrderViewSet, basename='order')
router.register('api/accounts', views.AccountDetailViewSet, basename='accounts')
router.register('api/transfer', views.TransferViewSet)
router.register('api/reviews', views.ReviewViewSet)
router.register('api/reviews', views.ReviewViewSet)
router.register('api/messages', views.MessageViewSet)

urlpatterns = [
    path('webhook', views.WebHooks.as_view(), name='webhook'),
    path('', include(router.urls)),
    ]
