from django.urls import path,include
from .views import *
from rest_framework.routers import DefaultRouter

router = DefaultRouter()
router.register('user', UserAPIView, basename='User')
router.register('login',LoginAPIView,basename='Login')
router.register('secret-key',SecretKeyValidationAPI,basename="Secret Key")
router.register('forgot-password',ResetPasswordAPIView,basename='ForgotPassword')
router.register('reset-link-validate',ValidateResetLink,basename='ResetLinkValidate')
router.register('system-info', SystemInfoViewSet, basename='system-info')
router.register('mac-address-validate', MacAddressValidationViewSet, basename='MacAddressValidationAPI')
router.register('role',RoleViewSet,basename="RoleAPIView")
urlpatterns= [
    path('', include(router.urls)),
    path('index/', index, name='index'),  # Add this line to serve the index view
]