from django.forms import ValidationError
from rest_framework import serializers
from api.models import Account, Size, Variant, Bank, Message, OrderItem, Image, Review, Transfer, User, Category, Cart, Product, Order, Brand, SizeChart

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
        return 'id', 'url'

class ProductSerializer(DynamicModelSerializer):

    class Meta:
        model = Product
        exclude = ("description", "quantity", "customers")
        extra_kwargs = {
            "is_available": { "default": True },
            "quantity": { "default": 1 }
        }

    @staticmethod
    def get_custom_fields():
        return 'id', 'name', 'is_available', 'brand', 'price'

class SizeChartSerializer(DynamicModelSerializer):

    class Meta:
        model = SizeChart
        fields = "__all__"

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

    def validate_size(self, value):
        if value not in SizeChart.objects.values_list("name", flat=True):
            raise serializers.ValidationError("Invalid value for size")
        return value

    def validate(self, attrs):
        quantity = attrs.get("quantity", None)

        if quantity:
            variant = attrs.get("variant", None) or self.instance.variant
            queryset = variant.sizes.exclude(id=self.instance.id) if self.instance else variant.sizes.all()
            
            if sum([x.quantity for x in queryset]) + quantity > variant.quantity:
                raise serializers.ValidationError("You cannot have more sizes for a product variant than product variant itself.")
        return super().validate(attrs)

    @staticmethod
    def get_custom_fields():
        return 'id', 'size', 'is_available'


class VariantSerializer(DynamicModelSerializer):

    class Meta:
        model = Variant
        fields = '__all__'

    def validate(self, attrs):
        quantity = attrs.get("quantity", None)
        if quantity:
            product = attrs.get("product", None) or self.instance.product
            queryset = product.variants.exclude(id=self.instance.id) if self.instance else product.variants.all()

            if sum([x.quantity for x in queryset]) + quantity > product.quantity:
                raise serializers.ValidationError("You cannot have more variants for a product than the product itself.")
        return super().validate(attrs)

    @staticmethod
    def get_custom_fields():
        return 'id', 'product', 'is_available', 'image_url'

class BrandSerializer(DynamicModelSerializer):
    owner = serializers.ReadOnlyField(source="owner.id")

    class Meta:
        model = Brand
        fields = '__all__'
        extra_kwargs = {
            'subaccount_code': { 'read_only': True, 'allow_null': True },
            'recipient_code': { 'read_only': True, 'allow_null': True }

        }

    @staticmethod
    def get_custom_fields():
        return 'id', 'name'

class ReviewSerializer(DynamicModelSerializer):
    user = serializers.ReadOnlyField(source="user.email")

    class Meta:
        model = Review
        fields = '__all__'

    def get_custom_fields():
        return 'id', 'product', 'stars'

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

    class Meta:
        model = User
        exclude = ('user_permissions', 'groups', 'is_superuser')
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

class MessageSerializer(DynamicModelSerializer):

    class Meta:
        model = Message
        fields = '__all__'

    @staticmethod
    def get_custom_fields():
        return '__all__'

class AccountSerializer(DynamicModelSerializer):

    class Meta:
        model = Account
        fields = '__all__'

    @staticmethod
    def get_custom_fields():
        return '__all__',

    def validate_acct_no(self, value):
        if len(value) != 10:
            raise serializers.ValidationError("Field 'acct_no' cannot be more or less than 10 digits")
        
        if not value.isnumeric():
            raise serializers.ValidationError("Field 'acct_no' may only contain digits")
        return value


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

class ProductSerializerPlus(ProductSerializer):
    images = ImageSerializer(read_only=True, many=True, fields=ImageSerializer.get_custom_fields())
    brand = CustomRelatedField(serializer=BrandSerializer, read_only=True)
    category = CustomRelatedField(read_only=True, serializer=CategorySerializer)
    variants = CustomRelatedField(read_only=True, serializer=VariantSerializer, many=True)

    class Meta:
        model = Product
        fields = "__all__"
        extra_kwargs = ProductSerializer.Meta.extra_kwargs

class UserSerializerPlus(UserSerializer):
    cart = CustomRelatedField(serializer=CartSerializer, read_only=True)

class BrandSerializerPlus(BrandSerializer):
    products = CustomRelatedField(serializer=ProductSerializer, read_only=True, many=True)

class VariantSerializerPlus(VariantSerializer):

    sizes = CustomRelatedField(serializer=SizeSerializer, read_only=True, many=True)

