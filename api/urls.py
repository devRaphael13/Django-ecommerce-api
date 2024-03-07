from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views


router = DefaultRouter()
router.register("api/products", views.ProductViewSet)
router.register('api/vendors', views.VendorViewSet)
router.register("api/users", views.UserViewSet)
router.register("api/carts", views.CartViewSet)
router.register("api/categories", views.CategoryViewSet)
router.register("api/images", views.ImageViewSet)
router.register("api/orders", views.OrderViewSet, basename="orders")
router.register("api/order-items", views.OrderItemViewSet)
router.register("api/reviews", views.ReviewViewSet)
router.register("api/sizes", views.SizeViewSet)


urlpatterns = [
    path("", include(router.urls)),
]
