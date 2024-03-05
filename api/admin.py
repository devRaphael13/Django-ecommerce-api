from django.contrib import admin
from api.models import (
    User,
    Cart,
    Order,
    OrderItem,
    Image,
    Size,
    Product,
    Category,
    Review,
)

admin.site.register(User)
admin.site.register(Cart)
admin.site.register(Order)
admin.site.register(OrderItem)
admin.site.register(Image)
admin.site.register(Size)
admin.site.register(Product)
admin.site.register(Category)
admin.site.register(Review)

