from rest_framework import permissions
from .models import Product


class IsUser(permissions.BasePermission):

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        user = obj.user if obj.user else obj
        return bool(request.user == user)


class IsVendor(permissions.BasePermission):

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        item = obj.product if obj.product else obj
        return bool(request.user == item.vendor.user)


class IsAVendor(permissions.BasePermission):

    def has_permission(self, request, view):
        return bool(
            request.user and request.user.is_authenticated and request.user.is_vendor
        )


class CanReview(permissions.BasePermission):

    def has_permission(self, request, view):
        if view.action == "create":
            product_id = request.data.get("product", None)
            if product_id:
                product = Product.objects.get(id=int(product_id[0]))
                return bool(
                    request.user
                    and request.user.is_authenticated
                    and request.user in product.customers.all()
                )
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        return request.user in obj.product.customers.all()


