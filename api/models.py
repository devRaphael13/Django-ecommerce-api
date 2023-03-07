import statistics
import uuid
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db import models
from django.contrib.auth.models import AbstractUser, User
from django.dispatch import receiver
from django.db.models.signals import post_save, pre_save
from rest_framework.authtoken.models import Token

from .managers import CustomUserManager
        
def validate_acct_no(value):
    if len(value) != 10:
        raise ValidationError("Field 'acct_no' cannot be more or less than 10 digits")
    
    if not value.isnumeric():
        raise ValidationError("Field 'acct_no' may only contain digits")


class User(AbstractUser):
    username = None
    profile_pic = models.URLField(blank=True, null=True)
    phone_number = models.CharField(validators=[RegexValidator(
        regex=r"^\+?1?\d{9,15}$",
        message="Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed.",
    )], max_length=17, blank=True)
    email = models.EmailField(unique=True)
    is_brand_owner = models.BooleanField(default=False)
    datetime_created = models.DateTimeField(auto_now_add=True)

    USERNAME_FIELD = 'email'

    REQUIRED_FIELDS = []

    objects = CustomUserManager()

    def __str__(self):
        return self.email

class Cart(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    items = models.ManyToManyField('OrderItem', blank=True)

    def __str__(self):
        return "{}'s cart".format(self.user.username)

    def get_total(self):
        return sum([item.get_total_amount() for item in self.items])

class Order(models.Model):
    ref = models.UUIDField(default=uuid.uuid4, primary_key=True, editable=False, unique=True)
    datetime_created = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)
    completed = models.BooleanField(default=False)
    order_item = models.OneToOneField('OrderItem', blank=True, null=True, on_delete=models.CASCADE)
    
    def __str__(self):
        return str(self.uuid)

class OrderItem(models.Model):
    quantity = models.PositiveIntegerField(default=1)
    variant = models.OneToOneField('Variant', on_delete=models.CASCADE)
    size = models.OneToOneField("Size", on_delete=models.CASCADE)

    def get_total_amount(self):
        return self.variant.product.price * self.quantity

class Image(models.Model):
    product = models.ForeignKey('Product', related_name='images', on_delete=models.CASCADE)
    url = models.URLField()

    def __str__(self):
        return f'image for {self.product.name}'

class SizeChart(models.Model):
    name = models.CharField(max_length=20)

class Size(models.Model):
    size = models.CharField(max_length=20, default='N/A')
    is_available = models.BooleanField(default=True)
    variant = models.ForeignKey('Variant', related_name="sizes", on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)

class Variant(models.Model):
    product = models.ForeignKey('Product', on_delete=models.CASCADE, related_name="variants")
    image_url = models.URLField()
    is_available = models.BooleanField(default=True)
    quantity = models.PositiveIntegerField(default=1)


class Product(models.Model):
    name = models.CharField(max_length = 150)
    display_image = models.URLField()
    datetime_created = models.DateTimeField(auto_now_add=True)
    category = models.ForeignKey('Category', on_delete=models.CASCADE, related_name='products')
    description = models.TextField(blank=True, null=True)
    quantity = models.PositiveIntegerField(default=1)
    brand = models.ForeignKey('Brand', related_name="products", on_delete=models.CASCADE)
    is_available = models.BooleanField(default=True)
    price = models.PositiveIntegerField()
    customers = models.ManyToManyField(User, related_name='users', blank=True)
    
    def __str__(self):
        return '{} ({} NGN)'.format(self.name, self.get_price())

    def get_price(self):
        return self.price / 100

    def get_stars(self):
        return round(statistics.mean([x.start for x in self.review_set.all()]), 1)

class Brand(models.Model):
    logo = models.URLField(null=True, blank=True)
    owner = models.ForeignKey(User, related_name='brands', on_delete=models.CASCADE)
    datetime_created = models.DateTimeField(auto_now_add=True)
    name = models.CharField(max_length = 150)
    percentage = models.FloatField(default=0.05)

    def __str__(self):
        return self.name

class Category(models.Model):
    name = models.CharField(max_length=150, unique=True)

    class Meta:
        verbose_name = 'categories'
    
    def __str__(self) -> str:
        return self.name

class Message(models.Model):

    MESSAGE_STATUS = (
        ('order.successful', 'order.successful'),
        ('order.failed', 'order.failed'),
        ('product.unavailable', 'product.unavailable'),
        ('product_variant.unavailable', 'product_variant.unavailable'),
        ('variant_size.unavailable', 'variant_size.unavailable'),
        ('transfer.successful', 'transfer.successful'),
        ('transfer.failed', 'transfer.failed'),
    )

    message = models.CharField(max_length=250)
    datetime_created = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=50, choices=MESSAGE_STATUS)
    brand = models.ForeignKey(Brand, on_delete=models.CASCADE)
    order_items = models.ManyToManyField(OrderItem, blank=True)
    user = models.OneToOneField(User, blank=True, null=True, on_delete=models.SET_NULL)

    def __str__(self):
        return 'Message for {}'.format(self.brand.name)

class Account(models.Model):
    bank = models.ForeignKey('Bank', on_delete=models.CASCADE)
    acct_no = models.CharField(max_length=10, validators=[validate_acct_no])
    acct_name = models.CharField(max_length=250, blank=True, null=True)
    brand = models.OneToOneField(Brand, on_delete=models.CASCADE)
    subaccount_code = models.CharField(max_length=255, blank=True, null=True)
    recipient_code = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return self.acct_no



class Bank(models.Model):
    code = models.CharField(max_length=3)
    name = models.CharField(max_length=250)

    def __str__(self):
        return self.name

class Transfer(models.Model):
    ref = models.UUIDField(default=uuid.uuid4, primary_key=True, editable=False, unique=True)
    code = models.CharField(blank=True, null=True, max_length=250)
    brand = models.ForeignKey(Brand, null=True, on_delete=models.SET_NULL)
    amount = models.PositiveIntegerField()
    paid = models.BooleanField(default=False)

class Review(models.Model):
    user = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)
    review = models.TextField()
    stars = models.PositiveIntegerField()
    product = models.ForeignKey(Product, on_delete=models.CASCADE)

@receiver(post_save, sender=User)
def create_user_cart(sender, instance, created, **kwargs):
    if created:
        Cart.objects.create(
            user=instance
        )
        Token.objects.create(
            user=instance
        )

@receiver(post_save, sender=User)
def save_user_cart(sender, instance, **kwargs):
    instance.cart.save()
    
