from collections import defaultdict
from abc import ABC
from concurrent.futures import ThreadPoolExecutor

from django.conf import settings
from django.contrib.auth.hashers import make_password
from django.core.mail import send_mail
from django.http.response import Http404
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from py4paystack.routes.subaccount import SubAccounts
from py4paystack.routes.transactions import Transaction
from py4paystack.routes.transfer_recipient import TransferRecipient
from py4paystack.routes.transfers import Transfer as BulkTransfer
from py4paystack.routes.verification import Verification
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from api.models import (Account, Bank, Brand, Cart, Category, Image, Message,
                        Order, OrderItem, Product, Review, Size, Transfer,
                        User, Variant, SizeChart)
from api.permissions import (CanReview, IsABrandOwner, IsAccountOwner,
                             IsOrderer, IsOwnerByBrand, IsProductOwner,
                             IsBrandOwner, IsUser, CanEditSize)
from api.serializers import (AccountSerializer, BankSerializer,
                             BrandSerializer, BrandSerializerPlus,
                             CategorySerializer, ImageSerializer,
                             MessageSerializer, OrderSerializer,
                             ProductSerializer, ProductSerializerPlus,
                             ReviewSerializer, SizeSerializer,
                             TransferSerializer, UserSerializer,
                             UserSerializerPlus, VariantSerializer,
                             VariantSerializerPlus, SizeChartSerializer)

from .mixin import (CustomCreateMixin, CustomDestroyMixin, CustomListMixin,
                    CustomModelViewSet, CustomReadOnlyViewSet,
                    CustomRetrieveMixin, CustomUpdateMixin, redis_client)


# Mods
class CustomSerializer():

    def get_serializer_class(self):
        if self.action == "retrieve" and hasattr(self, "serializer_class_plus"):
            return self.serializer_class_plus
        return super().get_serializer_class()

class UserViewSet(CustomSerializer, CustomModelViewSet):
    
    serializer_class = UserSerializer
    serializer_class_plus = UserSerializerPlus
    queryset = User.objects.all()

    def destroy(self, request, pk=None, *args, **kwargs):
        user = self.get_object()
        user.is_active = False
        user.save()
        return Response(status=status.HTTP_204_NO_CONTENT)

    def perform_create(self, serializer):
        serializer.save(password=make_password(serializer.validated_data['password']))
        return {"status": True, "data": {"token": serializer.instance.auth_token.key}}

    def get_permissions(self):
        if self.action == "list":
            return permissions.IsAdminUser(),
        if self.action == "create":
            return permissions.AllowAny(),
        return IsUser(),

    @action(detail=False, methods=['post'])
    def update_cart(self, request, pk=None, *args, **kwargs):
        data = request.data

        if not data:
            return Response({ 'product_variant_id': ['This field is required.'], 'action': ['This field is required'] }, status=status.HTTP_400_BAD_REQUEST)
        
        action_choices = ('add', 'subtract', 'remove')
        variant_id = data.get('product_variant_id', None)
        size = data.get('size', None)
        action = data.get('action', None)
        quantity = int(data.get('quantity', 1))
        res = {'errors': []}

        if not variant_id:
            res['errors'].append({ 'product_variant_id': ['This field is required.']})
        else:
            variant_id = int(variant_id)
            
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
                return self.add(cart, variant, size, quantity)

            elif action == 'subtract':
                return self.subtract(cart, variant, quantity)

            else:
                return self.remove(cart, variant)

        return Response(res, status=status.HTTP_400_BAD_REQUEST)
                    
    def add(self, cart, variant, size, quantity):
        if not variant.is_available:
            return Response({'detail': 'This variant of this product is out of stock'}, status=status.HTTP_404_NOT_FOUND)

        if size is None:
            return Response({"size": ["This field is required"]}, status=status.HTTP_400_BAD_REQUEST)

        if variant.quantity >= quantity:
            item = cart.items.filter(variant__id=variant.id)
            if item.exists():
                item = item[0]
                item.quantity += quantity
                item.save()
                return Response(status=status.HTTP_200_OK)

            size = variant.sizes.filter(id=int(size))
            if size and size.first().is_available:
                cart.items.add(OrderItem.objects.create(variant=variant, quantity=quantity, size=size.first()))
                return Response(status=status.HTTP_200_OK)
            return Response({ "detail": "The Size of the product you're adding to cart is out of stock" }, status=status.HTTP_404_NOT_FOUND)
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

class ProductViewSet(CustomSerializer, CustomModelViewSet):

    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    serializer_class_plus = ProductSerializerPlus

    def perform_create(self, serializer):
        serializer.save()
        redis_client.delete(f"Brand_{serializer.instance.brand_id}")

    def perform_update(self, serializer):
        serializer.save()
        redis_client.delete(f"Brand_{serializer.instance.brand_id}")

    def perform_destroy(self, instance):
        redis_client.delete(f"Brand_{instance.brand_id}")
        instance.delete()
    
    def get_permissions(self):
        if self.action == 'create':
            return IsABrandOwner(),
        elif self.action in ('list', 'retrieve'):
            return permissions.AllowAny(),
        return IsOwnerByBrand(),

class SizeViewSet(CustomModelViewSet):

    queryset = Size.objects.all()
    serializer_class = SizeSerializer

    def perform_create(self, serializer):
        serializer.save()
        redis_client.delete(f"Variant_{serializer.instance.variant_id}")

    def perform_update(self, serializer):
        serializer.save()
        redis_client.delete(f"Variant_{serializer.instance.variant_id}")
    
    def perform_destroy(self, instance):
        redis_client.delete(f"Variant_{instance.variant_id}")
        instance.delete()


    def get_permissions(self):
        if self.action in ('list', 'retrieve'):
            return permissions.AllowAny(),
        return CanEditSize(),

class SizeChartViewSet(viewsets.ModelViewSet):
    queryset = SizeChart.objects.all()
    serializer_class = SizeChartSerializer
    permission_classes = (permissions.IsAdminUser,)
    
class VariantViewSet(CustomSerializer, CustomModelViewSet):

    queryset = Variant.objects.all()
    serializer_class = VariantSerializer
    serializer_class_plus = VariantSerializerPlus

    def perform_create(self, serializer):
        serializer.save()
        redis_client.delete(f"Product_{serializer.instance.product_id}")

    def perform_update(self, serializer):
        serializer.save()
        redis_client.delete(f"Product_{serializer.instance.product_id}")

    def perform_destroy(self, instance):
        redis_client.delete(f"Product_{instance.product_id}")
        instance.delete()


    def get_permissions(self):
        if self.action in ('list', 'retrieve'):
            return permissions.AllowAny(),
        return IsProductOwner(),

class ImageViewSet(CustomModelViewSet):

    queryset = Image.objects.all()
    serializer_class = ImageSerializer

    def perform_create(self, serializer):
        serializer.save()
        redis_client.delete(f"Product_{serializer.instance.product_id}")

    def perform_update(self, serializer):
        serializer.save()
        redis_client.delete(f"Product_{serializer.instance.product_id}")

    def perform_destroy(self, instance):
        redis_client.delete(f"Product_{instance.product_id}")
        instance.delete()

    def get_permissions(self):
        if self.action in ('list', 'retrieve'):
            return permissions.AllowAny(),
        return IsProductOwner(),

class CategoryViewSet(CustomModelViewSet):

    queryset = Category.objects.all()
    serializer_class = CategorySerializer

    def get_permissions(self):
        if self.action in ('list', 'retrieve'):
            return permissions.AllowAny(),
        return permissions.IsAdminUser(),

class BankViewSet(CustomModelViewSet):

    queryset = Bank.objects.all()
    serializer_class = BankSerializer

    def get_permissions(self):
        if self.action in ('list', 'retrieve'):
            return permissions.IsAuthenticated(),
        return permissions.IsAdminUser(),

class BrandViewSet(CustomSerializer, CustomModelViewSet):
    queryset = Brand.objects.all()
    serializer_class = BrandSerializer
    serializer_class_plus = BrandSerializerPlus

    def perform_create(self, serializer):
        user = self.request.user
        serializer.save(owner=user)
        if not user.is_brand_owner:
            user.is_brand_owner = True
            user.save()

    def get_permissions(self):
        if self.action in ('list', 'retrieve'):
            return permissions.AllowAny(),
        elif self.action == 'create':
            return permissions.IsAuthenticated(),
        return IsBrandOwner(),

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

class ReviewViewSet(CustomModelViewSet):
    queryset = Review.objects.all()
    serializer_class = ReviewSerializer

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
        redis_client.delete(f"{serializer.Meta.model.__name__}_list*")
    
    def perform_update(self, serializer):
        serializer.save(user=self.request.user)
        redis_client.delete(f"{serializer.Meta.model.__name__}_list*")

    def get_permissions(self):
        if self.action in ('list', 'retrieve'):
            return permissions.AllowAny(),
        return CanReview(),

class AccountViewSet(viewsets.ModelViewSet):
    serializer_class = AccountSerializer
    
    def perform_create(self, serializer):
        data = self.create_account(
            serializer.validated_data["acct_no"], 
            serializer.validated_data["bank"], 
            serializer.validated_data['brand']
            )
        if not data:
            return {"status": False, "error": {"detail": "Check the account number provided for errors."}}
        serializer.validated_data.update({ "acct_name": data[0], "subaccount_code": data[1], "recipient_code": data[2] })
        serializer.save()        
    
    def perform_update(self, serializer):
        acct_no = serializer.validated_data.get("acct_no", None)
        bank = serializer.validated_data.get("bank", None)

        if any(( acct_no, bank )):
            data = self.create_account(
                acct_no if acct_no else serializer.instance.acct_no,
                bank if bank else serializer.instance.bank,
                serializer.instance.brand
            )

            if not data:
                return {"status": False, "error": {"detail": "Check the account number provided for errors."}}

            serializer.validated_data.update({ "acct_name": data[0], "subaccount_code": data[1], "recipient_code": data[2] })
        serializer.save()

    def create_account(self, acct_number, bank, brand):
        verify = Verification(settings.PAYSTACK_SECRET_KEY).resolve_acct_number(acct_number, bank.code)

        if not verify['status']:
            return False

        recipient = TransferRecipient(settings.PAYSTACK_SECRET_KEY).create("nuban", brand.name, brand.owner.email, account_number=acct_number, bank_code=bank.code)
        subaccount = SubAccounts(settings.PAYSTACK_SECRET_KEY).create(brand.name, bank.code, acct_number, 100 - brand.percentage)

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
                size = variant.sizes.filter(size=size)
                if size and size.first().is_available:
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
        if self.action == 'create':
            return permissions.IsAuthenticated(),
        elif self.action in ('retrieve', 'verify'):
            return permissions.OR(IsOrderer(), permissions.IsAdminUser()),
        return permissions.IsAdminUser(),

class TransferViewSet(viewsets.ReadOnlyModelViewSet):

    queryset = Transfer.objects.all()
    serializer_class = TransferSerializer
    permission_classes = (permissions.IsAdminUser,)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    
    def get_recipient_code(self, brand):
        try:
            recipient_code = brand.account.recipient_code

        except Brand.account.RelatedObjectDoesNotExist:
            return None
        return recipient_code

    @action(detail=False, methods=['post'])
    def transfer(self, request, *args, **kwargs):
        records = Transfer.objects.filter(paid=False).select_related("brand").select_related("brand__account")
                        
        if records.exists():
            reason = 'Payment for products provided'

            transfers = []
            for record in records:
                recipient_code = self.get_recipient_code(record.brand)
                if not recipient_code:
                    return Response({ 'detail': 'You do not have an account!' }, status=status.HTTP_404_NOT_FOUND)
                transfers.append({'amount': record.amount, 'recipient': recipient_code, 'reference': record.ref, 'reason': reason})

            return Response(BulkTransfer(settings.PAYSTACK_SECRET_KEY).initiate_bulk("balance", *transfers), status=status.HTTP_200_OK)
        return Response({ 'detail': 'All debts have been paid!' }, status=status.HTTP_204_NO_CONTENT)

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
    def use_threadpool(self, *func_with_args):
        with ThreadPoolExecutor() as executor:
            for func, args in func_with_args:
                executor.submit(func, *args)

    def get_order(self, ref):
        try:
            order = Order.objects.select_related().select_related('order_item__variant').get(ref=ref)
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
            self.MESSAGES[status].format(', check your dashboard for further details.\nYours faithfully\n{}.'.format(brand.name)),
            settings.EMAIL_HOST_USER,
            [brand.owner.email],
            fail_silently=False
        )


    def update_product(self, user, *item):
        for x in item:
            variant = x.variant
            quantity = x.quantity
            product = variant.product
            size = x.size
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
            order = self.get_order(ref)
            order.completed = True
            order.save()
            if order.order_item:
                brand = order.order_item.variant.product.brand
                self.use_threadpool(
                    (self.update_product, [order.user, order.order_item]),
                    (self.record, [brand, order.order_item]),
                    (self.message, [self.MESSAGES['order.successful'],'order.successful', brand, order.user, order.order_item]),
                    (self.mail, ["order.successful", brand])
                )

            else:
                self.update_product(order.user, *order.user.cart.items.all())
                data_dict = defaultdict(list)
                for order_item in order.user.cart.items.all():
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
