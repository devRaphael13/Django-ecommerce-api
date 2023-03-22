from django.contrib import admin
from api.models import (
    User,
    Cart,
    Order,
    OrderItem,
    Image,
    SizeChart,
    Size,
    Variant,
    Product,
    Brand,
    Category,
    Message,
    Account,
    Bank,
    Transfer,
    Review,
)

admin.site.register(User)
admin.site.register(Cart)
admin.site.register(Order)
admin.site.register(OrderItem)
admin.site.register(Image)
admin.site.register(SizeChart)
admin.site.register(Size)
admin.site.register(Variant)
admin.site.register(Product)
admin.site.register(Brand)
admin.site.register(Category)
admin.site.register(Message)
admin.site.register(Account)
admin.site.register(Bank)
admin.site.register(Transfer)
admin.site.register(Review)

