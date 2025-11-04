from django.db import models
from users.models import CustomUser

# Create your models here.

class Workspace(models.Model):
    class Meta:
        db_table = "Workspace"
    name = models.CharField(max_length=100,blank=True,null=True)
    activation_key = models.CharField(max_length=100,blank=True,null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL,null=True)
    is_activated = models.BooleanField(null=True,default=False)
    activation_key_expiry = models.DateTimeField(null=True)
    failed_activation_attempts = models.PositiveIntegerField(default=0,null=True,blank=True)
    field_assistant = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, related_name="field_assistant")
    sku_count = models.PositiveBigIntegerField(null=True,default=5)
    
class TrainingImage(models.Model):
    class Meta:
        db_table = "TrainingImage"
    workspace = models.ForeignKey(Workspace, on_delete=models.SET_NULL, null=True)
    image = models.ImageField(upload_to="training_images/")
    uploaded_at = models.DateTimeField(auto_now_add=True)
