from rest_framework.serializers import (
    ModelSerializer,
    PrimaryKeyRelatedField,
    RelatedField,
    ReadOnlyField,
    StringRelatedField,
    SerializerMethodField,
)

from .models import (
    Size,
    OrderItem,
    Image,
    Review,
    User,
    Category,
    Cart,
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
        fields["sub_categories"] = CategorySerializer(many=True, required=False)
        return fields


class SizeSerializer(ModelSerializer):

    class Meta:
        model = Size
        fields = "__all__"


class VendorSerializer(ModelSerializer):
    owner = ReadOnlyField(source="owner.id")

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

    images = StringRelatedField(many=True)
    sizes = CustomRelatedField(
        many=True, serializer=SizeSerializer, queryset=Size.objects.all()
    )
    category = CustomRelatedField(
        queryset=Category.objects.all(), serializer=CategorySerializer
    )
    customers = PrimaryKeyRelatedField(queryset=User.objects.all(), many=True)
    vendor = CustomRelatedField(
        queryset=Vendor.objects.all(), serializer=VendorSerializer
    )
    parent = PrimaryKeyRelatedField(queryset=Product.objects.all(), required=False)

    class Meta:
        model = Product
        fields = "__all__"
        extra_kwargs = {"is_available": {"default": True}, "quantity": {"default": 1}}


class OrderItemSerializer(ModelSerializer):
    product = PrimaryKeyRelatedField(queryset=Product.objects.all())

    class Meta:
        model = OrderItem
        fields = "__all__"
        extra_kwargs = {"quantity": {"default": 1}}


class CartSerializer(ModelSerializer):
    items = CustomRelatedField(
        queryset=OrderItem.objects.all(), serializer=OrderItemSerializer, many=True
    )

    class Meta:
        model = Cart
        fields = "__all__"
        extra_kwargs = {"user": {"read_only": True}}


class OrderSerializer(ModelSerializer):
    user = ReadOnlyField(source="user.id")
    items = OrderItemSerializer(read_only=True, many=True)

    class Meta:
        model = Order
        fields = "__all__"

    def create(self, validated_data):
        order = super().create(validated_data)
        order.items.add(*order.user.cart.items.all())
        return order
