from django.db import models
from workspace.models import *
# Create your models here.

class Tags(models.Model):
    class Meta:
        db_table = 'Tags'
    name = models.CharField(max_length=100,blank=True,null=True)
    is_active = models.BooleanField(default=True,null=True)


class SKU(models.Model):
    class Meta:
        db_table = "SKU"
    workspace = models.ForeignKey(Workspace,on_delete=models.CASCADE,null=True)
    tag = models.ForeignKey(Tags,on_delete=models.SET_NULL,null=True)
    name = models.CharField(max_length=100,blank=True,null=True)
    created_date_time = models.CharField(max_length=100,blank=True,null=True)
    updated_date_time  = models.CharField(max_length=100,blank=True,null=True)
    max_count = models.PositiveBigIntegerField(default=5, null=True, blank=True)
    count = models.PositiveBigIntegerField(default=0, null=True, blank=True)
    
class Labels(models.Model):
    class Meta:
        db_table = "Labels"
    name = models.CharField(max_length=100,blank=True,null=True)
    sku= models.ForeignKey(SKU,on_delete=models.CASCADE,null=True)
    shortcut_key = models.CharField(max_length=100,blank=True,null=True)
    color_code = models.CharField(max_length=100,blank=True,null=True)
    is_active = models.BooleanField(default=True,null=True)
    
class Versions(models.Model):
    class Meta:
        db_table = "Versions"
    name = models.CharField(max_length=100,blank=True,null=True)
    sku = models.ForeignKey(SKU,on_delete=models.CASCADE,null=True)

def sku_image_upload_path(instance, filename):
    version_name = instance.version.name if instance.version and instance.version.name else "default"
    return f'sku_images/{instance.sku.id}/{version_name}/{filename}'


class SKUImages(models.Model):
    class Meta:
        db_table = "SKUImages"

    sku = models.ForeignKey('SKU', on_delete=models.CASCADE)
    tags = models.CharField(max_length=100, blank=True, null=True)
    version = models.ForeignKey(Versions,on_delete=models.CASCADE,null=True)
    image = models.ImageField(upload_to=sku_image_upload_path)
    original_filename = models.CharField(max_length=255, null=True)  # Store client-provided filename
    content_hash = models.CharField(max_length=32, null=True)  # Store MD5 hash for deduplication
    label = models.ForeignKey(Labels,on_delete=models.SET_NULL,null=True)
    rejected = models.BooleanField(default=False)  # Flag to indicate if the image was rejected
    split_label = models.CharField(max_length=100, blank=True, null=True)  # Store split label if applicable
    data_set = models.BooleanField(default=False)  # Flag to indicate if the image is part of a dataset
    def __str__(self):
        return f"{self.original_filename or self.image.name} ({self.sku.id})"
    
class TestResultsFolder(models.Model):
    class Meta:
        db_table = "TestResultsFolder"
    sku = models.ForeignKey(SKU, on_delete=models.CASCADE, null=True)
    name = models.CharField(max_length=100, blank=True, null=True)

def test_image_upload_path(instance, filename):
    base_path = f'sku_images/{instance.sku.id}'
    folder_name = instance.folder.name if instance.folder and instance.folder.name else "default"
    return f'{base_path}/{folder_name}/{filename}'


class TestResults(models.Model):
    class Meta:
        db_table = "TestResults"
    sku = models.ForeignKey(SKU, on_delete=models.SET_NULL, null=True)
    version = models.ForeignKey(Versions, on_delete=models.SET_NULL, null=True)
    folder = models.ForeignKey(TestResultsFolder, on_delete=models.CASCADE, null=True)
    image = models.ImageField(upload_to=test_image_upload_path)
    meta_data = models.JSONField(default=dict, blank=True, null=True)  # Store additional metadata

    
from django.db.models.signals import post_migrate
from django.apps import apps
from django.db import connection

def create_default_tags(sender, **kwargs):
    if not connection.alias == 'default':
        return
    Tags = apps.get_model('sku', 'Tags')  # ← your app name is "sku"
    if not Tags.objects.exists():
        Tags.objects.update_or_create(id=1, defaults={'name': 'AnamolyDetection', 'is_active': True})
        Tags.objects.update_or_create(id=2, defaults={'name': 'CustomDetection', 'is_active': True})

post_migrate.connect(create_default_tags, sender=apps.get_app_config('sku'))


def create_default_labels(sender, **kwargs):
    if connection.alias != 'default':
        return
    Labels = apps.get_model('sku', 'Labels')

    # Check if 'Good' and 'Bad' labels already exist (avoid duplication)
    if not Labels.objects.filter(name__iexact='Good').exists():
        Labels.objects.create(name='Good', sku=None, shortcut_key='G', color_code='green', is_active=True)
    if not Labels.objects.filter(name__iexact='Bad').exists():
        Labels.objects.create(name='Bad', sku=None, shortcut_key='B', color_code='red', is_active=True)

post_migrate.connect(create_default_labels, sender=apps.get_app_config('sku'))






