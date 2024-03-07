from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor

from django.conf import settings
from django.contrib.auth.hashers import make_password
from django.core.mail import send_mail
from django.http.response import Http404
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet

from api.models import (
    Cart,
    Category,
    Image,
    Order,
    OrderItem,
    Product,
    Review,
    Size,
    User,
    Vendor,
)
from api.permissions import (
    CanReview,
    IsABrandOwner,
    IsAccountOwner,
    IsOrderer,
    IsOwnerByBrand,
    IsProductOwner,
    IsBrandOwner,
    IsUser,
    CanEditSize,
)
from api.serializers import (
    CategorySerializer,
    VendorSerializer,
    ImageSerializer,
    OrderSerializer,
    OrderItemSerializer,
    ProductSerializer,
    ReviewSerializer,
    SizeSerializer,
    UserSerializer,
    CartSerializer,
)

from .mixin import (
    CustomCreateMixin,
    CustomDestroyMixin,
    CustomListMixin,
    CustomModelViewSet,
    CustomReadOnlyViewSet,
    CustomRetrieveMixin,
    CustomUpdateMixin,
    redis_client,
)


# Mods
class CustomSerializer:

    def get_serializer_class(self):
        if self.action == "retrieve" and hasattr(self, "serializer_class_plus"):
            return self.serializer_class_plus
        return super().get_serializer_class()


class UserViewSet(ModelViewSet):
    queryset = User.objects.filter(is_active=True)
    serializer_class = UserSerializer

    def destroy(self, request, pk=None, *args, **kwargs):
        user = self.get_object()
        user.is_active = False
        user.save()
        return Response(status=status.HTTP_204_NO_CONTENT)

    def perform_create(self, serializer):
        serializer.save(password=make_password(serializer.validated_data["password"]))


class CartViewSet(ModelViewSet):
    queryset = Cart.objects.all()
    serializer_class = CartSerializer

    def create(self, request, *args, **kwargs):
        return Response(
            {"detail": 'Method "POST" not allowed.'}, status=status.HTTP_403_FORBIDDEN
        )

    def destroy(self, request, pk=None, *args, **kwargs):
        return Response(
            {"detail": 'Method "DELETE" not allowed.'}, status=status.HTTP_403_FORBIDDEN
        )


class ProductViewSet(ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    permission_classes = [permissions.IsAuthenticated]


class SizeViewSet(ModelViewSet):
    queryset = Size.objects.all()
    serializer_class = SizeSerializer


class ImageViewSet(ModelViewSet):

    queryset = Image.objects.all()
    serializer_class = ImageSerializer

    # def get_permissions(self):
    #     if self.action in ("list", "retrieve"):
    #         return (permissions.AllowAny(),)
    #     return (IsProductOwner(),)


class CategoryViewSet(ModelViewSet):

    queryset = Category.objects.all()
    serializer_class = CategorySerializer

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            return (permissions.AllowAny(),)
        return (permissions.IsAdminUser(),)


class VendorViewSet(ModelViewSet):
    queryset = Vendor.objects.all()
    serializer_class = VendorSerializer

    def perform_create(self, serializer):
        user = self.request.user
        serializer.save(owner=user)
        if not user.is_vendor:
            user.is_vendor = True
            user.save()

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            return (permissions.AllowAny(),)
        elif self.action == "create":
            return (permissions.IsAuthenticated(),)
        return (IsBrandOwner(),)


class OrderItemViewSet(ModelViewSet):
    serializer_class = OrderItemSerializer
    queryset = OrderItem.objects.all()
    

class ReviewViewSet(CustomModelViewSet):
    queryset = Review.objects.all()
    serializer_class = ReviewSerializer

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            return (permissions.AllowAny(),)
        return (CanReview(),)


class OrderViewSet(ModelViewSet):
    serializer_class = OrderSerializer
    queryset = Order.objects.all()
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
        