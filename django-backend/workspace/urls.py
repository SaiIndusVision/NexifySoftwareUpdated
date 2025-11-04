from django.urls import path,include
from .views import *
from rest_framework.routers import DefaultRouter

router = DefaultRouter()
router.register('workspace', WorkspaceViewSet, basename='WorkspaceAPI')
router.register('workspace-activate', WorkspaceActivationViewSet, basename='WorkspaceActivationAPI')
router.register('workspace-validate', WorkspaceValidateViewSet, basename='WorkspaceValidationAPI')
router.register('image-upload', ImageUploadViewSet, basename='ImageUploadAPI')
router.register('field-assistant-verification', FielEngineerVerification, basename='FielEngineerVerificationViewset')
router.register('serial-number', SerialNumberViewset, basename='SerialNumberViewSet')
urlpatterns= [
    path('', include(router.urls)),
]