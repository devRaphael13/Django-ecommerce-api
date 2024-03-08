from django.contrib.auth.hashers import make_password
from rest_framework import permissions, status
from rest_framework.response import Response
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


class UserViewSet(ModelViewSet):
    queryset = User.objects.filter(is_active=True)
    serializer_class = UserSerializer

    def destroy(self, request, pk=None, *args, **kwargs):
        user = self.get_object()
        cart = user.cart
        user.is_active = False
        cart.is_active = False
        cart.save()
        user.save()
        return Response(status=status.HTTP_204_NO_CONTENT)

    def perform_create(self, serializer):
        serializer.save(password=make_password(serializer.validated_data["password"]))

    def get_permissions(self):
        if self.action == "create":
            return permissions.AllowAny(),
        
        if self.action == "retrieve":
            return permissions.OR(permissions.IsAdminUser(), IsUser()),
        
        if self.action == "list":
            return permissions.IsAdminUser(),
        return permissions.IsAdminUser(),
        
# List, Retrieve, Update, P-Update, Delete, Create

class CartViewSet(ModelViewSet):
    queryset = Cart.objects.filter(is_active=True)
    serializer_class = CartSerializer

    def create(self, request, *args, **kwargs):
        return Response(
            {"detail": 'Method "POST" not allowed.'}, status=status.HTTP_403_FORBIDDEN
        )

    def destroy(self, request, pk=None, *args, **kwargs):
        return Response(
            {"detail": 'Method "DELETE" not allowed.'}, status=status.HTTP_403_FORBIDDEN
        )
    
    def get_permissions(self):
        if self.action == "retrieve":
            return permissions.OR(permissions.IsAdminUser(), IsUser()),
        
        if self.action == "list":
            return permissions.IsAdminUser(),
        return IsUser(),


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


class ReviewViewSet(ModelViewSet):
    queryset = Review.objects.all()
    serializer_class = ReviewSerializer

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class OrderViewSet(ModelViewSet):
    serializer_class = OrderSerializer
    queryset = Order.objects.all()

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
