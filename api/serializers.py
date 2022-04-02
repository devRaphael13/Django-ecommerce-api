from django.forms import ValidationError
from rest_framework import serializers
from api.models import AccountDetail, Size, Color, Variant, Bank, Message, OrderItem, Image, Review, Transfer, User, Category, Cart, Product, Order, Brand


class DynamicModelSerializer(serializers.ModelSerializer):

    def get_field_names(self, declared_fields, info):
        field_names = super(DynamicModelSerializer, self).get_field_names(declared_fields, info)
        if self.dynamic_fields is not None:
            allowed = set(self.dynamic_fields)
            excluded_field_names = set(field_names) - allowed
            field_names = tuple(x for x in field_names if x not in excluded_field_names)
        return field_names

    def __init__(self, *args, **kwargs):
        self.dynamic_fields = kwargs.pop('fields', None)
        self.read_only_fields = kwargs.pop('read_only_fields', [])
        super(DynamicModelSerializer, self).__init__(*args, **kwargs)

class CustomRelatedField(serializers.RelatedField):

    def __init__(self, **kwargs):
        self.serializer = kwargs.pop('serializer', None)
        super().__init__(**kwargs)

    def to_internal_value(self, data):
        return self.queryset.get(pk=data)

    def to_representation(self, value):
        return self.serializer(instance=value, fields=self.serializer.get_custom_fields()).data


class ImageSerializer(DynamicModelSerializer):

    class Meta:
        model = Image
        fields = '__all__'

    @staticmethod
    def get_custom_fields():
        return 'id', 'images'


class CategorySerializer(DynamicModelSerializer):

    class Meta:
        model = Category
        fields = '__all__'

    @staticmethod
    def get_custom_fields():
        return 'id', 'name'

class SizeSerializer(DynamicModelSerializer):

    class Meta:
        model = Size
        fields = '__all__'

    @staticmethod
    def get_custom_fields():
        return 'id', 'size', 'is_available'


class ColorSerializer(DynamicModelSerializer):

    class Meta:
        model = Color
        fields = '__all__'

    @staticmethod
    def get_custom_fields():
        return 'id', 'name'

class VariantSerializer(DynamicModelSerializer):

    sizes = SizeSerializer(read_only=True, many=True, fields=SizeSerializer.get_custom_fields())
    color = CustomRelatedField(queryset=Color.objects.all(), serializer=ColorSerializer)

    class Meta:
        model = Variant
        fields = '__all__'

    @staticmethod
    def get_custom_fields():
        return 'id', 'product', 'color', 'is_available'


class BrandSerializer(DynamicModelSerializer):
    owner = serializers.ReadOnlyField(source="owner.username")

    class Meta:
        model = Brand
        fields = '__all__'
        extra_kwargs = {
            'recipient_code': { 'read_only': True, 'allow_null': True }
        }

    @staticmethod
    def get_custom_fields():
        return 'id', 'name'

class ReviewSerializer(DynamicModelSerializer):
    user = serializers.ReadOnlyField(source="user.username")

    class Meta:
        model = Review
        field = '__all__'

    def get_custom_fields():
        return 'id', 'product', 'stars'

class ProductSerializer(DynamicModelSerializer):

    images = ImageSerializer(read_only=True, many=True, fields=ImageSerializer.get_custom_fields())
    brand = CustomRelatedField(queryset=Brand.objects.all(), serializer=BrandSerializer)

    class Meta:
        model = Product
        fields = '__all__'
        extra_kwargs = {
            "is_available": { "default": True },
            "quantity": { "default": 1 }
        }

    @staticmethod
    def get_custom_fields():
        return 'id', 'name', 'is_available', 'brand', 'price'



class OrderItemSerializer(DynamicModelSerializer):

    product = CustomRelatedField(queryset=Product.objects.all(), serializer=ProductSerializer)

    class Meta:
        model = OrderItem
        fields = '__all__'
        extra_kwargs = {
            "quantity": { "default": 1 }
        }

    @staticmethod
    def get_custom_fields():
        return 'product', 'quantity'


    
class CartSerializer(DynamicModelSerializer):
    items = CustomRelatedField(queryset=OrderItem.objects.all(), many=True, serializer=OrderItemSerializer)

    class Meta:
        model = Cart
        fields = '__all__'

    @staticmethod
    def get_custom_fields():
        return 'items',


class UserSerializer(DynamicModelSerializer):

    cart = CartSerializer(read_only=True, fields=CartSerializer.get_custom_fields())

    class Meta:
        model = User
        exclude = ('user_permissions', 'groups')
        extra_kwargs = {
            "password": { "write_only": True },
            "email": { "required": True },
            "is_active": { "read_only": True },
            "is_staff": { "read_only": True },
            "is_brand_owner": { "read_only": True, "default": False }
        }
    
    @staticmethod
    def get_custom_fields():
        return 'id', 'username', 'email'



class OrderSerializer(DynamicModelSerializer):
    
    order_item = CustomRelatedField(queryset=OrderItem.objects.all(), serializer=OrderItemSerializer)
    cart = CustomRelatedField(queryset=Cart.objects.all(), serializer=CartSerializer)

    class Meta:
        model = Order
        fields = '__all__'
        extra_kwargs = {
            "completed": { "default": False }
        }

    def validate_order_item(self, value):
        if self.cart and value:
            return ValidationError("You can only provide the cart or the item but not both")

    def validate_cart(self, value):
        if self.order_item and value:
            return ValidationError("ou can only provide the cart or the item but not both")

class MessageSerializer(DynamicModelSerializer):

    class Meta:
        model = Message
        fields = '__all__'

    @staticmethod
    def get_custom_fields():
        return '__all__'

class AccountDetailSerializer(DynamicModelSerializer):

    class Meta:
        model = AccountDetail
        fields = '__all__'
        extra_kwargs = {
            "in_use": { "default": True }
        }

    @staticmethod
    def get_custom_fields():
        return '__all__',


class BankSerializer(DynamicModelSerializer):

    class Meta:
        model = Bank
        fields = '__all__'

class TransferSerializer(DynamicModelSerializer):

    class Meta:
        model = Transfer
        fields = '__all__'
        extra_kwargs = {
            "paid": { "default": False }
        }

