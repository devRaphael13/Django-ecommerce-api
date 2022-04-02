from ctypes.wintypes import SIZE
import statistics
import uuid
from django.core.exceptions import ValidationError
from django.db import models
from django.contrib.auth.models import AbstractUser, User
from django.dispatch import receiver
from django.db.models.signals import post_save, pre_save
from rest_framework.authtoken.models import Token


def validate_acct_no(value):
    if len(value) != 10:
        raise ValidationError("Field 'acct_no' cannot be more or less than 10 digits")
    
    if not value.isnumeric():
        raise ValidationError("Field 'acct_no' may only contain digits")

    

class User(AbstractUser):
    pic = models.ImageField(upload_to='profile_images/', blank=True, null=True)
    is_brand_owner = models.BooleanField(default=False)
    datetime_created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.username

    def get_cart_total(self):
        total = 0
        for item in self.cart.items.all():
            total += item.get_total_amount()
        return total

  
class Cart(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    items = models.ManyToManyField('Variant', blank=True)

    def __str__(self):
        return "{}'s cart".format(self.user.username)

class Order(models.Model):
    ref = models.UUIDField(default=uuid.uuid4, primary_key=True, editable=False, unique=True)
    datetime_created = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)
    completed = models.BooleanField(default=False)
    order_item = models.OneToOneField('OrderItem', blank=True, null=True, on_delete=models.CASCADE)
    
    def __str__(self):
        return str(self.uuid)


class OrderItem(models.Model):
    size = models.OneToOneField('Size', null=True, on_delete=models.SET_NULL)
    quantity = models.PositiveIntegerField(default=1)
    variant = models.OneToOneField('Variant', on_delete=models.CASCADE)

    def get_total_amount(self):
        return self.variant.product.price * self.quantity

class Image(models.Model):
    variant = models.ForeignKey('Variant', related_name='images', on_delete=models.CASCADE)
    images = models.ImageField(upload_to='product_images/')

    def __str__(self):
        return f'image for {self.product.name}'

class Size(models.Model):
    SIZES = (
        ('N/A', 'N/A'),
        ('One size fits all', 'One size fits all'),
        ('XS', 'XS'),
        ('S', 'S'),
        ('M', 'M'),
        ('L', 'L'),
        ('XL', 'XL'),
        ('XXL', 'XXL'),
        ('XXXL', 'XXXL'),
        ('20', '20'), ('21', '21'), ('22', '22'), ('23', '23'), ('24', '24'), ('25', '25'), ('26', '26'), ('27', '27'), ('28', '28'), ('29', '29'),
        ('30', '30'), ('31', '31'), ('32', '32'), ('33', '33'), ('34', '34'), ('35', '35'), ('36', '36'), ('37', '37'), ('38', '38'), ('39', '39'),
        ('40', '40'), ('41', '41'), ('42', '42'), ('43', '43'), ('44', '44'), ('45', '45'), ('46', '46'), ('47', '47'), ('48', '48'), ('49', '49'),
        ('50', '50'), ('51', '51'), ('52', '52'), ('53', '53'), ('54', '54'), ('55', '55'), ('56', '56'), ('57', '57'), ('58', '58'), ('59', '59'),
        ('60', '60'),
    )

    size = models.CharField(max_length=20, default='N/A', choices=SIZES)
    is_available = models.BooleanField(default=True)
    variant = models.ForeignKey('Variant', on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)

class Color(models.Model):
    name = models.CharField(max_length=120, unique=True)
    code = models.CharField(max_length=6)

class Variant(models.Model):
    product = models.ForeignKey('Product', on_delete=models.CASCADE)
    color = models.OneToOneField('Color', null=True, on_delete=models.SET_NULL)
    is_available = models.BooleanField(default=True)
    quantity = models.PositiveIntegerField(default=1)



class Product(models.Model):
    name = models.CharField(max_length = 150)
    datetime_created = models.DateTimeField(auto_now_add=True)
    category = models.ForeignKey('Category', on_delete=models.CASCADE)
    description = models.TextField(blank=True, null=True)
    quantity = models.PositiveIntegerField(default=1)
    brand = models.ForeignKey('Brand', related_name="products", on_delete=models.CASCADE)
    is_available = models.BooleanField(default=True)
    price = models.IntegerField()
    customers = models.ManyToManyField(User, related_name='users', blank=True)
    
    def __str__(self):
        return '{} ({} NGN)'.format(self.name, self.get_price())

    def get_price(self):
        return self.price / 100

    def get_stars(self):
        return round(statistics.mean([x.start for x in self.review_set.all()]), 1)


class Brand(models.Model):
    logo = models.ImageField(upload_to='logos/', blank=True, null=True)
    owner = models.ForeignKey(User, related_name='brands', on_delete=models.CASCADE)
    datetime_created = models.DateTimeField(auto_now_add=True)
    name = models.CharField(max_length = 150)

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

class AccountDetail(models.Model):
    bank = models.ForeignKey('Bank', on_delete=models.CASCADE)
    acct_no = models.CharField(max_length=10, validators=[validate_acct_no])
    acct_name = models.CharField(max_length=250, blank=True, null=True)
    brand = models.ForeignKey(Brand, related_name='accounts', on_delete=models.CASCADE)
    recipient_code = models.CharField(max_length=255, blank=True, null=True)
    in_use = models.BooleanField(default=True)

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


# Signals for the Models bro.
@receiver(post_save, sender=AccountDetail)
def update_in_use(sender, instance, created, **kwargs):
    if created or instance.in_use:
        AccountDetail.objects.filter(brand=instance.brand).exclude(id=instance.id).update(in_use=False)


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
    
