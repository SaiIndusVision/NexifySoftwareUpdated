from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ImageModificationVisualizerAPI

router = DefaultRouter()
router.register(r'image_modifier', ImageModificationVisualizerAPI, basename='image_modifier')

urlpatterns = [
    path('', include(router.urls)),
]
