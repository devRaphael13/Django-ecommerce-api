import statistics
import uuid
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.dispatch import receiver
from django.db.models.signals import post_save
from rest_framework.authtoken.models import Token

from .managers import CustomUserManager


def validate_acct_no(value):
    if len(value) != 10:
        raise ValidationError("Field 'acct_no' cannot be more or less than 10 digits")

    if not value.isnumeric():
        raise ValidationError("Field 'acct_no' may only contain digits")


class User(AbstractUser):
    username = None
    id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False, unique=True
    )
    profile_pic = models.URLField(blank=True, null=True)
    phone_number = models.CharField(
        validators=[
            RegexValidator(
                regex=r"^\+?1?\d{9,15}$",
                message="Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed.",
            )
        ],
        max_length=17,
        blank=True,
    )
    email = models.EmailField(unique=True)
    is_vendor = models.BooleanField(default=False)
    datetime_created = models.DateTimeField(auto_now_add=True)

    USERNAME_FIELD = "email"

    REQUIRED_FIELDS = []

    objects = CustomUserManager()

    def __str__(self):
        return self.email


class Image(models.Model):
    product = models.ForeignKey(
        "Product", related_name="images", on_delete=models.CASCADE
    )
    url = models.URLField()

    def __str__(self):
        return self.url


class Product(models.Model):
    parent = models.ForeignKey(
        "self", on_delete=models.CASCADE, related_name="variants", blank=True, null=True
    )
    display_image = models.URLField()
    name = models.CharField(max_length=150)
    datetime_created = models.DateTimeField(auto_now_add=True)
    category = models.ForeignKey("Category", on_delete=models.CASCADE)
    description = models.TextField()
    quantity = models.PositiveIntegerField(default=1)
    vendor = models.ForeignKey("Vendor", on_delete=models.CASCADE)
    is_available = models.BooleanField(default=True)
    price = models.PositiveIntegerField()
    customers = models.ManyToManyField(User, related_name="users", blank=True)
    stars = models.IntegerField(default=0)
    reviews = models.IntegerField(default=0)

    def __str__(self):
        return "{} ({} NGN)".format(self.name, self.price/100)


class OrderItem(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="items")
    quantity = models.PositiveIntegerField(default=1)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)

    def get_total_amount(self):
        return self.product.price * self.quantity


class Order(models.Model):
    id = models.UUIDField(
        default=uuid.uuid4, primary_key=True, editable=False, unique=True
    )
    datetime_created = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)
    items = models.ManyToManyField(OrderItem, blank=True)
    completed = models.BooleanField(default=False)


class Size(models.Model):
    name = models.CharField(max_length=20, unique=True)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="sizes")


class Vendor(models.Model):
    logo = models.URLField(null=True, blank=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    datetime_created = models.DateTimeField(auto_now_add=True)
    name = models.CharField(max_length=150)

    def __str__(self):
        return self.name


class Category(models.Model):
    name = models.CharField(max_length=150, unique=True)
    parent = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        related_name="sub_categories",
        blank=True,
        null=True,
    )

    class Meta:
        verbose_name = "categories"

    def __str__(self) -> str:
        return self.name


class Review(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    review = models.TextField()
    stars = models.PositiveIntegerField()
    product = models.ForeignKey(Product, on_delete=models.CASCADE)


@receiver(post_save, sender=User)
def create_token(sender, instance, created, **kwargs):
    if created:
        Token.objects.create(user=instance)
