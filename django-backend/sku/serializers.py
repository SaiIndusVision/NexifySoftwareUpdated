from rest_framework import serializers
from .models import SKU,SKUImages

class SKUSerializer(serializers.ModelSerializer):
    tag_name = serializers.SerializerMethodField()
    version_count = serializers.SerializerMethodField()
    image_count = serializers.SerializerMethodField()
    first_image = serializers.SerializerMethodField()

    class Meta:
        model = SKU
        fields = '__all__'  # ✅ Use correct "__all__"
        extra_fields = ['tag_name', 'version_count', 'image_count', 'first_image']

    def get_tag_name(self, obj):
        return obj.tag.name if obj.tag else None

    def get_version_count(self, obj):
        return obj.versions_set.count()

    def get_image_count(self, obj):
        return SKUImages.objects.filter(sku=obj).count()

    def get_first_image(self, obj):
        first_image = SKUImages.objects.filter(sku=obj).order_by('id').first()
        if first_image and first_image.image:
            request = self.context.get('request')
            if request is not None:
                return request.build_absolute_uri(first_image.image.url)
            return first_image.image.url
        return None



class SKUImagesSerializer(serializers.ModelSerializer):
    sku_name = serializers.SerializerMethodField()
    version_name = serializers.CharField(source='version.name', read_only=True)
    label_id = serializers.IntegerField(source='label.id', read_only=True)
    label_name = serializers.CharField(source='label.name', read_only=True)
    label_color_code = serializers.CharField(source='label.color_code', read_only=True)

    class Meta:
        model = SKUImages
        fields = [
            'id', 'sku', 'sku_name', 'tags', 'image',
            'original_filename', 'content_hash', 'version', 'version_name',
            'label_id', 'label_name', 'label_color_code','rejected','data_set','split_label'
        ]

    def get_sku_name(self, obj):
        return obj.sku.name if obj.sku else None



class SKUImageLabelSerializer(serializers.ModelSerializer):
    image = serializers.SerializerMethodField()
    label_id = serializers.SerializerMethodField()
    split_label = serializers.CharField(read_only=True)
    class Meta:
        model = SKUImages
        fields = ['image', 'label_id', 'split_label']

    def get_image(self, obj):
        absolute = self.context.get('absolute_path', False)
        try:
            if absolute:
                return obj.image.path  # Absolute path on disk
            else:
                request = self.context.get('request')
                return request.build_absolute_uri(obj.image.url) if request else obj.image.url
        except:
            return None

    def get_label_id(self, obj):
        if obj.label and obj.label.name.lower() == "good":
            return 0
        elif obj.label and obj.label.name.lower() == "bad":
            return 1
        return None