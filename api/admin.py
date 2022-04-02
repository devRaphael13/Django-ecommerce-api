from django.contrib import admin
from api.models import Category, Product, Brand, Cart, Order, Image, User

admin.site.register(Category)
admin.site.register(Image)
admin.site.register(Product)
admin.site.register(Brand)
admin.site.register(Cart)
admin.site.register(Order)
admin.site.register(User)
