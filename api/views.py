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

    def create(self, request, pk=None, *args, **kwargs):
        return Response(
            {"detail": 'Method "POST" not allowed.'}, status=status.HTTP_403_FORBIDDEN
        )

    def destroy(self, request, pk=None, *args, **kwargs):
        return Response(
            {"detail": 'Method "DELETE" not allowed.'}, status=status.HTTP_403_FORBIDDEN
        )


#     @action(detail=False, methods=['post'])
#     def update_cart(self, request, pk=None, *args, **kwargs):
#         data = request.data

#         if not data:
#             return Response({ 'product_variant_id': ['This field is required.'], 'action': ['This field is required'] }, status=status.HTTP_400_BAD_REQUEST)

#         action_choices = ('add', 'subtract', 'remove')
#         variant_id = data.get('product_variant_id', None)
#         size = data.get('size', None)
#         action = data.get('action', None)
#         quantity = int(data.get('quantity', 1))
#         res = {'errors': []}

#         if not variant_id:
#             res['errors'].append({ 'product_variant_id': ['This field is required.']})
#         else:
#             variant_id = int(variant_id)

#         if not action:
#             res['errors'].append({ 'action': ['This field is required'] })
#         else:
#             action = action.lower()

#         if action not in action_choices:
#             res['errors'].append({'action': [f'Invalid action: Your choices are {", ".join(action_choices)}']})

#         if not res['errors']:
#             cart = request.user.cart
#             variant = get_object_or_404(Variant, pk=variant_id)

#             if action == 'add':
#                 return self.add(cart, variant, size, quantity)

#             elif action == 'subtract':
#                 return self.subtract(cart, variant, quantity)

#             else:
#                 return self.remove(cart, variant)

#         return Response(res, status=status.HTTP_400_BAD_REQUEST)

#     def add(self, cart, variant, size, quantity):
#         if not variant.is_available:
#             return Response({'detail': 'This variant of this product is out of stock'}, status=status.HTTP_404_NOT_FOUND)

#         if size is None:
#             return Response({"size": ["This field is required"]}, status=status.HTTP_400_BAD_REQUEST)

#         if variant.quantity >= quantity:
#             item = cart.items.filter(variant__id=variant.id)
#             if item.exists():
#                 item = item[0]
#                 item.quantity += quantity
#                 item.save()
#                 return Response(status=status.HTTP_200_OK)

#             size = variant.sizes.filter(id=int(size))
#             if size and size.first().is_available:
#                 cart.items.add(OrderItem.objects.create(variant=variant, quantity=quantity, size=size.first()))
#                 return Response(status=status.HTTP_200_OK)
#             return Response({ "detail": "The Size of the product you're adding to cart is out of stock" }, status=status.HTTP_404_NOT_FOUND)
#         return Response({ 'detail': 'The quantity you are trying to add is greater than is available' }, status=status.HTTP_400_BAD_REQUEST)

#     def subtract(self, cart, variant, quantity):
#         if cart.items.exists():
#             item = cart.items.filter(variant__id=variant.id)
#             if item.exists():
#                 item = item[0]
#                 if quantity >= item.quantity:
#                     cart.items.remove(item)
#                     return Response({ 'detail': f"Variant of product {variant.product.name} was removed from user {cart.user}'s cart" },status=status.HTTP_200_OK)
#                 item.quantity -= quantity
#                 item.save()
#                 return Response(status=status.HTTP_200_OK)
#             return Response({ 'detail': 'Cannot reduce the quantity of an item that is not in the cart' }, status=status.HTTP_400_BAD_REQUEST)
#         return Response({ 'detail': 'Cannot alter an empty cart' }, status=status.HTTP_404_NOT_FOUND)

#     def remove(self, cart, variant):
#         if cart.items.exists():
#             item = cart.items.filter(variant__id=variant.id)
#             if item.exists():
#                 cart.items.remove(item[0])
#                 return Response(status=status.HTTP_200_OK)
#             return Response({ 'detail': 'Cannot remove an item that is not in the cart' }, status=status.HTTP_404_NOT_FOUND)
#         return Response({ 'detail': 'Cannot alter an empty cart' }, status=status.HTTP_404_NOT_FOUND)


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

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            return (permissions.AllowAny(),)
        return (IsProductOwner(),)


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


class OrderViewSet(ReadOnlyModelViewSet):
    serializer_class = OrderSerializer

    def create(self, request, *args, **kwargs):
        data = request.data
        user = request.user
        variant = data.get("variant_id", None)
        redirect_url = data["redirect_url"]
        size = data.get("size", "N/A")
        quantity = data.get("quantity", 1)
        transaction = Transaction(settings.PAYSTACK_SECRET_KEY)

        if variant_id is not None:
            # variant = Variant.objects.get(id=variant_id)
            if not (variant.is_available and variant.product.is_available):
                return Response(
                    {"detail": "Product is out of stock"},
                    status=status.HTTP_404_NOT_FOUND,
                )

            if variant.quantity >= quantity:
                size = variant.sizes.filter(size=size)
                if size and size.first().is_available:
                    item = OrderItem.objects.create(
                        variant=variant, quantity=quantity, size=size
                    )

                    order = Order.objects.create(
                        user=user,
                        order_item=item,
                    )
                    subaccount = Account.objects.get(
                        brand=variant.product.brand
                    ).subaccount_code

                    return Response(
                        transaction.initialize(
                            user.email,
                            item.get_total_amount(),
                            redirect_url,
                            subaccount=subaccount,
                            generate_reference=True,
                        ),
                        status=status.HTTP_200_OK,
                    )
                return Response(
                    {
                        "detail": "The size of the product you are trying to order is out of stock"
                    },
                    status=status.HTTP_404_NOT_FOUND,
                )
            return Response(
                {
                    "detail": "'quantity' is greater than the quantity of the product available"
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        cart = user.cart
        if cart.items.all().exists():
            order = Order.objects.create(user=user)
            return Response(
                transaction.initialize(
                    user.email,
                    user.get_cart_total(),
                    redirect_url,
                    generate_reference=True,
                ),
                status=status.HTTP_200_OK,
            )
        return Response(
            {"detail": "Your cart is empty"}, status=status.HTTP_404_NOT_FOUND
        )

    def destroy(self, request, pk=None, *args, **kwargs):
        order = self.get_object()
        order.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True)
    def verify(self, request, pk=None, *args, **kwargs):
        order = self.get_object()
        transaction = Transaction(settings.PAYSTACK_SECRET_KEY)
        return Response(transaction.verify(order.ref))

    def get_queryset(self):
        if self.request.user.is_superuser or self.request.user.is_staff:
            return Order.objects.all()
        return Order.objects.filter(user=self.request.user)

    def get_permissions(self):
        if self.action == "create":
            return (permissions.IsAuthenticated(),)
        elif self.action in ("retrieve", "verify"):
            return (permissions.OR(IsOrderer(), permissions.IsAdminUser()),)
        return (permissions.IsAdminUser(),)
