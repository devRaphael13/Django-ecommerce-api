from django.contrib.auth.hashers import make_password
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.serializers import ValidationError


from api.models import (
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
    IsVendor,
    IsAVendor,
    IsUser,
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
)


def get_parent(query_params, queryset):
    parent = query_params.get("parent", None)
    if parent:
        if parent in ("None", "none", "null"):
            queryset = queryset.filter(parent=None)
        else:
            parent = parent.replace(" ", "")
            if parent.isdigit():
                queryset = queryset.filter(parent=parent)
            else:
                raise ValidationError(
                    {
                        "parent": [
                            "Select a valid choice. That choice is not one of the available choices."
                        ]
                    }
                )
    return queryset


class UserViewSet(ModelViewSet):
    queryset = User.objects.filter(is_active=True)
    serializer_class = UserSerializer
    filterset_fields = ["id", "first_name", "last_name", "is_active", "is_vendor", "email"]
    
    def destroy(self, request, pk=None, *args, **kwargs):
        user = self.get_object()
        user.is_active = False
        user.save()
        return Response(status=status.HTTP_204_NO_CONTENT)

    def perform_create(self, serializer):
        serializer.save(password=make_password(serializer.validated_data["password"]))

    def get_permissions(self):
        if self.action == "create":
            return (permissions.AllowAny(),)

        if self.action == "retrieve":
            return (permissions.OR(IsUser(), permissions.IsAdminUser()),)

        if self.action == "list":
            return (permissions.IsAdminUser(),)
        return (IsUser(),)


class ProductViewSet(ModelViewSet):
    queryset = Product.objects.filter(is_available=True)
    serializer_class = ProductSerializer
    filterset_fields = ["id", "name", "category", "vendor", "is_available", "price"]

    def get_permissions(self):
        if self.action == "create":
            return (IsAVendor(),)

        if self.action in ("list", "retrieve"):
            return (permissions.AllowAny(),)

        if self.action == "destroy":
            return (permissions.OR(IsVendor(), permissions.IsAdminUser()),)
        return (IsVendor(),)

    def filter_queryset(self, queryset):
        return super().filter_queryset(get_parent(self.request.query_params, queryset))


class SizeViewSet(ModelViewSet):
    queryset = Size.objects.all()
    serializer_class = SizeSerializer
    filterset_fields = ["id", "name", "product"]

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            return (permissions.AllowAny(),)
        return (IsVendor(),)


class ImageViewSet(ModelViewSet):

    queryset = Image.objects.all()
    serializer_class = ImageSerializer
    filterset_fields = ["id", "product"]

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            return (permissions.AllowAny(),)

        if self.action == "destroy":
            return (permissions.OR(IsVendor(), permissions.IsAdminUser()),)
        return (IsVendor(),)


class CategoryViewSet(ModelViewSet):

    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    filterset_fields = ["id", "name"]

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            return (permissions.AllowAny(),)
        return (permissions.IsAdminUser(),)

    def filter_queryset(self, queryset):
        return super().filter_queryset(get_parent(self.request.query_params, queryset))


class VendorViewSet(ModelViewSet):
    queryset = Vendor.objects.all()
    serializer_class = VendorSerializer
    filterset_fields = ["id", "name", "user"]

    def perform_create(self, serializer):
        user = self.request.user
        serializer.save(user=user)
        if not user.is_vendor:
            user.is_vendor = True
            user.save()

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            return (permissions.AllowAny(),)
        elif self.action == "create":
            return (permissions.IsAuthenticated(),)
        return (permissions.OR(IsUser(), permissions.IsAdminUser()),)


class OrderItemViewSet(ModelViewSet):
    serializer_class = OrderItemSerializer
    queryset = OrderItem.objects.all()
    filterset_fields = ["id", "user", "product"]

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def get_permissions(self):
        return (permissions.OR(permissions.IsAdminUser(), IsUser()),)


class ReviewViewSet(ModelViewSet):
    queryset = Review.objects.all()
    serializer_class = ReviewSerializer
    filterset_fields = ["id", "stars", "user", "product"]

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            return (permissions.AllowAny(),)

        if self.action == "create":
            return (permissions.OR(CanReview(), permissions.IsAdminUser()),)
        return (permissions.OR(IsUser(), permissions.IsAdminUser()),)


class OrderViewSet(ModelViewSet):
    serializer_class = OrderSerializer
    queryset = Order.objects.all()
    filterset_fields = ["id", "user", "completed"]

    def update(self, request, *args, **kwargs):
        return Response(
            {"detail": 'Method "PUT" not allowed.'},
            status=status.HTTP_405_METHOD_NOT_ALLOWED,
        )

    def partial_update(self, request, *args, **kwargs):
        return Response(
            {"detail": 'Method "PATCH" not allowed.'},
            status=status.HTTP_405_METHOD_NOT_ALLOWED,
        )

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def get_permissions(self):
        if self.action == "create":
            return (permissions.IsAuthenticated(),)
        return (permissions.OR(IsUser(), permissions.IsAdminUser()),)
