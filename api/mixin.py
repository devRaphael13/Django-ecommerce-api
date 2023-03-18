import redis
import json
from django.conf import settings
from rest_framework.viewsets import GenericViewSet
from rest_framework.response import Response
from rest_framework import status
from rest_framework.settings import api_settings

redis_client = redis.Redis(
    host=settings.REDIS_HOSTNAME,
    port=settings.REDIS_PORT,
    password=settings.REDIS_PASSWORD
    )

class CustomCreateMixin:
    """
    Create a model instance.
    """
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = self.perform_create(serializer)
        if data:
            if data["status"]:
                serializer.validated_data.update(data["data"])
            else:
                return Response(data["error"], status=status.HTTP_400_BAD_REQUEST)
        redis_client.delete(f"{serializer.Meta.model.__name__}_list*")
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def get_success_headers(self, data):
        try:
            return {'Location': str(data[api_settings.URL_FIELD_NAME])}
        except (TypeError, KeyError):
            return {}

    def perform_create(self, serializer):
        serializer.save()

class CustomListMixin:
    """
    List a queryset.
    """
    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        model_name = queryset.model.__name__
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            name = f"{model_name}_list_page_{self.get_offset(request.query_params)}"
            data = redis_client.get(name)
            if data:
                return self.get_paginated_response(json.loads(data))
            
            res = self.get_paginated_response(serializer.data)
            redis_client.set(name, json.dumps(res.data))
            return res

        name = f"{model_name}_list"
        data = redis_client.get(name)
        if data:
            return Response(json.loads(data), status=status.HTTP_200_OK)
        serializer = self.get_serializer(queryset, many=True)
        redis_client.set(name, json.dumps(serializer.data))
        return Response(serializer.data)
    
    def get_offset(self, params):
        offset = params.get("offset", None)
        if offset:
            return int(offset[0]) + 1
        return 1


class CustomRetrieveMixin:
    """
    Retrieve a model instance.
    """
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        model_name = instance.__class__.__name__
        name = f"{model_name}_{instance.pk}"
        data = redis_client.get(name)
        if data:
            return Response(json.loads(data), status=status.HTTP_200_OK)
        
        redis_client.set(name, json.dumps(serializer.data))
        return Response(serializer.data)

class CustomUpdateMixin:
    """
    Update a model instance.
    """
    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)

        data = self.perform_update(serializer)
        if data:
            if data["status"]:
                serializer.validated_data.update(data["data"])
            else:
                return Response(data["error"], status=status.HTTP_400_BAD_REQUEST)
                
        redis_client.delete(f"{instance.__class__.__name__}_*")
        if getattr(instance, '_prefetched_objects_cache', None):
            # If 'prefetch_related' has been applied to a queryset, we need to
            # forcibly invalidate the prefetch cache on the instance.
            instance._prefetched_objects_cache = {}
        return Response(serializer.data)
    
    def partial_update(self, request, *args, **kwargs):
        kwargs['partial'] = True
        return self.update(request, *args, **kwargs)

    def perform_update(self, serializer):
        serializer.save()

class CustomDestroyMixin:
    """
    Destroy a model instance.
    """
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        redis_client.delete(f"{instance.__class__.__name__}_*")
        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)
    
    def perform_destroy(self, instance):
        instance.delete()

class CustomModelViewSet(
    CustomListMixin,
    CustomCreateMixin,
    CustomUpdateMixin,
    CustomRetrieveMixin,
    CustomDestroyMixin,
    GenericViewSet
):
    """
    Custom Model viewset with caching feature.
    """
    pass

class CustomReadOnlyViewSet(
    CustomListMixin,
    CustomRetrieveMixin,
    GenericViewSet
):
    """
    Custom Read only viewset with caching feature.
    """
    pass