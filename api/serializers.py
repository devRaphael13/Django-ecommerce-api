from rest_framework.serializers import (
    ModelSerializer,
    PrimaryKeyRelatedField,
    RelatedField,
    ReadOnlyField,
    StringRelatedField,
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


class DynamicModelSerializer(ModelSerializer):

    def get_field_names(self, declared_fields, info):
        field_names = super(DynamicModelSerializer, self).get_field_names(
            declared_fields, info
        )
        if self.dynamic_fields is not None:
            allowed = set(self.dynamic_fields)
            excluded_field_names = set(field_names) - allowed
            field_names = tuple(x for x in field_names if x not in excluded_field_names)
        return field_names

    def __init__(self, *args, **kwargs):
        self.dynamic_fields = kwargs.pop("fields", None)
        self.read_only_fields = kwargs.pop("read_only_fields", [])
        super(DynamicModelSerializer, self).__init__(*args, **kwargs)


class CustomRelatedField(RelatedField):

    def __init__(self, **kwargs):
        self.serializer = kwargs.pop("serializer", None)
        super().__init__(**kwargs)

    def to_internal_value(self, data):
        return self.queryset.get(pk=data)

    def to_representation(self, value):
        return self.serializer(instance=value).data


class ImageSerializer(DynamicModelSerializer):

    class Meta:
        model = Image
        fields = "__all__"

    @staticmethod
    def get_custom_fields():
        return "id", "url"


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

    # def validate_size(self, value):
    #     if value not in SizeChart.objects.values_list("name", flat=True):
    #         raise serializers.ValidationError("Invalid value for size")
    #     return value

    # def validate(self, attrs):
    #     quantity = attrs.get("quantity", None)

    #     if quantity:
    #         variant = attrs.get("variant", None) or self.instance.variant
    #         queryset = (
    #             variant.sizes.exclude(id=self.instance.id)
    #             if self.instance
    #             else variant.sizes.all()
    #         )

    #         if sum([x.quantity for x in queryset]) + quantity > variant.quantity:
    #             raise serializers.ValidationError(
    #                 "You cannot have more sizes for a product variant than product variant itself."
    #             )
    #     return super().validate(attrs)

    @staticmethod
    def get_custom_fields():
        return "id", "size", "is_available"


class VendorSerializer(ModelSerializer):
    owner = ReadOnlyField(source="owner.id")

    class Meta:
        model = Vendor
        fields = "__all__"


class ReviewSerializer(DynamicModelSerializer):
    user = ReadOnlyField(source="user.email")

    class Meta:
        model = Review
        fields = "__all__"

    def get_custom_fields():
        return "id", "product", "stars"


class UserSerializer(ModelSerializer):
    auth_token = StringRelatedField()

    class Meta:
        model = User
        exclude = ("user_permissions", "groups", "is_superuser")
        extra_kwargs = {
            "password": {"write_only": True},
            "email": {"required": True},
            "is_active": {"read_only": True},
            "is_staff": {"read_only": True},
            "is_vendor": {"read_only": True, "default": False},
        }


class ProductSerializer(ModelSerializer):
 
    class Meta:
        model = Product
        fields = "__all__"
        extra_kwargs = {"is_available": {"default": True}, "quantity": {"default": 1}}
    
    def get_fields(self):
        fields = super().get_fields()
        fields["parent"] = PrimaryKeyRelatedField(queryset=Product.objects.all(), required=False)
        fields["sizes"] = CustomRelatedField(
            many=True, serializer=SizeSerializer, queryset=Size.objects.all()
        )

        fields["category"] = CustomRelatedField(
            queryset=Category.objects.all(), serializer=CategorySerializer
        )
        fields["customers"] = CustomRelatedField(
            queryset=User.objects.all(), many=True, serializer=UserSerializer
        )
        fields["vendor"] = CustomRelatedField(
            queryset=Vendor.objects.all(), serializer=VendorSerializer
        )
        return fields


class OrderItemSerializer(DynamicModelSerializer):

    product = CustomRelatedField(
        queryset=Product.objects.all(), serializer=ProductSerializer
    )

    class Meta:
        model = OrderItem
        fields = "__all__"
        extra_kwargs = {"quantity": {"default": 1}}

    @staticmethod
    def get_custom_fields():
        return "product", "quantity"


class CartSerializer(ModelSerializer):
    items = OrderItemSerializer(many=True, required=False)

    class Meta:
        model = Cart
        fields = "__all__"
        extra_kwargs = {"user": {"read_only": True}}


class OrderSerializer(DynamicModelSerializer):

    cart = CustomRelatedField(queryset=Cart.objects.all(), serializer=CartSerializer)

    class Meta:
        model = Order
        fields = "__all__"
