from rest_framework.serializers import (
    ModelSerializer,
    PrimaryKeyRelatedField,
    RelatedField,
    ReadOnlyField,
    StringRelatedField,
    SerializerMethodField,
    ValidationError
)

from .models import (
    Size,
    OrderItem,
    Image,
    Review,
    User,
    Category,
    Product,
    Order,
    Vendor,
)


class CustomRelatedField(RelatedField):

    def __init__(self, **kwargs):
        self.serializer = kwargs.pop("serializer", None)
        self.display_fields = kwargs.pop("display_fields", None)
        super().__init__(**kwargs)

    def to_internal_value(self, data):
        return self.queryset.get(pk=data)

    def to_representation(self, value):
        return self.serializer(instance=value).data


class ImageSerializer(ModelSerializer):

    class Meta:
        model = Image
        fields = "__all__"


class CategorySerializer(ModelSerializer):
    class Meta:
        model = Category
        fields = "__all__"

    def get_fields(self):
        fields = super().get_fields()
        fields["sub_categories"] = CategorySerializer(many=True, read_only=True)
        return fields


class SizeSerializer(ModelSerializer):

    class Meta:
        model = Size
        fields = "__all__"


class VendorSerializer(ModelSerializer):
    user = ReadOnlyField(source="user.id")

    class Meta:
        model = Vendor
        fields = "__all__"


class ReviewSerializer(ModelSerializer):
    user = ReadOnlyField(source="user.id")

    class Meta:
        model = Review
        fields = "__all__"


class UserSerializer(ModelSerializer):
    auth_token = StringRelatedField()

    class Meta:
        model = User
        exclude = ("user_permissions", "groups", "is_superuser")
        extra_kwargs = {
            "password": {"write_only": True},
            "email": {"required": True},
            # "is_active": {"read_only": True},
            "is_staff": {"read_only": True},
            "is_vendor": {"read_only": True, "default": False},
        }


class ProductSerializer(ModelSerializer):

    images = CustomRelatedField(many=True, serializer=ImageSerializer, read_only=True)
    sizes = CustomRelatedField(many=True, serializer=SizeSerializer, read_only=True)
    category = CustomRelatedField(
        queryset=Category.objects.all(), serializer=CategorySerializer
    )
    customers = PrimaryKeyRelatedField(
        queryset=User.objects.all(), many=True, required=False
    )
    vendor = CustomRelatedField(
        queryset=Vendor.objects.all(), serializer=VendorSerializer
    )
    parent = PrimaryKeyRelatedField(queryset=Product.objects.all(), required=False)

    class Meta:
        model = Product
        fields = "__all__"
        extra_kwargs = {"is_available": {"default": True}, "quantity": {"default": 1}}


class OrderItemSerializer(ModelSerializer):
    user = ReadOnlyField(source="user.id")
    product = PrimaryKeyRelatedField(queryset=Product.objects.all())

    class Meta:
        model = OrderItem
        fields = "__all__"
        extra_kwargs = {"quantity": {"default": 1}}

    def create(self, validated_data):
        product = validated_data["product"]
        quantity = validated_data["quantity"]
        user = validated_data["user"]
        instance = None

        items = OrderItem.objects.filter(product=product, user=user)
        if items.exists():
            instance = items.first()
            quantity = instance.quantity + quantity

        if quantity > product.quantity:
            raise ValidationError({"quantity": [f"Product has only {product.quantity} units available."]})

        if instance:
            instance.quantity = quantity
            instance.save()
            return instance
        return super().create(validated_data)

    def update(self, instance, validated_data):
        quantity = validated_data.get("quantity", None)

        if quantity and quantity > instance.product.quantity:
            raise ValidationError(
                {"quantity": [f"Product has only {product.quantity} units available."]}
            )
        return super().update(instance, validated_data)


class OrderSerializer(ModelSerializer):
    user = ReadOnlyField(source="user.id")
    items = OrderItemSerializer(read_only=True, many=True)

    class Meta:
        model = Order
        fields = "__all__"

    def create(self, validated_data):
        user = validated_data["user"]
        items = user.items.all()

        if not items.exists():
            raise ValidationError({"items": ["User's cart is empty!"]})
        order = super().create(validated_data)
        order.items.add(*user.items.all())
        return order
