from rest_framework import permissions
from .models import Product

class IsOwnerByBrand(permissions.BasePermission):

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        return obj.brand.owner == request.user



class CanReview(permissions.BasePermission):

    def has_permission(self, request, view):
        if view.action == "create":
            product_id = request.data.get("product", None)
            if product_id:
                product = Product.objects.get(id=int(product_id[0]))
                return bool(
                    request.user and
                    request.user.is_authenticated and
                    request.user in product.customers.all()
                )
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        return request.user in obj.product.customers.all()
        
class IsUser(permissions.BasePermission):

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        return bool(request.user == obj)

class IsBrandOwner(permissions.BasePermission):

    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        return bool(request.user == obj.owner)

class IsABrandOwner(permissions.BasePermission):

    def has_permission(self, request, view):
        return bool(request.user and
        request.user.is_authenticated and 
        request.user.is_brand_owner)

class CanEditSize(permissions.BasePermission):

    def has_permission(self, request, view):
        if view.action == "create":
            variant_id = request.data.get("variant", None)
            if variant_id:
                variant = Variant.objects.get(id=int(variant_id[0]))
                return bool(
                    request.user and
                    request.user.is_authenticated and
                    request.user == variant.product.brand.owner
                )
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        return obj.variant.product.brand.owner == request.user


class IsProductOwner(permissions.BasePermission):

    def has_permission(self, request, view):
        if view.action == "create":
            product_id = request.data.get("product", None)
            if product_id:
                product = Product.objects.get(id=int(product_id[0]))
                return bool(
                   request.user and
                   request.user.is_authenticated and
                   request.user == product.brand.owner 
                )

        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        return bool(obj.product.brand.owner == request.user)

class IsAccountOwner(permissions.BasePermission):

    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        return bool(obj.brand.owner == request.user)

class IsOrderer(permissions.BasePermission):

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        return bool(obj.user == request.user)