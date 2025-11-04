from django.db import models
from django.contrib.auth.models import AbstractUser

# Create your models here.

class Role(models.Model):
    class Meta:
        db_table = "Role"
    name = models.CharField(max_length=100,blank=True,null=True)
    is_active = models.BooleanField(null=True,default=True)

class CustomUser(AbstractUser):
    class Meta:
        db_table = "CustomUser"
    first_name = models.CharField(max_length=100,blank=True,null=True)
    last_name = models.CharField(max_length=100,blank=True,null=True)
    email = models.EmailField(null=True,blank=True)
    country_code = models.CharField(max_length=100,null=True,blank=True)
    phone_number = models.CharField(max_length=100,null=True,blank=True)
    password = models.CharField(max_length=250,blank=True,null=True)
    secret_key = models.CharField(max_length=100,blank=True,null=True)
    secret_key_verified = models.BooleanField(null=True,default=False)
    role = models.ForeignKey(Role,on_delete=models.SET_NULL,null=True)
    serial_number = models.CharField(max_length=100,blank=True,null=True)
    is_authorized = models.BooleanField(null=True,default=True)
    started_on = models.DateField(null=True)
    is_verified = models.BooleanField(default=False,null=True)
    failed_login_attempts = models.PositiveIntegerField(default=0,null=True,blank=True)
    last_failed_login = models.DateTimeField(null=True, blank=True)
    link_expire_token = models.CharField(max_length=250,null=True,blank=True)
    

class DisposableDomains(models.Model):
    class Meta:
        db_table = "DisposableDomains"
    domain_name = models.CharField(max_length=100,blank=True,null=True)