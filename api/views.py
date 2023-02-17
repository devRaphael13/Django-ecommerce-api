import os
import redis
from unittest.mock import patch
from concurrent.futures import ThreadPoolExecutor
from collections import defaultdict

from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.core.mail import send_mail
from django.forms import ValidationError
from django.shortcuts import get_object_or_404
from django.contrib.auth.hashers import make_password
from django.http.response import Http404

from py4paystack.routes.transactions import Transaction
from py4paystack.routes.transfer_recipient import TransferRecipient 
from py4paystack.routes.transfers import Transfer
from py4paystack.routes.subaccount import SubAccounts
from py4paystack.routes.verification import Verification

from rest_framework.exceptions import PermissionDenied
from rest_framework.decorators import action
from rest_framework.views import APIView
from rest_framework import status, viewsets
from rest_framework.response import Response
from rest_framework import permissions

from api.permissions import (
    IsAccountOwner, 
    IsOrderer,
    IsOwnerByBrand, 
    IsProductOwner, 
    CanReview, 
    IsTheBrandOwner, 
    IsABrandOwner, 
    IsUser
)

from api.models import (
    Account, 
    Color, 
    Message, 
    OrderItem, 
    Size, 
    Transfer, 
    Product, 
    Category, 
    Brand, 
    Order, 
    Review, 
    User, 
    Cart, 
    Image, 
    Bank, 
    Transfer, 
    Variant
)

from api.serializers import (
    ColorSerializer, 
    MessageSerializer, 
    ImageSerializer, 
    SizeSerializer, 
    UserSerializer,
    UserSerializerPlus,
    ProductSerializer,
    ProductSerializerPlus,
    CategorySerializer, 
    BrandSerializer, 
    OrderSerializer, 
    AccountSerializer, 
    BankSerializer, 
    TransferSerializer, 
    ReviewSerializer, 
    VariantSerializer
)

redis_client = redis.Redis(host='localhost', port=6379, db=0)



# user
class CustomSerializerViewSet(viewsets.ModelViewSet):

    def get_serializer_class(self):
        if self.action in ( "create", "update", "partial_update", "retrieve") and hasattr(self, "serializer_class_plus"):
            return self.serializer_class_plus
        return super().get_serializer_class()


class UserViewSet(CustomSerializerViewSet):
    
    serializer_class = UserSerializer
    serializer_class_plus = UserSerializerPlus
    queryset = User.objects.all()

    def get_serializer_class(self):
        if self.action == "retrieve" and hasattr(self, "retrieve_serializer_class"):
            return self.retrieve_serializer_class
        return super().get_serializer_class()

    def create(self, request, *args, **kwargs):
        res = {}
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        res['token'] = serializer.instance.auth_token.key
        res.update(serializer.data)
        return Response(res, status=status.HTTP_201_CREATED, headers=headers)

    def destroy(self, request, pk=None, *args, **kwargs):
        user = self.get_object()
        user.is_active = False
        user.save()
        return Response(status=status.HTTP_204_NO_CONTENT)


    def perform_create(self, serializer):
        serializer.save(password=make_password(serializer.validated_data['password']))


    @action(detail=False, methods=['post'])  
    def update_cart(self, request, pk=None, *args, **kwargs):
        data = request.data

        if not data:
            return Response({ 'product_variant_id': ['This field is required.'], 'action': ['This field is required'] }, status=status.HTTP_400_BAD_REQUEST)
        
        action_choices = ('add', 'subtract', 'remove')
        variant_id = int(data.get('product_variant_id', None))
        size = data.get('size', 'N/A')
        action = data.get('action', None)
        quantity = int(data.get('quantity', 1))
        res = {'errors': []}

        if not variant_id:
            res['errors'].append({ 'product_variant_id': ['This field is required.']})

        if not action:
            res['errors'].append({ 'action': ['This field is required'] })
        else:
            action = action.lower()

        if action not in action_choices:
            res['errors'].append({'action': [f'Invalid action: Your choices are {", ".join(action_choices)}']})
        
        if not res['errors']:
            cart = request.user.cart
            variant = get_object_or_404(Variant, pk=variant_id)

            if action == 'add':
                return self.add(cart, variant, quantity)

            elif action == 'subtract':
                return self.subtract(cart, variant, quantity)

            else:
                return self.remove(cart, variant)

        return Response(res, status=status.HTTP_400_BAD_REQUEST)
                    
    def add(self, cart, variant, quantity):
        if not variant.is_available:
            return Response({'detail': 'This variant of this product is out of stock'}, status=status.HTTP_404_NOT_FOUND)

        if variant.quantity >= quantity:
            item = cart.items.filter(variant__id=variant.id)
            if item.exists():
                item = item[0]
                item.quantity += quantity
                item.save()
                return Response(status=status.HTTP_200_OK)

            cart.items.add(OrderItem.objects.create(variant=variant, size=size, quantity=quantity))
            return Response(status=status.HTTP_200_OK)
        return Response({ 'detail': 'The quantity you are trying to add is greater than is available' }, status=status.HTTP_400_BAD_REQUEST)

    def subtract(self, cart, variant, quantity):
        if cart.items.exists():
            item = cart.items.filter(variant__id=variant.id)
            if item.exists():
                item = item[0]
                if quantity >= item.quantity:
                    cart.items.remove(item)
                    return Response({ 'detail': f"Variant of product {variant.product.name} was removed from user {cart.user}'s cart" },status=status.HTTP_200_OK)
                item.quantity -= quantity
                item.save()
                return Response(status=status.HTTP_200_OK)
            return Response({ 'detail': 'Cannot reduce the quantity of an item that is not in the cart' }, status=status.HTTP_400_BAD_REQUEST)
        return Response({ 'detail': 'Cannot alter an empty cart' }, status=status.HTTP_404_NOT_FOUND)    

    def remove(self, cart, variant):
        if cart.items.exists():
            item = cart.items.filter(variant__id=variant.id)
            if item.exists():
                cart.items.remove(item[0])
                return Response(status=status.HTTP_200_OK)
            return Response({ 'detail': 'Cannot remove an item that is not in the cart' }, status=status.HTTP_404_NOT_FOUND)
        return Response({ 'detail': 'Cannot alter an empty cart' }, status=status.HTTP_404_NOT_FOUND)  


# Products *

class ProductViewSet(CustomSerializerViewSet):

    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    serializer_class_plus = ProductSerializerPlus

    def get_permissions(self):
        if self.action == 'create':
            return IsABrandOwner(),
        elif self.action in ('list', 'retrieve'):
            return permissions.AllowAny(),
        return IsOwnerByBrand(),


# colors of variants / products *

class ColorViewSet(viewsets.ModelViewSet):

    queryset = Color.objects.all()
    serializer = ColorSerializer

    def get_permissions(self):
        if self.action in ('list', 'retrieve'):
            return permissions.AllowAny(),
        return permissions.OR(permissions.IsAdminUser(), IsABrandOwner())

# Sizes of products

class SizeViewSet(viewsets.ModelViewSet):

    queryset = Size.objects.all()
    serializer = SizeSerializer

    def check_quantity(self, variant, quantity):
        total_quantity = variant.quantity
        if quantity > total_quantity or sum(variant.size_set.only('quantity')) + quantity > total_quantity:
            raise ValidationError("You cannot have more sizes for a product than the product itself!")

    def get_permissions(self):
        if self.action in ('list', 'retrieve'):
            return permissions.AllowAny(),
        return permissions.OR(permissions.IsAdminUser(), IsABrandOwner())

    def perform_create(self, serializer):
        self.check_quantity(serializer.validated_data['variant'], serializer.validated_data['quantity'])
        serializer.save()

    def perform_update(self, serializer):
        self.check_quantity(serializer.validated_data['variant'], serializer.validated_data['quantity'])
        serializer.save()

        
# Variants of a product 

class VariantViewSet(viewsets.ModelViewSet):

    queryset = Variant.objects.all()
    serializer_class = VariantSerializer

    def check_quantity(self, product, quantity):
        total_products = product.quantity
        if quantity > total_products or sum(product.variant_set.only('quantity'))  + quantity > total_products:
            raise ValidationError('Variant quantity cannot be greater than that of the Product itself.')

    def perform_update(self, serializer):
        self.check_quantity(serializer.validated_data['product'], serializer.validated_data['quantity'])
        serializer.save()

    def perform_create(self, serializer):
        self.check_quantity(serializer.validated_data['product'], serializer.validated_data['quantity'])
        serializer.save()

    def get_permissions(self):
        if self.action in ('list', 'retrieve'):
            return permissions.AllowAny(),
        return IsProductOwner(),

# Product Images/ connect this to cloudinary........
class ImageViewSet(viewsets.ModelViewSet):

    queryset = Image.objects.all()
    serializer_class = ImageSerializer

    def get_permissions(self):
        if self.action in ('list', 'retrieve'):
            return permissions.AllowAny()
        return IsProductOwner()

# Category

class CategoryViewSet(viewsets.ModelViewSet):

    queryset = Category.objects.all()
    serializer_class = CategorySerializer

    def get_permissions(self):
        if self.action in ('list', 'retrieve'):
            return permissions.AllowAny(),
        return permissions.IsAdminUser(),


# Bank *

class BankViewSet(viewsets.ModelViewSet):

    queryset = Bank.objects.all()
    serializer_class = BankSerializer

    def get_permissions(self):
        if self.action in ('list', 'retrieve'):
            return permissions.IsAuthenticated(),
        return permissions.IsAdminUser(),


# Brand *

class BrandViewSet(viewsets.ModelViewSet):
    queryset = Brand.objects.all()
    serializer_class = BrandSerializer

    def perform_create(self, serializer):
        user = self.request.user
        serializer.save(owner=user)
        if not user.is_brand_owner:
            user.is_brand_owner = True
            user.save()
        
    def create(self, request, *args, **kwargs):
        # Add cloudinary magic 
        return super().create(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        if 'logo' in request.data:
            pass # Add cloudinary to the update...
        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.logo:
            pass # Delete from cloudinary
        return super().destroy(request, *args, **kwargs)

    def get_permissions(self):
        if self.action in ('list', 'retrieve'):
            return permissions.AllowAny(),
        elif self.action == 'create':
            return permissions.IsAuthenticated(),
        return IsTheBrandOwner(),

# Messages *

class MessageViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Message.objects.all()
    serializer_class = MessageSerializer

    def get_permissions(self):
        if self.action == 'list':
            return permissions.IsAdminUser(),
        return IsOwnerByBrand(),

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# Reviews *
 
class ReviewViewSet(viewsets.ModelViewSet):
    queryset = Review.objects.all()
    serializer_class = ReviewSerializer

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def get_permissions(self):
        if self.action == 'list':
            return permissions.AllowAny(),
        elif self.action in ('create', 'retrieve'):
            return permissions.IsAuthenticated(),
        return CanReview(),

# Account Details *

class AccountViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = AccountSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(res, status=status.HTTP_201_CREATED, headers=headers)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
        
    def perform_create(self, serializer):
        data = self.create_account(
            serializer.validated_data["acct_no"], 
            Bank.objects.get(id=serializer.validated_data["bank"]), 
            Brand.objects.get(id=serializer.validated_data['brand'])
            )

        serializer.validated_data.update({ "acct_name": data[0], "subaccount_code": data[1], "recipient_code": data[2] })
        serializer.save()        
    

    def create_account(self, acct_number, bank_code, brand):
        verify = Verification(settings.PAYSTACK_SECRET_KEY)
        verify = verify.resolve_acct_number(acct_number, bank_code)

        if not verify['status']:
            raise ValidationError("The account number provided doesn't seem to belong to the bank chosen")

        recipient = TransferRecipient(settings.PAYSTACK_SECRET_KEY).create("nuban", brand.name, brand.owner.email)
        subaccount = SubAccounts(settings.PAYSTACK_SECRET_KEY).create(brand.name, bank.code, acct_no, 100 - brand.percentage)

        return verify['data']['account_name'], subaccount['data']['subaccount_code'], recipient['data']['recipient_code']

    def get_permissions(self):
        if self.action == 'create':
            permission_classes = (IsABrandOwner(),)
        elif self.action == 'list':
            permission_classes = (permissions.IsAdminUser(),)
        elif self.action == 'retrieve':
            permission_classes = (permissions.OR(permissions.IsAdminUser(), IsAccountOwner()),)
        else:
            permission_classes = (IsAccountOwner(),)
        return permission_classes

    def get_queryset(self):
        if self.request.user.is_superuser or self.request.user.is_staff:
            return Account.objects.all()
        return Account.objects.filter(brand__owner=self.request.user)


# Orders

class OrderViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = OrderSerializer

    def create(self, request, *args, **kwargs):
        data = request.data
        user = request.user
        variant = data.get('variant_id', None)
        redirect_url = data['redirect_url']
        size = data.get('size', 'N/A')
        quantity = data.get('quantity', 1)
        transaction = Transaction(settings.PAYSTACK_SECRET_KEY)

        if variant_id is not None:
            variant = Variant.objects.get(id=variant_id)
            if not ( variant.is_available and variant.product.is_available ):
                return Response({'detail': 'Product is out of stock'}, status=status.HTTP_404_NOT_FOUND)

            if variant.quantity >= quantity:
                size = variant.size_set.filter(size=size)
                if size:
                    if size.first().is_available:
                        item = OrderItem.objects.create(
                            variant=variant,
                            quantity=quantity,
                            size=size
                        )

                        order = Order.objects.create(
                            user=user,
                            order_item=item,
                        )
                        subaccount = Account.objects.get(brand=variant.product.brand).subaccount_code

                        return Response(transaction.initialize(user.email, item.get_total_amount(), redirect_url, subaccount=subaccount, generate_reference=True), status=status.HTTP_200_OK)
                    return Response({ 'detail': "The size of the product you are trying to order is out of stock" }, status=status.HTTP_404_NOT_FOUND)
            return Response({ 'detail': "'quantity' is greater than the quantity of the product available" }, status=status.HTTP_400_BAD_REQUEST)

        cart = user.cart
        if cart.items.all().exists(): 
            order = Order.objects.create(
                    user=user
                )
            return Response(transaction.initialize(user.email, user.get_cart_total(), redirect_url, generate_reference=True), status=status.HTTP_200_OK)
        return Response({ 'detail': 'Your cart is empty' }, status=status.HTTP_404_NOT_FOUND)

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
        if self.action == 'create_order':
            return permissions.IsAuthenticated(),
        elif self.action in ('retrieve', 'verify'):
            return permissions.OR(IsOrderer(), permissions.IsAdminUser()),
        return permissions.IsAdminUser(),
# Transfers

class TransferViewSet(viewsets.ReadOnlyModelViewSet):

    queryset = Transfer.objects.all()
    serializer_class = TransferSerializer
    permission_classes = (permissions.IsAdminUser,)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    
    @action(detail=False, methods=['post'])
    def transfer(self, request, *args, **kwargs):
        records = Transfer.objects.filter(paid=False).select_related('brand').select_related('brand__account')
                        
        if records.exists():
            reason = 'Payment for products provided'

            transfers = []
            for record in records:
                recipient = record.brand.account.recipient_code
                transfers.append({'amount': record.amount, 'recipient': recipient, 'reference': record.ref, 'reason': reason})

            if transfers :
                res = paystack.bulk_transfer(transfers)
            return Response(res, status=status.HTTP_200_OK)
        return Response({ 'detail': 'All debts have been paid!' }, status=status.HTTP_204_NO_CONTENT)   

# Webhook for paystack api

class WebHooks(APIView):

    MESSAGES = {
        'order.successful': "You've got an order!!{}",
        'transfer.successful': "You've just been paid!!, your money is on the way{}",
        'transfer.failed': "Transfer to the account you provided failed, check the account details in your account.\nIf after 24 hours you still haven't been paid, reply this email stating your username and your brand name{}",
        'transfer.reversed': "Transfer to you was reversed, please wait you'll still be paid with the next batch within the next 24 hours{}",
        'product.unavailable': "You've got some products that are out of stock{}",
        'product_variant.unavailable': "Some variations of your products are out of stock, remember to update them when they arrive{}",
        'variant_size.unavailable': "Sizes of some of your products are unavailable{}"
    } 
    # *(func, [args])
    def use_threadpool(*func_with_args):
        with ThreadPoolExecutor() as executor:
            for func, args in func_with_args:
                executor.submit(func, *args)

    def get_order(self, pk):
        try:
            order = Order.objects.select_related().select_related('order_item__variant').get(pk=pk)
        except Order.DoesNotExist:
            raise Http404
        return order

    def message(self, message, status, brand, user=None, *items):
        message = Message.objects.create(
            message=message.format(''),
            status=status,
            brand=brand,
            user=user,
        )
        if items:
            message.order_items.add(*items)

        
    def mail(self, status, brand):
        send_mail(
            "You've got notifications",
            self.MESSAGES[status].format(', check your dashboard for further details.\nYours faithfully\n{}.'.format(settings.BRAND_NAME)),
            settings.EMAIL_HOST_USER,
            [brand.owner.email],
            fail_silently=False
        )


    def update_product(self, user, *item):
        for x in item:
            variant = x.variant
            quantity = x.quantity
            size = x.size
            product = variant.product

            variant.quantity -= quantity
            size.quantity -= quantity
            product.customers.add(user)

            if product.quantity <= 0:
                product.is_available = False
                product.quantity = 0
                self.use_threadpool(
                    (self.message, [self.MESSAGES['product.unavailable'], 'product.unavailable', product.brand]),
                    (self.mail, ['product.unavailable', product.brand])
                    )

            if variant.quantity <= 0:
                variant.is_available = False
                variant.quantity = 0
                self.use_threadpool(
                    (self.message, [self.MESSAGES['product_variant.unavailable'], 'product_variant.unavailable', product.brand]),
                    (self.mail, ['product_variant.unavailable', product.brand])
                )

            if size.quantity <= 0:
                size.is_available = False
                size.quantity = 0
                self.use_threadpool(
                    (self.message, [self.MESSAGES['variant_size.unavailable', 'variant_size.unavailable', product.brand]]),
                    (self.mail, ['variant_size.unavailable', product.brand])
                )

            product.save()
            variant.save()
            size.save()

    def record(self, brand, *items):
        total = 0
        for x in items:
            total += x.get_total_amount()

        Transfer.objects.create(
                    brand=brand,
                    amount=total * (1.0 - brand.percentage),
                )

    @csrf_exempt
    def post(self, request, format=None):

        data = request.data

        if data['event'] == 'charge.success':
            ref = data['data']['reference']
            order = self.get_object(ref)
            order.completed = True
            order.save()
            if order.order_item:
                brand = order.order_item.product.brand
                self.use_threadpool(
                    (self.update_product, [order.user, order.order_item]),
                    (self.record, [brand, order.order_item]),
                    (self.message, [self.MESSAGES['order.successful'],'order.successful', brand, order.user, order.order_item]),
                    (self.mail, ["order.successful", brand])
                )

            else:
                self.update_product(order.user, *order.cart.items.all())
                data_dict = defaultdict(list)
                for order_item in order.cart.items.all():
                    data_dict[order_item.product.brand].append(order_item)
                
                for brand in data_dict:
                    self.use_threadpool(
                        (self.record, [brand, *data_dict[brand]]),
                        (self.message, [self.MESSAGES['order.successful'],'order.successful', brand, order.user, *data_dict[brand]]),
                        (self.mail, ['order.successful', brand])
                    )

        elif data['event'] == 'transfer.success':
            ref = data['data']['reference']
            transfer = get_object_or_404(Transfer, ref=ref)
            transfer.paid = True
            transfer.code = data['data']['transfer_code']
            transfer.save()
            self.use_threadpool(
                (self.message, [self.MESSAGES['transfer.successful'], 'transfer.successful', transfer.brand]),
                (self.mail, ['transfer.successful', transfer.brand])
            )

        elif data['event'] == 'transfer.failed':
            brand = get_object_or_404(Transfer, ref=data['data']['reference']).brand
            self.use_threadpool(
                (self.message, [self.MESSAGES['transfer.failed'], 'transfer.failed', brand]),
                (self.mail, ['transfer.failed', brand])
            )

        elif data['event'] == 'transfer.reversed':
            ref = data['data']['reference']
            transfer = get_object_or_404(Transfer, ref=ref)
            transfer.paid = False
            transfer.save()
            brand = transfer.brand
            self.use_threadpool(
                (self.message, [self.MESSAGES['transfer.reversed'], 'transfer.reversed', brand]),
                (self.mail, ['transfer.reversed', brand])
            )
        return Response(status=status.HTTP_200_OK)