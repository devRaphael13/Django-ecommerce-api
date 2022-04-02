import os
from django.forms import ValidationError
import redis
from unittest.mock import patch

from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.core.mail import send_mail
from django.shortcuts import get_object_or_404
from collections import defaultdict
from django.contrib.auth.hashers import make_password
from django.http.response import Http404
from rest_framework.exceptions import PermissionDenied
from rest_framework.decorators import action
from rest_framework.views import APIView
from rest_framework import status, viewsets
from rest_framework.response import Response
from rest_framework import permissions
from api.permissions import IsAccountOwner, IsOrderer,IsOwnerByBrand, IsProductOwner, IsReviewer, IsTheBrandOwner, IsABrandOwner, IsUser
from api.models import AccountDetail, Color, Message, OrderItem, Size, Transfer, Product, Category, Brand, Order, Review, User, Cart, Image, Bank, Transfer, Variant
from api.serializers import ColorSerializer, MessageSerializer, ImageSerializer, SizeSerializer, UserSerializer, ProductSerializer, CategorySerializer, BrandSerializer, OrderSerializer, AccountDetailSerializer, BankSerializer, TransferSerializer, ReviewSerializer, VariantSerializer
from api.paystack import Paystack

redis_client = redis.Redis(host='localhost', port=6379, db=0)
paystack = Paystack()


# user
class UserViewSet(viewsets.ModelViewSet):
    
    serializer_class = UserSerializer
    queryset = User.objects.all()

    def create(self, request, *args, **kwargs):
        res = {}
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        res['token'] = serializer.instance.auth_token.key
        res.update(serializer.data)
        return Response(res, status=status.HTTP_201_CREATED, headers=headers)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        if 'images' in request.data:
            os.remove(instance.pic.path)
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(serializer.data)

    def destroy(self, request, pk=None, *args, **kwargs):
        user = self.get_object()
        user.is_active = False
        user.save()
        return Response(status=status.HTTP_204_NO_CONTENT)

    def get_permissions(self):
        if self.action in ('list', 'retrieve'):
            permission_classes = (permissions.IsAdminUser(),)
        elif self.action == 'create':
            permission_classes = (permissions.AllowAny(),)
        else:
            permission_classes = (IsUser(),)
        return permission_classes

    def perform_create(self, serializer):
        serializer.save(password=make_password(serializer.validated_data['password']))


    @action(detail=False, methods=['post'])  
    def update_cart(self, request, pk=None, *args, **kwargs):
        data = request.data
        if not data:
            return Response({ 'product_variant_id': ['This field is required.'], 'action': ['This field is required'] }, status=status.HTTP_400_BAD_REQUEST)
        actions = ('add', 'subtract', 'remove')
        variant = int(data.get('product_variant_id', None))
        size = data.get('size', 'N/A')
        action = data.get('action', None)
        quantity = int(data.get('quantity', 1))
        res = {'errors': []}

        if not variant:
            res['errors'].append({ 'product_variant_id': ['This field is required.']})

        if not action:
            res['errors'].append({ 'action': ['This field is required'] })
        else:
            action = action.lower()

        if action not in actions:
            res['errors'].append({'action': ['Invalid action']})
        
        if not res['errors']:
            cart = request.user.cart
            variant = get_object_or_404(Variant, pk=variant)

            if action == 'add':
                if not variant.is_available:
                    return Response({'detail': 'This variant of this product is out of stock'}, status=status.HTTP_404_NOT_FOUND)

                if variant.quantity >= quantity:
                    if cart.items.exists():
                        item = cart.items.filter(variant=variant)
                        if item:
                            item, = item
                            item.quantity += quantity
                            item.save()
                            return Response(status=status.HTTP_200_OK)
                    
                    cart.items.add(OrderItem.objects.create(variant=variant, size=size, quantity=quantity))
                    return Response(status=status.HTTP_200_OK)
                return Response({ 'detail': 'Cannot add more product than available to cart' }, status=status.HTTP_404_NOT_FOUND)
                
            elif action == 'subtract':
                if cart.items.exists():
                    item = cart.items.filter(variant=variant)
                    if item:
                        item, = item
                        if quantity >= item.quantity:
                            cart.items.remove(item)
                            return Response(status=status.HTTP_200_OK)
                        item.quantity -= quantity
                        item.save()
                        return Response(status=status.HTTP_200_OK)
                    return Response(
                    { 'detail': 'Cannot reduce the quantity of an item that is not in the cart' },
                    status=status.HTTP_404_NOT_FOUND
                    )
                return Response(
                    { 'detail': 'Cannot alter an empty cart' },
                    status=status.HTTP_404_NOT_FOUND
                )    
            else:
                if cart.items.exists():
                    item = cart.items.filter(variant=variant)
                    if item:
                        item, = item
                        cart.items.remove(item)
                        return Response(status=status.HTTP_200_OK)
                    return Response(
                    { 'detail': 'Cannot remove an item that is not in the cart' },
                    status=status.HTTP_404_NOT_FOUND
                    )
                return Response(
                    { 'detail': 'Cannot alter an empty cart' },
                    status=status.HTTP_404_NOT_FOUND
                )   
        return Response(res, status=status.HTTP_400_BAD_REQUEST)
                    

# Products

class ProductViewSet(viewsets.ModelViewSet):

    queryset = Product.objects.all()
    serializer_class = ProductSerializer

    def get_permissions(self):
        if self.action == 'create':
            return IsABrandOwner(),
        elif self.action in ('list', 'retrieve'):
            return permissions.AllowAny(),
        return IsOwnerByBrand(),


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
        v_total = variant.quantity
        if quantity > v_total:
            raise ValidationError('Size quantity cannot be greater than that of the Variant.')

        s_total = sum(variant.size_set.only('quantity'))
        if s_total + quantity > v_total:
            raise ValidationError('Total Sizes quantity cannot be greater than that of the Variant product itself.')

    def get_permissions(self):
        if self.action in ('list', 'retrieve'):
            return permissions.AllowAny(),
        return permissions.OR(permissions.IsAdminUser(), IsABrandOwner())

    def perform_create(self, serializer):
        self.check_quantity(serializer.validated_data['variant'], serializer.validated_data['quantity'])
        serializer.save()

# Variants of a product 

class VariantViewSet(viewsets.ModelViewSet):

    queryset = Variant.objects.all()
    serializer_class = VariantSerializer

    def check_quantity(self, product, quantity):
        p_total = product.quantity
        if quantity > p_total:
            raise ValidationError('Variant quantity cannot be greater than that of the Product itself.')
        
        v_total = sum(product.variant_set.only('quantity'))
        if v_total + quantity > p_total:
            raise ValidationError('Total Variants quantity cannot be greater than that of the product itself. Update the Product quantity if you have made new purchases.')


    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        if request.user != serializer.validated_data['product'].brand.owner:
            raise PermissionDenied("You do not have permission to perform this action")
        self.check_quantity(serializer.validated_data['product'], serializer.validated_data['quantity'])
        self.perform_create(serializer)
        return Response(serializer.data, status=status)
    
    def perform_update(self, serializer):
        self.check_quantity(serializer)
        serializer.save()

    def get_permissions(self):
        if self.action in ('list', 'retrieve'):
            return permissions.AllowAny(),
        elif self.action == 'create':
            return IsABrandOwner(),
        return IsProductOwner(),

# Product Images

class ImageViewSet(viewsets.ModelViewSet):

    queryset = Image.objects.all()
    serializer_class = ImageSerializer

    def update(self, request, *args, **kwargs):
        if 'images' in request.data:
            instance = self.get_object()
            os.remove(instance.images.path)
        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        os.remove(instance.images.path)
        return super().destroy(request, *args, **kwargs)

    def get_permissions(self):
        if self.action in ('create', 'update', 'partial_update','delete'):
            return IsABrandOwner(), IsProductOwner()
        return permissions.AllowAny(),

# Category

class CategoryViewSet(viewsets.ModelViewSet):

    queryset = Category.objects.all()
    serializer_class = CategorySerializer

    def get_permissions(self):
        if self.action in ('list', 'retrieve'):
            return permissions.AllowAny(),
        return permissions.IsAdminUser(),


# Bank

class BankViewSet(viewsets.ModelViewSet):

    queryset = Bank.objects.all()
    serializer_class = BankSerializer

    def get_permissions(self):
        if self.action in ('list', 'retrieve'):
            return permissions.IsAuthenticated(),
        return permissions.IsAdminUser(),


# Brand

class BrandViewSet(viewsets.ModelViewSet):
    queryset = Brand.objects.all()
    serializer_class = BrandSerializer

    def perform_create(self, serializer):
        user = self.request.user
        serializer.save(owner=user)
        if not user.is_brand_owner:
            user.is_brand_owner = True
            user.save()
        
    def update(self, request, *args, **kwargs):
        if 'logo' in request.data:
            instance = self.get_object()
            os.remove(instance.logo.path)
        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.logo:
            os.remove(instance.logo.path)
        return super().destroy(request, *args, **kwargs)

    def get_permissions(self):
        if self.action in ('list', 'retrieve'):
            return permissions.AllowAny(),
        elif self.action == 'create':
            return permissions.IsAuthenticated(),
        return IsTheBrandOwner(),

# Messages

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


# Reviews
 
class ReviewViewSet(viewsets.ModelViewSet):
    queryset = Review.objects.all()
    serializer_class = ReviewSerializer
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        if not request.user in serializer.validated_data['product'].customers.all():
            raise PermissionDenied("You do not have permission to perform this action")
        self.perform_create(serializer)
        return Response(serializer.data, status=status)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def get_permissions(self):
        if self.action == 'list':
            return permissions.AllowAny(),
        elif self.action in ('create', 'retrieve'):
            return permissions.IsAuthenticated(),
        return IsReviewer(),

# Account Details

class AccountDetailViewSet(viewsets.ModelViewSet):
    serializer_class = AccountDetailSerializer

    def check(self, serializer, action):
        acct_no = serializer.validated_data.get('acct_no', None)
        bank = serializer.validated_data.get('bank', None)

        if action == 'create':
            brand = serializer.validated_data['brand']


        elif action == 'update':
            brand = serializer.instance.brand
            acct_name = serializer.validated_data.get('acct_name', None)
            if not all((acct_name, acct_no, bank)):
                serializer.save()
                return

        res1 = paystack.resolve(acct_no, bank.code)
        if not res1['status']:
            raise ValidationError("The account number provided doesn't seem to belong to the bank chosen")
        res2 = paystack.transfer_recipient(brand.name, acct_no, bank.code)
        serializer.save(acct_name=res1['data']['account_name'], recipient_code=res2['data']['recipient_code'])

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
            return AccountDetail.objects.all()
        return AccountDetail.objects.filter(brand__owner=self.request.user)

    def perform_create(self, serializer):
        self.check(serializer, 'create')

    def perform_update(self, serializer):
        self.check(serializer, 'update')


# Orders

class OrderViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = OrderSerializer

    def get_queryset(self):
        if self.request.user.is_superuser or self.request.user.is_staff:
            return Order.objects.all()
        return Order.objects.filter(user=self.request.user)

    def destroy(self, request, pk=None, *args, **kwargs):
        order = self.get_object()
        order.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    def get_permissions(self):
        if self.action == 'create_order':
            return permissions.IsAuthenticated(),
        elif self.action in ('retrieve', 'verify'):
            return permissions.OR(IsOrderer(), permissions.IsAdminUser()),
        return permissions.IsAdminUser(),

    @action(detail=True, permission_classes=(IsOrderer(),))
    def verify(self, request, pk=None, *args, **kwargs):
        order = self.get_object()
        return Response(paystack.verify(order.ref))

    def get_object(self, pk):
        try:
            variant = Variant.objects.select_related('product').get(pk=pk)
        except Variant.DoesNotExist:
            raise Http404
        return variant

    @action(detail=False, methods=['post'], permission_classes=(permissions.IsAuthenticated,))
    def create_order(self, request, *args, **kwargs):
        data = request.data
        user = request.user
        variant = data.get('product_variant_id', None)
        size = data.get('size', 'N/A')
        quantity = int(data.get('quantity', 1))
        
        if variant:
            
            variant = self.get_object(variant)
            
            if not ( variant.is_available and variant.product.is_available ):
                return Response({'detail': 'Product is out of stock'}, status=status.HTTP_404_NOT_FOUND)

            if variant.quantity >= quantity:
                size = variant.size_set.filter(size=size)
                if size:
                    size,= size
                    if size.is_available:
                        item = OrderItem.objects.create(
                            variant=variant,
                            quantity=quantity,
                            size=size
                        )

                        order = Order.objects.create(
                            user=user,
                            order_item=item,
                        )
                        return Response(paystack.transaction(user.email, item.get_total_amount(), order.ref), status=status.HTTP_200_OK)
                    return Response({ 'detail': "The size of the product you are trying to order is not available" }, status=status.HTTP_404_NOT_FOUND)
                return Response({ 'detail': "The size you are trying to order does not exist" }, status=status.HTTP_404_NOT_FOUND)
            return Response({ 'detail': "'quantity' is greater than the quantity of the product available" }, status=status.HTTP_400_BAD_REQUEST)


        if user.cart.items.all().exists():
            order = Order.objects.create(
                user=user
            )
            return Response(paystack.transaction(user.email, user.get_cart_total(), order.ref), status=status.HTTP_200_OK)
        return Response({ 'detail': 'The User provided has no products in his/her cart' }, status=status.HTTP_404_NOT_FOUND)


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

        records = Transfer.objects.filter(paid=False)\
            .select_related('brand')\
                .select_related('brand__owner')
                        
        if records.exists():
            response = {}
            reason = 'Payment for products provided'
            accounts = AccountDetail.objects.all().select_related('bank')

            transfers = []
            errors = {
                'status': 'failed',
                'detail': 'Brands have not added any bank account details to their account',
                'data': []
            }

            for record in records:
                accts = accounts.filter(brand=record.brand)
                if accts.exists():
                    recipient = accts.get(in_use=True).recipient_code
                    transfers.append({'amount': record.amount, 'recipient': recipient, 'reference': record.ref, 'reason': reason})
                else:
                    errors['data'].append(record.brand.name)
                    continue

            if transfers :
                res = paystack.bulk_transfer(transfers)
                if res['status']:
                    response.update({'transfers': {'status': 'success', 'detail': 'Your transfers are being processed'}})
            if errors['data']:
                response.update({'errors': errors})
            
            if response.get('transfers', None) is None:
                return Response(response, status=status.HTTP_404_NOT_FOUND)
            return Response(response, status=status.HTTP_200_OK)
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
    
    def get_object(self, pk):
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
        assert status in self.MESSAGES
        send_mail(
            status.replace('_', ' ').replace('.', ' '),
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
                self.message(self.MESSAGES['product.unavailable'], 'product.unavailable', product.brand)
            
            if variant.quantity <= 0:
                variant.is_available = False
                variant.quantity = 0
                self.message(self.MESSAGES['product_variant.unavailable'], 'product_variant.unavailable', product.brand)
                self.mail('product_variant.unavailable', product.brand)

            if size.quantity <= 0:
                size.is_available = False
                size.quantity = 0
                self.message(self.MESSAGES['variant_size.unavailable'], 'variant_size.unavailable', product.brand)
                self.mail('variant_size.unavailable', product.brand)

            product.save()
            variant.save()
            size.save()

    def record(self, brand, *items):
        total = 0
        for x in items:
            total += x.get_total_amount()

        Transfer.objects.create(
                    brand=brand,
                    amount=total * 0.9,
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
                self.update_product(order.user, order.order_item)
                self.record(brand, order.order_item)
                self.message(self.MESSAGES['order.successful'],'order.successful', brand, order.user, order.order_item)
                self.mail("order.successful", brand)

            else:
                self.update_product(order.user, *order.cart.items.all())
                data_dict = defaultdict(list)
                for order_item in order.cart.items.all():
                    data_dict[order_item.product.brand].append(order_item)
                
                for brand in data_dict:
                    self.record(brand, *data_dict[brand])
                    self.message(self.MESSAGES['order.successful'],'order.successful', brand, order.user, *data_dict[brand])
                    self.mail('order.successful', brand)

        elif data['event'] == 'transfer.success':
            ref = data['data']['reference']
            transfer = get_object_or_404(Transfer, ref=ref)
            transfer.paid = True
            transfer.code = data['data']['transfer_code']
            transfer.save()
            self.message(self.MESSAGES['transfer.successful'], 'transfer.successful', transfer.brand)
            self.mail('transfer.successful', transfer.brand)

        elif data['event'] == 'transfer.failed':
            brand = get_object_or_404(Transfer, ref=data['data']['reference']).brand
            self.message(self.MESSAGES['transfer.failed'], 'transfer.failed', brand)
            self.mail('transfer.failed', brand)

        elif data['event'] == 'transfer.reversed':
            ref = data['data']['reference']
            transfer = get_object_or_404(Transfer, ref=ref)
            transfer.paid = False
            transfer.save()
            brand = transfer.brand
            self.message(self.MESSAGES['transfer.reversed'], 'transfer.reversed', brand)
            self.mail('transfer.reversed', brand)
        return Response(status=status.HTTP_200_OK)


# TODO Implement Cache. (Resources acquired!)
# TODO Update the gitignore file.
# TODO Make some websocket tasks asycio for speed.