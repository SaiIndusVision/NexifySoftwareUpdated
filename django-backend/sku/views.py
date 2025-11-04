# sku/views.py
from rest_framework import viewsets, status
from rest_framework.response import Response
from .models import SKU,Tags,Versions,Labels,TestResults,TestResultsFolder
from .serializers import SKUSerializer,SKUImageLabelSerializer
from django.shortcuts import get_object_or_404
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from rest_framework.decorators import action
from django.core.files.base import ContentFile
import base64, hashlib, secrets
import random
import datetime
import os
import hashlib
import logging
from rest_framework import viewsets, status
from rest_framework.response import Response
from .models import SKUImages, SKU, Versions
from .serializers import SKUImagesSerializer
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.core.files import File
from django.core.files.storage import default_storage
import shutil
import os
from django.db import transaction
from django.conf import settings
from django.db.models import Count,Q
import hashlib
import zipfile
import tempfile
from django.core.files.uploadedfile import SimpleUploadedFile

# logger = logging.getLogger(_name_)

class SKUViewSet(viewsets.ViewSet):
    
    @swagger_auto_schema(
        operation_summary="List SKUs",
        operation_description="Returns a list of SKUs. Optionally filter by workspace_id and tag_id.",
        manual_parameters=[
            openapi.Parameter(
                'workspace_id',
                openapi.IN_QUERY,
                description="Filter SKUs by Workspace ID",
                type=openapi.TYPE_INTEGER,
                required=False
            ),
            openapi.Parameter(
                'tag_id',
                openapi.IN_QUERY,
                description="Filter SKUs by Tag ID",
                type=openapi.TYPE_INTEGER,
                required=False
            )
        ],
        responses={200: SKUSerializer(many=True)}
    )
    def list(self, request):
        workspace_id = request.query_params.get("workspace_id")
        tag_id = request.query_params.get("tag_id")

        queryset = SKU.objects.all()

        if workspace_id:
            queryset = queryset.filter(workspace_id=workspace_id)
        if tag_id:
            queryset = queryset.filter(tag_id=tag_id)

        serializer = SKUSerializer(queryset, many=True)
        return Response({"results": serializer.data}, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        operation_summary="Create SKU",
        operation_description="Create a new SKU with workspace and optional tag. Block if max_count reached.",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["workspace", "name"],
            properties={
                "workspace": openapi.Schema(type=openapi.TYPE_INTEGER, description="Workspace ID"),
                "tag": openapi.Schema(type=openapi.TYPE_INTEGER, description="Tag ID", nullable=True),
                "name": openapi.Schema(type=openapi.TYPE_STRING, description="SKU Name"),
                "created_date_time": openapi.Schema(type=openapi.TYPE_STRING, format="date-time", description="Creation Time", nullable=True),
                "updated_date_time": openapi.Schema(type=openapi.TYPE_STRING, format="date-time", description="Updated Time", nullable=True),
            }
        ),
        responses={
            201: openapi.Response(description="SKU created successfully", schema=SKUSerializer),
            400: openapi.Response(description="Bad request or max count reached"),
        }
    )
    def create(self, request):
        workspace = request.data.get('workspace')
        name = request.data.get('name')

        # Check for duplicate SKU
        if SKU.objects.filter(workspace_id=workspace, name__iexact=name).exists():
            return Response(
                {
                    "message": f"SKU with name '{name}' already exists in this workspace.",
                    "status": status.HTTP_400_BAD_REQUEST
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        # 🔄 Check total SKUs in this workspace
        total_existing_skus = SKU.objects.filter(workspace_id=workspace).count()

        # ✅ Check against latest max_count (from latest SKU)
        latest_sku = SKU.objects.filter(workspace_id=workspace).order_by('-id').first()
        if latest_sku and latest_sku.max_count is not None:
            if total_existing_skus >= latest_sku.max_count:
                return Response(
                    {
                        "message": f"Cannot create more SKUs. Max limit of {latest_sku.max_count} reached for this workspace.",
                        "status": status.HTTP_400_BAD_REQUEST
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )

        # Save SKU
        serializer = SKUSerializer(data=request.data)
        if serializer.is_valid():
            sku_instance = serializer.save()

            # 🔼 After saving, increment its `count`
            sku_instance.count = 1
            sku_instance.save()

            return Response(
                {"message": "SKU Created Successfully", "status": status.HTTP_201_CREATED},
                status=status.HTTP_201_CREATED
            )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @swagger_auto_schema(responses={200: SKUSerializer})
    def retrieve(self, request, pk=None):
        sku = get_object_or_404(SKU, pk=pk)
        serializer = SKUSerializer(sku)
        return Response({"results":serializer.data})

    @swagger_auto_schema(
        operation_summary="Update SKU",
        operation_description="Update an existing SKU, including name, workspace, tag, and max_count.",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["workspace", "name"],  # Required fields
            properties={
                "workspace": openapi.Schema(type=openapi.TYPE_INTEGER, description="Workspace ID"),
                "tag": openapi.Schema(type=openapi.TYPE_INTEGER, description="Tag ID", nullable=True),
                "name": openapi.Schema(type=openapi.TYPE_STRING, description="SKU Name"),
                "created_date_time": openapi.Schema(type=openapi.TYPE_STRING, format="date-time", description="Creation Time", nullable=True),
                "updated_date_time": openapi.Schema(type=openapi.TYPE_STRING, format="date-time", description="Updated Time", nullable=True),
                "max_count": openapi.Schema(type=openapi.TYPE_INTEGER, description="Maximum SKU allowed in this workspace", nullable=True),
            }
        ),
        responses={
            200: openapi.Response(description="SKU updated successfully", schema=SKUSerializer),
            400: openapi.Response(description="Bad request or name conflict")
        }
    )
    def update(self, request, pk=None):
        sku = get_object_or_404(SKU, pk=pk)
        name = request.data.get('name')
        workspace = request.data.get('workspace')

        # Check if name already exists in the workspace (excluding current SKU)
        if SKU.objects.filter(workspace_id=workspace, name__iexact=name).exclude(id=sku.id).exists():
            return Response(
                {
                    "message": f"SKU with name '{name}' already exists in this workspace.",
                    "status": status.HTTP_400_BAD_REQUEST
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = SKUSerializer(sku, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({"message": "SKU updated successfully", "results": serializer.data})
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)



    @swagger_auto_schema(responses={204: 'No content'})
    def destroy(self, request, pk=None):
        sku = get_object_or_404(SKU, pk=pk)

        # Fetch all versions related to this SKU
        versions = Versions.objects.filter(sku=sku)

        for version in versions:
            # Fetch all images in this version
            images = SKUImages.objects.filter(version=version)

            for image in images:
                # Delete image file from storage if it exists
                if image.image and default_storage.exists(image.image.name):
                    default_storage.delete(image.image.name)

                # Delete SKUImage instance
                image.delete()

            # Delete version after its images are deleted
            version.delete()

        # Delete any SKUImages directly tied to SKU but not any version
        loose_images = SKUImages.objects.filter(sku=sku, version__isnull=True)
        for image in loose_images:
            if image.image and default_storage.exists(image.image.name):
                default_storage.delete(image.image.name)
            image.delete()

        # Delete the SKU
        sku.delete()

        # After deleting, remove the folder sku_images/<sku.id> from media storage
        sku_folder_path = os.path.join(settings.MEDIA_ROOT, f"sku_images/{pk}")
        if os.path.exists(sku_folder_path):
            try:
                shutil.rmtree(sku_folder_path)  # Force delete the folder and its contents
            except Exception as e:
                return Response({
                    "message": f"SKU deleted, but failed to delete image folder: {str(e)}",
                    "status": 500
                }, status=500)

        return Response({
            "message": "SKU and its associated versions, images, and folders deleted successfully",
            "status": 204
        })
class SKUImagesViewSet(viewsets.ViewSet):

    def create(self, request, *args, **kwargs):
        sku_id = request.data.get('sku_id')
        version_id = request.data.get('version_id')
        tags = request.data.get('tags', '')
        allow_duplicates = request.data.get('allow_duplicates', 'false').lower() == 'true'
        overwrite = request.data.get('overwrite', 'false').lower() == 'true'
        zip_file = request.FILES.get('zip_folder')
        image_files = request.FILES.getlist('images')

        if not sku_id or not version_id:
            return Response({"message": "Both 'sku_id' and 'version_id' are required.","status": status.HTTP_400_BAD_REQUEST}, status=status.HTTP_400_BAD_REQUEST)
        # Don't allow both zip and image files at the same time
        if zip_file and image_files:
            return Response(
                {"message": "Please upload either a folder or individual images, not both at the same time.","status": status.HTTP_400_BAD_REQUEST},status=status.HTTP_400_BAD_REQUEST
            )

        try:
            sku = SKU.objects.get(id=sku_id)
            version = Versions.objects.get(id=version_id)
        except (SKU.DoesNotExist, Versions.DoesNotExist):
            return Response({"message": "Invalid sku_id or version_id."}, status=status.HTTP_404_NOT_FOUND)

        created_entries = []
        skipped_entries = []
        processed_hashes = set()

        existing_hashes = set(
            SKUImages.objects.filter(sku=sku, version=version)
            .exclude(content_hash__isnull=True)
            .values_list('content_hash', flat=True)
        )

        # Helper to handle individual files
        def handle_file(file_obj, file_name):
            nonlocal created_entries, skipped_entries, processed_hashes, existing_hashes

            file_content = file_obj.read()
            content_hash = hashlib.md5(file_content).hexdigest()
            file_obj.seek(0)

            existing_entry = SKUImages.objects.filter(
                sku=sku,
                version=version,
                original_filename=file_name
            ).first()

            if existing_entry and overwrite:
                if existing_entry.image and existing_entry.image.storage.exists(existing_entry.image.name):
                    existing_entry.image.delete(save=False)
                existing_entry.delete()

            elif existing_entry and not allow_duplicates:
                skipped_entries.append({
                    "filename": file_name,
                    "reason": "Duplicate image filename",
                    "content_hash": content_hash,
                    "version_id": version.id
                })
                return

            elif not allow_duplicates and (content_hash in existing_hashes or content_hash in processed_hashes):
                skipped_entries.append({
                    "filename": file_name,
                    "reason": "Duplicate image content",
                    "content_hash": content_hash,
                    "version_id": version.id
                })
                return

            # Wrap in Django-compatible uploaded file
            django_file = SimpleUploadedFile(file_name, file_content, content_type='image/jpeg')

            image_instance = SKUImages(
                sku=sku,
                version=version,
                tags=tags,
                image=django_file,
                original_filename=file_name,
                content_hash=content_hash
            )
            image_instance.save()
            created_entries.append(SKUImagesSerializer(image_instance).data)
            processed_hashes.add(content_hash)
            existing_hashes.add(content_hash)

        # Process direct image files
        for img in image_files:
            handle_file(img, os.path.basename(img.name))

        # Process zip
        if zip_file:
            with tempfile.TemporaryDirectory() as tmp_dir:
                with zipfile.ZipFile(zip_file, 'r') as zip_ref:
                    zip_ref.extractall(tmp_dir)

                for root, _, files in os.walk(tmp_dir):
                    for file in files:
                        file_path = os.path.join(root, file)
                        with open(file_path, 'rb') as f:
                            file_bytes = f.read()
                            # Convert to Django-compatible upload object
                            django_file = SimpleUploadedFile(file, file_bytes, content_type='image/jpeg')
                            handle_file(django_file, file)

        return Response({
            "message": f"{len(created_entries)} image(s) uploaded, {len(skipped_entries)} skipped.",
            "uploaded": created_entries,
            "skipped": skipped_entries
        }, status=status.HTTP_201_CREATED)


    def destroy(self, request, pk=None):
        """
        DELETE /sku-images/{id}/ → Single delete by ID
        """
        if not pk:
            return Response({"message": "Image ID is required for deletion."},
                            status=status.HTTP_400_BAD_REQUEST)

        try:
            image = SKUImages.objects.get(pk=pk)
        except SKUImages.DoesNotExist:
            return Response({"message": "Image not found."}, status=status.HTTP_404_NOT_FOUND)

        if image.image and image.image.storage.exists(image.image.name):
            image.image.delete(save=False)
        image.delete()

        return Response({"message": f"Image {pk} deleted successfully."}, status=status.HTTP_204_NO_CONTENT)


    @action(detail=False, methods=["post"])
    def delete(self, request):
        """
        POST /sku-images/delete/ → Bulk delete
        Body:
        {
            "image_ids": [1, 2, 3]
        }
        """
        image_ids = request.data.get("image_ids", [])

        if not isinstance(image_ids, list) or not image_ids:
            return Response({"message": "image_ids must be a non-empty list."},
                            status=status.HTTP_400_BAD_REQUEST)

        deleted = []
        not_found = []

        for image_id in image_ids:
            try:
                image = SKUImages.objects.get(id=image_id)
                if image.image and image.image.storage.exists(image.image.name):
                    image.image.delete(save=False)
                image.delete()
                deleted.append(image_id)
            except SKUImages.DoesNotExist:
                not_found.append(image_id)

        return Response({
            "deleted": deleted,
            "not_found": not_found,
            "message": f"{len(deleted)} image(s) deleted, {len(not_found)} not found."
        }, status=status.HTTP_200_OK)
        
    @swagger_auto_schema(
        method='post',
        operation_summary="Merge images from one version to another",
        operation_description="""
        This API merges images from a source version to a target version for a given SKU.
        Options available to overwrite existing images, skip duplicates, and delete the source images.
        """,
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['source_version_id', 'target_version_id', 'sku_id'],
            properties={
                'source_version_id': openapi.Schema(type=openapi.TYPE_INTEGER, description='ID of the source version'),
                'target_version_id': openapi.Schema(type=openapi.TYPE_INTEGER, description='ID of the target version'),
                'sku_id': openapi.Schema(type=openapi.TYPE_INTEGER, description='ID of the SKU'),
                'overwrite': openapi.Schema(type=openapi.TYPE_BOOLEAN, description='Overwrite images in the target version', default=False),
                'skip_duplicates': openapi.Schema(type=openapi.TYPE_BOOLEAN, description='Skip duplicate images (by hash)', default=True),
                'delete_source': openapi.Schema(type=openapi.TYPE_BOOLEAN, description='Delete images from the source version after moving', default=False),
            }
        ),
        responses={
            200: openapi.Response(
                description="Merge result summary",
                examples={
                    "application/json": {
                        "message": "Merged 10 images, skipped 2 duplicates",
                        "merged_count": 10,
                        "skipped_count": 2,
                        "skipped_images": ["image1.jpg", "image2.jpg"],
                        "errors": None
                    }
                }
            ),
            400: 'Bad Request',
            404: 'Not Found'
        }
    )
    @action(detail=False, methods=['post'], url_path='merge-versions')
    def merge_versions(self, request):
        """
        Merge images from one version to another, optionally deleting from source.
        POST /api/sku-images/merge-versions/
        {
            "source_version_id": 1,
            "target_version_id": 2,
            "sku_id": 1,
            "overwrite": false,
            "skip_duplicates": true,
            "delete_source": true
        }
        """
        source_version_id = request.data.get('source_version_id')
        target_version_id = request.data.get('target_version_id')
        sku_id = request.data.get('sku_id')
        overwrite = request.data.get('overwrite', False)
        skip_duplicates = request.data.get('skip_duplicates', True)
        delete_source = request.data.get('delete_source', False)

        # Validate inputs
        if not all([source_version_id, target_version_id, sku_id]):
            return Response(
                {"message": "source_version_id, target_version_id and sku_id are required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            sku = SKU.objects.get(id=sku_id)
            source_version = Versions.objects.get(id=source_version_id, sku=sku)
            target_version = Versions.objects.get(id=target_version_id, sku=sku)
        except (SKU.DoesNotExist, Versions.DoesNotExist) as e:
            return Response({"message": str(e)}, status=status.HTTP_404_NOT_FOUND)

        # Get source images
        source_images = SKUImages.objects.filter(
            sku=sku, version=source_version
        ).select_related('version')

        # Get content hashes from target version
        target_hashes = set(
            SKUImages.objects.filter(sku=sku, version=target_version)
            .exclude(content_hash__isnull=True)
            .values_list('content_hash', flat=True)
        )

        merged_count = 0
        skipped_count = 0
        skipped_images = []  # Track skipped image filenames
        errors = []

        for source_image in source_images:
            try:
                # Skip if already exists in target and skipping is enabled
                if skip_duplicates and source_image.content_hash in target_hashes:
                    skipped_count += 1
                    skipped_images.append(source_image.original_filename)
                    continue

                old_path = source_image.image.path
                new_filename = os.path.basename(old_path)
                new_relative_path = f'sku_images/{sku_id}/{target_version.name}/{new_filename}'
                new_full_path = default_storage.path(new_relative_path)

                os.makedirs(os.path.dirname(new_full_path), exist_ok=True)

                if default_storage.exists(old_path):
                    # Overwrite existing file if necessary
                    if overwrite and default_storage.exists(new_relative_path):
                        default_storage.delete(new_relative_path)

                    with default_storage.open(old_path, 'rb') as old_file:
                        default_storage.save(new_relative_path, old_file)

                    # Remove existing DB record if overwrite is set
                    if overwrite:
                        SKUImages.objects.filter(
                            sku=sku,
                            version=target_version,
                            original_filename=source_image.original_filename
                        ).delete()

                    # Create new record in target version
                    SKUImages.objects.create(
                        sku=sku,
                        tags=source_image.tags,
                        version=target_version,
                        image=new_relative_path,
                        original_filename=source_image.original_filename,
                        content_hash=source_image.content_hash
                    )

                    merged_count += 1

                    # Delete from source if requested
                    if delete_source:
                        if default_storage.exists(old_path):
                            default_storage.delete(old_path)
                        source_image.delete()

                else:
                    errors.append(f"Source file not found: {old_path}")

            except Exception as e:
                errors.append(str(e))
                continue

        return Response({
            "message": f"Merged {merged_count} images, skipped {skipped_count} duplicates",
            "merged_count": merged_count,
            "skipped_count": skipped_count,
            "skipped_images": skipped_images,
            "errors": errors if errors else None
        }, status=status.HTTP_200_OK)
    
    @swagger_auto_schema(
        method='post',
        operation_summary="Merge versions from one SKU to another",
        operation_description="""
        This API merges all versions (and their images) from a source SKU to a destination SKU.
        Optionally handles version name conflicts and deletion of the source versions.
        """,
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['source_sku_id', 'destination_sku_id'],
            properties={
                'source_sku_id': openapi.Schema(type=openapi.TYPE_INTEGER, description='ID of the source SKU'),
                'destination_sku_id': openapi.Schema(type=openapi.TYPE_INTEGER, description='ID of the destination SKU'),
                'delete_source_versions': openapi.Schema(type=openapi.TYPE_BOOLEAN, description='Delete the source versions after merging', default=False),
                'rename_conflicts': openapi.Schema(type=openapi.TYPE_BOOLEAN, description='Automatically rename versions to avoid conflicts', default=True),
            }
        ),
        responses={
            200: openapi.Response(
                description="SKU merge result",
                examples={
                    "application/json": {
                        "message": "Successfully merged 3 versions with 20 images.",
                        "details": [
                            {
                                "source_version_id": 1,
                                "source_version_name": "v1",
                                "new_version_id": 4,
                                "new_version_name": "v1",
                                "images_moved": 10
                            },
                            {
                                "source_version_id": 2,
                                "source_version_name": "v2",
                                "new_version_id": 5,
                                "new_version_name": "v2_1",
                                "images_moved": 10
                            }
                        ],
                        "destination_sku_id": 2,
                        "source_sku_id": 1
                    }
                }
            ),
            400: 'Bad Request',
            404: 'Not Found',
            500: 'Internal Server Error'
        }
    )
    @action(detail=False, methods=['post'], url_path='merge-sku')
    def merge_sku(self, request):
        """
        POST /sku-images/merge-sku/
        Body:
        {
            "source_sku_id": 1,
            "destination_sku_id": 2,
            "delete_source_versions": false,  # optional, default false
            "rename_conflicts": true  # optional, default true
        }
        """
        source_sku_id = request.data.get('source_sku_id')
        destination_sku_id = request.data.get('destination_sku_id')
        delete_source_versions = request.data.get('delete_source_versions', False)
        rename_conflicts = request.data.get('rename_conflicts', True)

        if not source_sku_id or not destination_sku_id:
            return Response(
                {"message": "Both source_sku_id and destination_sku_id are required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            source_sku = SKU.objects.get(id=source_sku_id)
            destination_sku = SKU.objects.get(id=destination_sku_id)
        except SKU.DoesNotExist:
            return Response(
                {"message": "Invalid SKU ID(s) provided."},
                status=status.HTTP_404_NOT_FOUND
            )

        # Get all versions to move from source SKU
        versions_to_merge = Versions.objects.filter(sku=source_sku)

        if not versions_to_merge.exists():
            return Response(
                {"message": "No versions found under source SKU to merge."},
                status=status.HTTP_400_BAD_REQUEST
            )

        existing_version_names = set(
            Versions.objects.filter(sku=destination_sku).values_list('name', flat=True)
        )

        results = []
        moved_images_count = 0

        try:
            with transaction.atomic():
                for version in versions_to_merge:
                    original_name = version.name
                    new_version_name = original_name
                    conflict_suffix = 1

                    # Handle version name conflicts
                    while rename_conflicts and new_version_name in existing_version_names:
                        new_version_name = f"{original_name}_{conflict_suffix}"
                        conflict_suffix += 1

                    # Create new version under destination SKU
                    new_version = Versions.objects.create(
                        name=new_version_name,
                        sku=destination_sku
                    )
                    existing_version_names.add(new_version_name)

                    # Move all images from source version to new version
                    images = SKUImages.objects.filter(version=version)
                    for image in images:
                        if not image.image or not default_storage.exists(image.image.name):
                            continue

                        old_path = image.image.name
                        new_path = f'sku_images/{destination_sku.id}/{new_version.name}/{image.original_filename}'

                        # Ensure directory exists
                        dir_path = os.path.dirname(new_path)
                        if not default_storage.exists(dir_path):
                            os.makedirs(default_storage.path(dir_path), exist_ok=True)

                        # Move file
                        with default_storage.open(old_path, 'rb') as f:
                            default_storage.save(new_path, f)
                        if default_storage.exists(old_path):
                            default_storage.delete(old_path)

                        # Update image record
                        image.version = new_version
                        image.sku = destination_sku
                        image.image.name = new_path
                        image.save()
                        moved_images_count += 1

                    results.append({
                        'source_version_id': version.id,
                        'source_version_name': original_name,
                        'new_version_id': new_version.id,
                        'new_version_name': new_version.name,
                        'images_moved': images.count()
                    })

                    if delete_source_versions:
                        version.delete()

            return Response({
                'message': f'Successfully merged {len(results)} versions with {moved_images_count} images.',
                'details': results,
                'destination_sku_id': destination_sku_id,
                'source_sku_id': source_sku_id
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response(
                {"message": f"Error during merge: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )




# class SKUListImages(viewsets.ViewSet):

#     @swagger_auto_schema(
#         manual_parameters=[
#             openapi.Parameter(
#                 'sku_id', openapi.IN_QUERY,
#                 description="Filter by SKU ID", type=openapi.TYPE_INTEGER
#             ),
#             openapi.Parameter(
#                 'version_id', openapi.IN_QUERY,
#                 description="Filter by version ID", type=openapi.TYPE_INTEGER
#             ),
#             openapi.Parameter(
#                 'tags', openapi.IN_QUERY,
#                 description="Filter by tag (partial match)", type=openapi.TYPE_STRING
#             ),
#         ],
#         responses={200: SKUImagesSerializer(many=True)},
#         operation_summary="List SKU Images",
#         operation_description="Retrieve SKU images filtered by SKU ID, version ID, and tags."
#     )
#     def list(self, request):
#         queryset = SKUImages.objects.all()
#         sku_id = request.query_params.get('sku_id')
#         version_id = request.query_params.get('version_id')
#         tags = request.query_params.get('tags')

#         if sku_id:
#             queryset = queryset.filter(sku__id=sku_id)
#         if version_id:
#             queryset = queryset.filter(version__id=version_id)
#         if tags:
#             queryset = queryset.filter(tags__icontains=tags)

#         serializer = SKUImagesSerializer(queryset, many=True)
#         return Response({"results": serializer.data}, status=status.HTTP_200_OK)

class SKUListImages(viewsets.ViewSet):

    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter(
                'sku_id', openapi.IN_QUERY,
                description="Filter by SKU ID", type=openapi.TYPE_INTEGER
            ),
            openapi.Parameter(
                'version_id', openapi.IN_QUERY,
                description="Filter by Version ID", type=openapi.TYPE_INTEGER
            ),
            openapi.Parameter(
                'tags', openapi.IN_QUERY,
                description="Filter by Tag (partial match)", type=openapi.TYPE_STRING
            ),
            openapi.Parameter(
                'label_id', openapi.IN_QUERY,
                description="Filter by Label ID", type=openapi.TYPE_INTEGER
            ),
            openapi.Parameter(
                'rejected', openapi.IN_QUERY,
                description="Filter by Rejected Status (true or false)", type=openapi.TYPE_BOOLEAN
            ),
            openapi.Parameter(
                'data_set', openapi.IN_QUERY,
                description="Filter by Dataset Flag (true or false)", type=openapi.TYPE_BOOLEAN
            ),
        ],
        responses={200: SKUImagesSerializer(many=True)},
        operation_summary="List SKU Images",
        operation_description="Retrieve SKU images filtered by SKU ID, version ID, tags, label ID, rejected flag, and dataset flag."
    )
    def list(self, request):
        queryset = SKUImages.objects.all()
        sku_id = request.query_params.get('sku_id')
        version_id = request.query_params.get('version_id')
        tags = request.query_params.get('tags')
        label_id = request.query_params.get('label_id')
        rejected = request.query_params.get('rejected')
        data_set = request.query_params.get('data_set')

        if sku_id:
            queryset = queryset.filter(sku__id=sku_id)
        if version_id:
            queryset = queryset.filter(version__id=version_id)
        if tags:
            queryset = queryset.filter(tags__icontains=tags)
        if label_id:
            queryset = queryset.filter(label__id=label_id)
        if rejected is not None:
            if rejected.lower() in ['true', '1']:
                queryset = queryset.filter(rejected=True)
            elif rejected.lower() in ['false', '0']:
                queryset = queryset.filter(rejected=False)
        if data_set is not None:
            if data_set.lower() in ['true', '1']:
                queryset = queryset.filter(data_set=True)
            elif data_set.lower() in ['false', '0']:
                queryset = queryset.filter(data_set=False)

        serializer = SKUImagesSerializer(queryset, many=True)
        return Response({"results": serializer.data}, status=status.HTTP_200_OK)

    
class TagsViewSet(viewsets.ViewSet):
    
    @swagger_auto_schema(
        operation_summary="List all tags",
        responses={200: openapi.Response(description="List of tags")}
    )
    def list(self, request):
        tags = Tags.objects.all().values()
        return Response({"results": list(tags)}, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        operation_summary="Retrieve a tag by ID",
        responses={
            200: openapi.Response(description="Tag details"),
            404: openapi.Response(description="Tag not found")
        }
    )
    def retrieve(self, request, pk=None):
        try:
            tag = Tags.objects.filter(pk=pk).values().first()
            if not tag:
                raise Tags.DoesNotExist
            return Response(tag)
        except Tags.DoesNotExist:
            return Response({"message": "Tag not found"}, status=status.HTTP_404_NOT_FOUND)

    @swagger_auto_schema(
        operation_summary="Create a new tag",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['name'],
            properties={
                'name': openapi.Schema(type=openapi.TYPE_STRING, description='Tag name'),
                'is_active': openapi.Schema(type=openapi.TYPE_BOOLEAN, description='Is tag active?')
            }
        ),
        responses={201: openapi.Response(description="Tag created")}
    )
    def create(self, request):
        name = request.data.get("name")
        is_active = request.data.get("is_active", True)

        if not name:
            return Response({"message": "Name is required"}, status=status.HTTP_400_BAD_REQUEST)

        tag = Tags.objects.create(name=name, is_active=is_active)
        return Response({"id": tag.id, "name": tag.name, "is_active": tag.is_active}, status=status.HTTP_201_CREATED)

    @swagger_auto_schema(
        operation_summary="Update a tag",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'name': openapi.Schema(type=openapi.TYPE_STRING, description='Tag name'),
                'is_active': openapi.Schema(type=openapi.TYPE_BOOLEAN, description='Is tag active?')
            }
        ),
        responses={
            200: openapi.Response(description="Tag updated"),
            404: openapi.Response(description="Tag not found")
        }
    )
    def update(self, request, pk=None):
        try:
            tag = Tags.objects.get(pk=pk)
        except Tags.DoesNotExist:
            return Response({"message": "Tag not found"}, status=status.HTTP_404_NOT_FOUND)

        tag.name = request.data.get("name", tag.name)
        tag.is_active = request.data.get("is_active", tag.is_active)
        tag.save()

        return Response({"id": tag.id, "name": tag.name, "is_active": tag.is_active})

    @swagger_auto_schema(
        operation_summary="Delete a tag",
        responses={
            204: openapi.Response(description="Tag deleted"),
            404: openapi.Response(description="Tag not found")
        }
    )
    def destroy(self, request, pk=None):
        try:
            tag = Tags.objects.get(pk=pk)
        except Tags.DoesNotExist:
            return Response({"message": "Tag not found"}, status=status.HTTP_404_NOT_FOUND)

        tag.delete()
        return Response({"message": "Tag deleted"}, status=status.HTTP_204_NO_CONTENT)
    

class VersionsViewSet(viewsets.ViewSet):

    @swagger_auto_schema(
        operation_summary="List all versions (optional filter by SKU ID)",
        manual_parameters=[
            openapi.Parameter(
                'sku',
                openapi.IN_QUERY,
                description="Filter by SKU ID",
                type=openapi.TYPE_INTEGER
            )
        ],
        responses={200: 'Returns a list of version objects with image annotation stats'}
    )
    def list(self, request):
        sku_id = request.query_params.get("sku")

        if sku_id:
            versions = Versions.objects.filter(sku_id=sku_id)
        else:
            versions = Versions.objects.all()

        versions = versions.annotate(
            total_image_count=Count('skuimages'),
            labeled_image_count=Count('skuimages', filter=Q(skuimages__label__isnull=False)),
            unlabeled_image_count=Count('skuimages', filter=Q(skuimages__label__isnull=True))
        )

        version_data = [
            {
                "id": version.id,
                "name": version.name,
                "sku_id": version.sku_id,
                "total_image_count": version.total_image_count,
                "labeled_image_count": version.labeled_image_count,
                "unlabeled_image_count": version.unlabeled_image_count,
            }
            for version in versions
        ]

        return Response({"results": version_data}, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        operation_summary="Create a new version",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["name", "sku"],
            properties={
                'name': openapi.Schema(type=openapi.TYPE_STRING),
                'sku': openapi.Schema(type=openapi.TYPE_INTEGER)
            }
        ),
        responses={201: 'Version created successfully', 400: 'Bad request'}
    )
    def create(self, request):
        name = request.data.get("name")
        sku_id = request.data.get("sku")

        if not name or not sku_id:
            return Response({"message": "Both 'name' and 'sku' are required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            sku = SKU.objects.get(id=sku_id)
        except SKU.DoesNotExist:
            return Response({"message": "Invalid SKU ID."}, status=status.HTTP_404_NOT_FOUND)

        # Check for duplicate version name under same SKU
        if Versions.objects.filter(name__iexact=name, sku=sku).exists():
            return Response(
                {"message": f"Version with name '{name}' already exists for this SKU."},
                status=status.HTTP_400_BAD_REQUEST
            )

        version = Versions.objects.create(name=name, sku=sku)
        return Response({"id": version.id, "name": version.name, "sku": version.sku.id}, status=status.HTTP_201_CREATED)

    @swagger_auto_schema(
        operation_summary="Retrieve a version by ID",
        responses={200: 'Returns a version object', 404: 'Not found'}
    )
    def retrieve(self, request, pk=None):
        try:
            version = Versions.objects.get(id=pk)
        except Versions.DoesNotExist:
            return Response({"message": "Version not found."}, status=status.HTTP_404_NOT_FOUND)

        return Response({"id": version.id, "name": version.name, "sku": version.sku.id}, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        operation_summary="Update a version by ID",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'name': openapi.Schema(type=openapi.TYPE_STRING),
                'sku': openapi.Schema(type=openapi.TYPE_INTEGER)
            }
        ),
        responses={200: 'Version updated successfully'}
    )
    def update(self, request, pk=None):
        try:
            version = Versions.objects.get(id=pk)
        except Versions.DoesNotExist:
            return Response({"message": "Version not found."}, status=status.HTTP_404_NOT_FOUND)

        name = request.data.get("name", version.name)
        sku_id = request.data.get("sku", version.sku.id if version.sku else None)

        if sku_id:
            try:
                sku = SKU.objects.get(id=sku_id)
            except SKU.DoesNotExist:
                return Response({"message": "Invalid SKU ID."}, status=status.HTTP_404_NOT_FOUND)
        else:
            sku = version.sku

        # Prevent duplicate name under same SKU
        if Versions.objects.filter(name__iexact=name, sku=sku).exclude(id=pk).exists():
            return Response(
                {"message": f"Another version with name '{name}' already exists for this SKU."},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        version.name = name
        version.sku = sku
        version.save()

        return Response({"id": version.id, "name": version.name, "sku": version.sku.id}, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        operation_summary="Delete a version by ID",
        responses={204: 'Deleted successfully', 404: 'Not found'}
    )
    def destroy(self, request, pk=None):
        try:
            version = Versions.objects.get(id=pk)
        except Versions.DoesNotExist:
            return Response({"message": "Version not found."}, status=status.HTTP_404_NOT_FOUND)

        version.delete()
        return Response({"message": f"Version {pk} deleted successfully."}, status=status.HTTP_204_NO_CONTENT)


# class LabelsViewSet(viewsets.ViewSet):

#     @swagger_auto_schema(
#         operation_summary="List all labels",
#         manual_parameters=[
#             openapi.Parameter(
#                 'is_active',
#                 openapi.IN_QUERY,
#                 description="Filter by is_active (true or false)",
#                 type=openapi.TYPE_BOOLEAN
#             ),
#             openapi.Parameter(
#                 'sku',
#                 openapi.IN_QUERY,
#                 description="Filter by SKU ID",
#                 type=openapi.TYPE_INTEGER
#             ),
#         ],
#         responses={200: openapi.Response("List of labels")}
#     )
#     def list(self, request):
#         is_active = request.query_params.get('is_active', None)
#         sku = request.query_params.get('sku', None)

#         labels = Labels.objects.all().order_by('-id')

#         if is_active is not None:
#             if is_active.lower() in ['true', '1']:
#                 labels = labels.filter(is_active=True)
#             elif is_active.lower() in ['false', '0']:
#                 labels = labels.filter(is_active=False)

#         if sku is not None:
#             labels = labels.filter(sku__id=sku)

#         data = [{
#             "id": label.id,
#             "name": label.name,
#             "sku_id": label.sku.id if label.sku else None,
#             'color_code': label.color_code,
#             "shortcut_key": label.shortcut_key,
#             "is_active": label.is_active
#         } for label in labels]

#         return Response({"status": status.HTTP_200_OK, "result": data})


class LabelsViewSet(viewsets.ViewSet):

    @swagger_auto_schema(
        operation_summary="List all labels",
        manual_parameters=[
            openapi.Parameter(
                'is_active',
                openapi.IN_QUERY,
                description="Filter by is_active (true or false)",
                type=openapi.TYPE_BOOLEAN
            ),
            openapi.Parameter(
                'sku',
                openapi.IN_QUERY,
                description="Filter by SKU ID",
                type=openapi.TYPE_INTEGER
            ),
            openapi.Parameter(
                'label',
                openapi.IN_QUERY,
                description="Filter labels where label is null (use label=null)",
                type=openapi.TYPE_STRING
            ),
        ],
        responses={200: openapi.Response("List of labels")}
    )
    def list(self, request):
        is_active = request.query_params.get('is_active', None)
        sku = request.query_params.get('sku', None)
        label_param = request.query_params.get('label', None)

        labels = Labels.objects.all().order_by('-id')

        if is_active is not None:
            if is_active.lower() in ['true', '1']:
                labels = labels.filter(is_active=True)
            elif is_active.lower() in ['false', '0']:
                labels = labels.filter(is_active=False)

        if sku is not None:
            labels = labels.filter(sku__id=sku)

        # Handle `label=null` logic — assuming label refers to Labels with no SKU
        if label_param == 'null':
            labels = labels.filter(sku__isnull=True)

        data = [{
            "id": label.id,
            "name": label.name,
            "sku_id": label.sku.id if label.sku else None,
            'color_code': label.color_code,
            "shortcut_key": label.shortcut_key,
            "is_active": label.is_active
        } for label in labels]

        return Response({"status": status.HTTP_200_OK, "result": data})


    @swagger_auto_schema(
        operation_summary="Create a new label",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["name", "sku_id", "shortcut_key"],
            properties={
                'name': openapi.Schema(type=openapi.TYPE_STRING),
                'sku_id': openapi.Schema(type=openapi.TYPE_INTEGER),
                'shortcut_key': openapi.Schema(type=openapi.TYPE_STRING),
                'color_code': openapi.Schema(type=openapi.TYPE_STRING),
                'is_active': openapi.Schema(type=openapi.TYPE_BOOLEAN)
            },
        ),
        responses={201: "Label created", 400: "Bad request"}
    )
    def create(self, request):
        name = request.data.get("name", "").strip()
        sku_id = request.data.get("sku_id")
        color_code = request.data.get("color_code", "").strip()
        shortcut_key = request.data.get("shortcut_key", "").strip()
        is_active = request.data.get("is_active", True)

        if not name or not sku_id or not shortcut_key:
            return Response({
                "message": "Fields 'name', 'sku_id' and 'shortcut_key' are required.",
                "status": status.HTTP_400_BAD_REQUEST
            }, status=status.HTTP_400_BAD_REQUEST)

        # Label name uniqueness (case-insensitive) per SKU
        if Labels.objects.filter(sku_id=sku_id, name__iexact=name).exists():
            return Response({
                "message": "Label with this name already exists for this SKU.",
                "status": status.HTTP_400_BAD_REQUEST
            }, status=status.HTTP_400_BAD_REQUEST)

        # Shortcut key uniqueness (case-insensitive) per SKU
        if Labels.objects.filter(sku_id=sku_id, shortcut_key__iexact=shortcut_key).exists():
            return Response({
                "message": "Shortcut key already exists for this SKU.",
                "status": status.HTTP_400_BAD_REQUEST
            }, status=status.HTTP_400_BAD_REQUEST)

        # Color code uniqueness (case-insensitive) per SKU
        if color_code and Labels.objects.filter(sku_id=sku_id, color_code__iexact=color_code).exists():
            return Response({
                "message": "Color code already exists for this SKU.",
                "status": status.HTTP_400_BAD_REQUEST
            }, status=status.HTTP_400_BAD_REQUEST)

        Labels.objects.create(
            name=name,
            sku_id=sku_id,
            shortcut_key=shortcut_key,
            color_code=color_code,
            is_active=is_active
        )

        return Response({
            "message": "Label Created Successfully",
            "status": status.HTTP_201_CREATED,
        }, status=status.HTTP_201_CREATED)



    @swagger_auto_schema(
        operation_summary="Update an existing label",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'name': openapi.Schema(type=openapi.TYPE_STRING),
                'shortcut_key': openapi.Schema(type=openapi.TYPE_STRING),
                'color_code': openapi.Schema(type=openapi.TYPE_STRING),
                'is_active': openapi.Schema(type=openapi.TYPE_BOOLEAN),
            },
        ),
        responses={200: "Label updated", 400: "Bad request", 404: "Not found"}
    )
    def update(self, request, pk=None):
        try:
            label = Labels.objects.get(pk=pk)
        except Labels.DoesNotExist:
            return Response({
                "message": "Label not found.",
                "status": status.HTTP_404_NOT_FOUND
            }, status=status.HTTP_404_NOT_FOUND)

        name = request.data.get("name", label.name).strip()
        shortcut_key = request.data.get("shortcut_key", label.shortcut_key).strip()
        color_code = request.data.get("color_code", label.color_code).strip()
        is_active = request.data.get("is_active", label.is_active)

        # Uniqueness check for name per SKU
        if Labels.objects.filter(sku=label.sku, name__iexact=name).exclude(pk=label.id).exists():
            return Response({
                "message": "Another label with this name already exists for this SKU.",
                "status": status.HTTP_400_BAD_REQUEST
            }, status=status.HTTP_400_BAD_REQUEST)

        # Uniqueness check for shortcut_key per SKU
        if Labels.objects.filter(sku=label.sku, shortcut_key__iexact=shortcut_key).exclude(pk=label.id).exists():
            return Response({
                "message": "Another label with this shortcut key already exists for this SKU.",
                "status": status.HTTP_400_BAD_REQUEST
            }, status=status.HTTP_400_BAD_REQUEST)

        # Uniqueness check for color_code per SKU
        if color_code and Labels.objects.filter(sku=label.sku, color_code__iexact=color_code).exclude(pk=label.id).exists():
            return Response({
                "message": "Another label with this color code already exists for this SKU.",
                "status": status.HTTP_400_BAD_REQUEST
            }, status=status.HTTP_400_BAD_REQUEST)

        label.name = name
        label.shortcut_key = shortcut_key
        label.color_code = color_code
        label.is_active = is_active
        label.save()

        return Response({
            "message": "Label updated successfully",
            "status": status.HTTP_200_OK
        })


class AnnotationViewSet(viewsets.ViewSet):
    
    @swagger_auto_schema(
        operation_summary="Create annotation (assign label and optional rejection)",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["image_id", "label_id"],
            properties={
                'image_id': openapi.Schema(type=openapi.TYPE_INTEGER, description="ID of the SKUImage"),
                'label_id': openapi.Schema(type=openapi.TYPE_INTEGER, description="ID of the Label to assign"),
                'rejected': openapi.Schema(type=openapi.TYPE_BOOLEAN, description="Mark image as rejected or not", nullable=True),
            },
        ),
        responses={
            201: openapi.Response(description="Label assigned successfully"),
            400: "Bad request",
            404: "Image or Label not found"
        }
    )
    def create(self, request):
        image_id = request.data.get("image_id")
        label_id = request.data.get("label_id", None)  # Optional
        rejected = request.data.get("rejected", None)  # Optional (can be True/False/null)

        if not image_id:
            return Response(
                {"message": "image_id is required.", "status": status.HTTP_400_BAD_REQUEST},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            image = SKUImages.objects.get(pk=image_id)
        except SKUImages.DoesNotExist:
            return Response(
                {"message": "Image not found.", "status": status.HTTP_404_NOT_FOUND},
                status=status.HTTP_404_NOT_FOUND
            )

        if label_id:
            try:
                label = Labels.objects.get(pk=label_id)
                image.label = label
            except Labels.DoesNotExist:
                return Response(
                    {"message": "Label not found.", "status": status.HTTP_404_NOT_FOUND},
                    status=status.HTTP_404_NOT_FOUND
                )

        if rejected is not None:
            image.rejected = bool(rejected)

        image.save()

        return Response({
            "message": "Image updated successfully.",
            "status": status.HTTP_201_CREATED
        }, status=status.HTTP_201_CREATED)

    # def create(self, request):
    #     image_id = request.data.get("image_id")
    #     label_id = request.data.get("label_id")
    #     rejected = request.data.get("rejected", False)  # Default to False if not provided

    #     if not image_id:
    #         return Response(
    #             {"message": "Image_id' is required.", "status": status.HTTP_400_BAD_REQUEST},
    #             status=status.HTTP_400_BAD_REQUEST
    #         )

    #     try:
    #         image = SKUImages.objects.get(pk=image_id)
    #     except SKUImages.DoesNotExist:
    #         return Response({"message": "Image not found.", "status": status.HTTP_404_NOT_FOUND}, status=status.HTTP_404_NOT_FOUND)

    #     try:
    #         label = Labels.objects.get(pk=label_id)
    #     except Labels.DoesNotExist:
    #         return Response({"message": "Label not found.", "status": status.HTTP_404_NOT_FOUND}, status=status.HTTP_404_NOT_FOUND)
        
    #     image.label = label
    #     image.rejected = bool(rejected)
    #     image.save()

    #     return Response({
    #         "message": "Label assigned successfully to image.",
    #         "status": status.HTTP_201_CREATED
    #     }, status=status.HTTP_201_CREATED)

    @swagger_auto_schema(
        operation_summary="Update annotation (update label and/or rejection status for an image)",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=[],
            properties={
                'label_id': openapi.Schema(type=openapi.TYPE_INTEGER, description="New label ID to update", nullable=True),
                'rejected': openapi.Schema(type=openapi.TYPE_BOOLEAN, description="Mark image as rejected or not", nullable=True),
            },
        ),
        responses={
            200: openapi.Response(description="Annotation updated successfully"),
            400: "Bad request",
            404: "Image or Label not found"
        }
    )
    def update(self, request, pk=None):
        label_id = request.data.get("label_id")
        rejected = request.data.get("rejected")  # True / False

        try:
            image = SKUImages.objects.get(pk=pk)
        except SKUImages.DoesNotExist:
            return Response({"message": "Image not found.", "status": status.HTTP_404_NOT_FOUND}, status=status.HTTP_404_NOT_FOUND)

        if label_id:
            try:
                label = Labels.objects.get(pk=label_id)
            except Labels.DoesNotExist:
                return Response({"message": "Label not found.", "status": status.HTTP_404_NOT_FOUND}, status=status.HTTP_404_NOT_FOUND)

            if label.sku != image.sku:
                return Response({"message": "Label SKU does not match image SKU.", "status": status.HTTP_400_BAD_REQUEST}, status=status.HTTP_400_BAD_REQUEST)

            image.label = label

        if rejected is not None:
            image.rejected = bool(rejected)

        image.save()

        return Response({
            "message": "Annotation updated successfully.",
            "status": status.HTTP_200_OK
        }, status=status.HTTP_200_OK)

    

class CameraImageCaptureViewset(viewsets.ViewSet):

    @swagger_auto_schema(
        operation_summary="Upload base64 image to SKUImages",
        operation_description="Takes a base64 encoded image and saves it to the SKUImages model with associated SKU and Version.",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["sku_id", "version_id", "image"],
            properties={
                'sku_id': openapi.Schema(type=openapi.TYPE_INTEGER, description="ID of the SKU"),
                'version_id': openapi.Schema(type=openapi.TYPE_INTEGER, description="ID of the Version"),
                'tags': openapi.Schema(type=openapi.TYPE_STRING, description="Optional image tags"),
                'image': openapi.Schema(type=openapi.TYPE_STRING, description="Base64 encoded image (with MIME prefix)")
            }
        ),
        responses={
            201: openapi.Response(description="Image uploaded successfully", schema=SKUImagesSerializer),
            400: "Bad request",
            404: "SKU or Version not found"
        }
    )
    def create(self, request):
        sku_id = request.data.get('sku_id')
        version_id = request.data.get('version_id')
        tags = request.data.get('tags', '')
        base64_image = request.data.get('image')

        if not all([sku_id, version_id, base64_image]):
            return Response({"message": "sku_id, version_id, and image are required."},
                            status=status.HTTP_400_BAD_REQUEST)

        try:
            sku = SKU.objects.get(id=sku_id)
        except SKU.DoesNotExist:
            return Response({"message": "Invalid sku_id."}, status=status.HTTP_404_NOT_FOUND)

        try:
            version = Versions.objects.get(id=version_id)
        except Versions.DoesNotExist:
            return Response({"message": "Invalid version_id."}, status=status.HTTP_404_NOT_FOUND)

        try:
            format, imgstr = base64_image.split(';base64,')
            ext = format.split('/')[-1]
            decoded_image = base64.b64decode(imgstr)
        except Exception:
            return Response({"message": "Invalid base64 image format."}, status=status.HTTP_400_BAD_REQUEST)

        content_hash = hashlib.md5(decoded_image).hexdigest()
        random_name = secrets.token_hex(4)[:7]
        filename = f"{random_name}.{ext}"
        image_file = ContentFile(decoded_image, name=filename)

        image_obj = SKUImages.objects.create(
            sku=sku,
            version=version,
            tags=tags,
            image=image_file,
            original_filename=filename,
            content_hash=content_hash
        )

        return Response({
            "message": "Image uploaded successfully.",
            "status": status.HTTP_201_CREATED,
        }, status=status.HTTP_201_CREATED)
        
        
class DataSetViewset(viewsets.ViewSet):

    @swagger_auto_schema(
        operation_summary="Get labeled image paths by SKU and Version",
        operation_description="Returns image URLs with label_id (0 for Good, 1 for Bad) filtered by SKU and Version IDs. Only includes images with labels assigned.",
        manual_parameters=[
            openapi.Parameter('sku_id', openapi.IN_QUERY, type=openapi.TYPE_INTEGER, required=True, description="ID of the SKU"),
            openapi.Parameter('version_id', openapi.IN_QUERY, type=openapi.TYPE_STRING, required=True, description="Comma-separated Version IDs (e.g., 1,2,3 or just 3)"),
            openapi.Parameter('absolute_path', openapi.IN_QUERY, type=openapi.TYPE_BOOLEAN, required=False, description="Whether to return absolute paths"),
        ],
        responses={
            200: openapi.Response(description="Filtered image list", schema=openapi.Schema(
                type=openapi.TYPE_ARRAY,
                items=openapi.Items(type=openapi.TYPE_OBJECT, properties={
                    "image": openapi.Schema(type=openapi.TYPE_STRING, description="Image URL"),
                    "label_id": openapi.Schema(type=openapi.TYPE_INTEGER, description="0 for Good, 1 for Bad"),
                })
            )),
            400: "Missing parameters",
        }
    )
    def list(self, request):
        sku_id = request.query_params.get('sku_id')
        version_ids = request.query_params.get('version_id')
        absolute_path = request.query_params.get('absolute_path', 'false').lower() == 'true'

        if not sku_id or not version_ids:
            return Response({"message": "sku_id and version_ids are required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Clean input: remove empty strings, strip whitespace, and convert to int
            version_id_list = [int(v.strip()) for v in version_ids.split(',') if v.strip().isdigit()]
            if not version_id_list:
                raise ValueError
        except ValueError:
            return Response({"message": "Invalid version_ids format. Must be comma-separated integers."}, status=status.HTTP_400_BAD_REQUEST)

        queryset = SKUImages.objects.filter(
            sku_id=sku_id,
            version_id__in=version_id_list,
            label__isnull=False
        )

        serializer = SKUImageLabelSerializer(
            queryset,
            many=True,
            context={'request': request, 'absolute_path': absolute_path}
        )
        return Response(serializer.data, status=status.HTTP_200_OK)


    
class DatasetSplitViewSet(viewsets.ViewSet):

    @swagger_auto_schema(
        operation_summary="Split Annotated Images into Train/Val/Test",
        operation_description="Randomly assigns annotated images into training, validation, and test sets based on percentages provided.",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["sku_id", "version_id", "train_split", "val_split", "test_split"],
            properties={
                "sku_id": openapi.Schema(type=openapi.TYPE_INTEGER, description="SKU ID"),
                "version_id": openapi.Schema(type=openapi.TYPE_INTEGER, description="Version ID"),
                "train_split": openapi.Schema(type=openapi.TYPE_INTEGER, description="Train split percentage (e.g. 70)"),
                "val_split": openapi.Schema(type=openapi.TYPE_INTEGER, description="Validation split percentage (e.g. 15)"),
                "test_split": openapi.Schema(type=openapi.TYPE_INTEGER, description="Test split percentage (e.g. 15)"),
            }
        ),
        responses={
            200: openapi.Response(description="Dataset split successfully."),
            400: openapi.Response(description="Invalid input or split error."),
            404: openapi.Response(description="No annotated images found.")
        }
    )
    # def create(self, request):
    #     sku_id = request.data.get("sku_id")
    #     version_id = request.data.get("version_id")
    #     train_split = int(request.data.get("train_split", 70))
    #     val_split = int(request.data.get("val_split", 15))
    #     test_split = int(request.data.get("test_split", 15))

    #     if train_split + val_split + test_split != 100:
    #         return Response({"error": "Splits must total 100%"}, status=status.HTTP_400_BAD_REQUEST)

    #     images = list(SKUImages.objects.filter(sku_id=sku_id, version_id=version_id, label__isnull=False))
    #     total = len(images)
    #     if total == 0:
    #         return Response({"error": "No annotated images found."}, status=status.HTTP_404_NOT_FOUND)

    #     random.shuffle(images)

    #     train_end = int(total * train_split / 100)
    #     val_end = train_end + int(total * val_split / 100)

    #     for i, image in enumerate(images):
    #         if i < train_end:
    #             image.split_label = "train"
    #         elif i < val_end:
    #             image.split_label = "val"
    #         else:
    #             image.split_label = "test"
    #         image.save()

    #     return Response({
    #         "message": "Dataset split successfully.",
    #         "total": total,
    #         "train": train_end,
    #         "val": val_end - train_end,
    #         "test": total - val_end
    #     }, status=status.HTTP_200_OK)
    def create(self, request):
        sku_id = request.data.get("sku_id")
        version_id = request.data.get("version_id")
        train_split = int(request.data.get("train_split", 70))
        val_split = int(request.data.get("val_split", 15))
        test_split = int(request.data.get("test_split", 15))

        if train_split + val_split + test_split != 100:
            return Response({"error": "Splits must total 100%"}, status=status.HTTP_400_BAD_REQUEST)

        images = list(SKUImages.objects.filter(sku_id=sku_id, version_id=version_id, label__isnull=False))
        total = len(images)
        if total == 0:
            return Response({"error": "No annotated images found."}, status=status.HTTP_404_NOT_FOUND)

        random.shuffle(images)

        train_end = int(total * train_split / 100)
        val_end = train_end + int(total * val_split / 100)

        for i, image in enumerate(images):
            if i < train_end:
                image.split_label = "train"
            elif i < val_end:
                image.split_label = "val"
            else:
                image.split_label = "test"

            # ✅ Mark as part of dataset
            image.data_set = True  
            image.save()

        return Response({
            "message": "Dataset split successfully.",
            "total": total,
            "train": train_end,
            "val": val_end - train_end,
            "test": total - val_end
        }, status=status.HTTP_200_OK)

        
        
import os
import subprocess
import sys
import signal
from django.conf import settings
from rest_framework import viewsets, status
from rest_framework.response import Response
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi


class ScriptRunnerViewSet(viewsets.ViewSet):
    BASE_DIR = settings.BASE_DIR
    PID_DIR = os.path.join(BASE_DIR, "pids")
    PID_FILE = os.path.join(PID_DIR, "main_script.pid")
    SCRIPT_PATH = os.path.join(BASE_DIR,"ml_shell_scripts", "data_collection", "dummy.py")  # Updated script path

    @swagger_auto_schema(
        operation_summary="Run main.py with arguments (background)",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=[
                "sku_id", "version_id", "tag_name", "end_point_url", "camera_config_file"
            ],
            properties={
                "sku_id": openapi.Schema(type=openapi.TYPE_STRING),
                "version_id": openapi.Schema(type=openapi.TYPE_STRING),
                "tag_name": openapi.Schema(type=openapi.TYPE_STRING),
                "end_point_url": openapi.Schema(type=openapi.TYPE_STRING),
                "camera_config_file": openapi.Schema(type=openapi.TYPE_STRING),
            }
        ),
        responses={200: "Script started successfully"}
    )
    def create(self, request):
        required_keys = [
            "sku_id", "version_id", "tag_name", "end_point_url", "camera_config_file"
        ]

        if not all(key in request.data for key in required_keys):
            return Response(
                {"message": f"Missing required fields. Required: {required_keys}"},
                status=status.HTTP_400_BAD_REQUEST
            )

        ### this is for streaming endpoint urls #####
        end_point_url = request.data.get("end_point_url", "http://localhost:8000/api/capture-images/")
        streaming_endpoint_url = request.data.get("streaming_endpoint_url", "http://localhost:8000/api/stream-image/")
        try:
            os.makedirs(self.PID_DIR, exist_ok=True)

            # Prepare subprocess arguments
            args = [
                sys.executable,
                self.SCRIPT_PATH,
                "--sku_id", request.data["sku_id"],
                "--version_id", request.data["version_id"],
                "--tag_name", request.data["tag_name"],
                "--end_point_url", end_point_url,
                "--camera_config_file", request.data["camera_config_file"],
                "--streaming_endpoint_url", streaming_endpoint_url
            ]

            # Include PYTHONPATH so relative imports work
            # env = os.environ.copy()
            # env["PYTHONPATH"] = settings.BASE_DIR  # ensures data_collection is importable
            env = os.environ.copy()
            env["PYTHONPATH"] = str(settings.BASE_DIR)

            creationflags = subprocess.CREATE_NEW_PROCESS_GROUP if os.name == 'nt' else 0

            process = subprocess.Popen(
                args,
                start_new_session=(os.name != 'nt'),
                creationflags=creationflags,
                env=env
            )

            with open(self.PID_FILE, "w") as f:
                f.write(str(process.pid))

            return Response({
                "message": f"main.py started with PID {process.pid}",
                "process.pid":process.pid,
                "status": status.HTTP_200_OK
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response(
                {"message": f"Error: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @swagger_auto_schema(
        operation_summary="Terminate background main.py process",
        responses={200: "Terminated", 404: "Not found", 500: "Error"}
    )
    def destroy(self, request, pk=None):
        if not os.path.exists(self.PID_FILE):
            return Response({"message": "PID file not found."}, status=status.HTTP_404_NOT_FOUND)

        try:
            with open(self.PID_FILE, "r") as f:
                pid = int(f.read().strip())

            if os.name == 'nt':
                os.kill(pid, signal.SIGTERM)
            else:
                os.killpg(pid, signal.SIGTERM)

            os.remove(self.PID_FILE)

            return Response({"message": f"✅ Process with PID {pid} terminated."}, status=status.HTTP_200_OK)

        except ProcessLookupError:
            os.remove(self.PID_FILE)
            return Response({"message": "⚠️ Process not found (already exited?)."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"message": f"❌ Error terminating process: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        

class FinalDataSet(viewsets.ViewSet):
    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter(
                'sku_id',
                openapi.IN_QUERY,
                description="SKU ID to filter dataset images",
                type=openapi.TYPE_INTEGER,
                required=True
            )
        ],
        operation_summary="Get Dataset Images Grouped by Version with Count and Metadata",
        operation_description="Fetch all images (with label and in dataset) for a given SKU ID, group them by version name, and return the image metadata and count per version.",
        responses={
            200: openapi.Response(
                description="Grouped image metadata and count by version name",
                examples={
                    "application/json": {
                        "Version A": {
                            "count": 2,
                            "version_id": 12,
                            "images": [
                                {
                                    "image_url": "http://localhost:8000/media/uploads/image1.jpg",
                                    "label_id": 1,
                                    "label_name": "Crack",
                                    "split_label": "train",
                                    "data_set": True
                                }
                            ]
                        }
                    }
                }
            ),
            400: "Missing sku_id or invalid input",
            404: "No images found for given sku_id"
        }
    )
    def list(self, request):
        sku_id = request.query_params.get("sku_id")
        if not sku_id:
            return Response({"message": "sku_id is required as query param"}, status=status.HTTP_400_BAD_REQUEST)

        images = SKUImages.objects.filter(
            sku_id=sku_id,
            label__isnull=False,
            data_set=True
        ).select_related("version", "label")

        if not images.exists():
            return Response({"message": "No images found."}, status=status.HTTP_404_NOT_FOUND)

        grouped_data = {}
        for img in images:
            version_name = img.version.name if img.version else "Unknown Version"
            version_id = img.version.id if img.version else None
            image_url = request.build_absolute_uri(img.image.url) if img.image else ""

            image_data = {
                "image_url": image_url,
                "label_id": img.label.id if img.label else None,
                "label_name": img.label.name if img.label else None,
                "split_label": img.split_label,
                "data_set": img.data_set
            }

            if version_name not in grouped_data:
                grouped_data[version_name] = {
                    "count": 0,
                    "version_id": version_id,
                    "images": []
                }

            grouped_data[version_name]["images"].append(image_data)
            grouped_data[version_name]["count"] += 1

        return Response(grouped_data, status=status.HTTP_200_OK)
    
# from pathlib import Path

# sku_id = 1
# results_save_dir = Path(settings.MEDIA_ROOT) / str(sku_id)
# print(f"Results will be saved to: {results_save_dir}")

# class TrainingRunnerViewSet(viewsets.ViewSet):
#     BASE_DIR = settings.BASE_DIR
#     PID_DIR = os.path.join(BASE_DIR, "pids")
#     PID_FILE = os.path.join(PID_DIR, "train_script.pid")
#     SCRIPT_PATH = os.path.join(BASE_DIR, "ml_shell_scripts", "anomaly_detection", "train.py")

#     @swagger_auto_schema(
#         operation_summary="Run training script with arguments (background)",
#         request_body=openapi.Schema(
#             type=openapi.TYPE_OBJECT,
#             required=[
#                 "sku_id", "version_id", "augmentations"
#             ],
#             properties={
#                 "sku_id": openapi.Schema(type=openapi.TYPE_INTEGER),
#                 "version_id": openapi.Schema(type=openapi.TYPE_INTEGER),
#                 "augmentations": openapi.Schema(type=openapi.TYPE_STRING),

#                 # Optional with defaults
#                 "max_epochs": openapi.Schema(type=openapi.TYPE_INTEGER, default=1),
#                 "fetch_dataset_url": openapi.Schema(type=openapi.TYPE_STRING, default="http://localhost:8000/api/data-set/"),
#                 "seed": openapi.Schema(type=openapi.TYPE_INTEGER, default=42),
#                 "train_batch_size": openapi.Schema(type=openapi.TYPE_INTEGER, default=16),
#                 "eval_batch_size": openapi.Schema(type=openapi.TYPE_INTEGER, default=16),
#                 "devices": openapi.Schema(type=openapi.TYPE_INTEGER, default=1),
#                 "num_workers": openapi.Schema(type=openapi.TYPE_INTEGER, default=2),
#             }
#         ),
#         responses={200: "Training script started successfully"}
#     )
#     def create(self, request):
        
#         # ✅ Only required fields need validation
#         sku_id = request.data.get("sku_id")
#         version_id = request.data.get("version_id")
#         required_keys = ["sku_id", "version_id", "augmentations"]
#         if not all(key in request.data for key in required_keys):
#             return Response(
#                 {"message": f"Missing required fields. Required: {required_keys}"},
#                 status=status.HTTP_400_BAD_REQUEST
#             )

#         try:
#             # Fetch dataset name from SKU
#             try:
#                 sku = SKU.objects.get(id=request.data["sku_id"])
#                 dataset_name = sku.name or f"SKU_{sku.id}"
#             except SKU.DoesNotExist:
#                 return Response({"message": "SKU not found."}, status=status.HTTP_404_NOT_FOUND)

            
#             model_name = "AnomalyDetection1"
#             results_save_dir = os.path.join(settings.MEDIA_ROOT, "sku_images", str(sku.id))
#             print(f"Results will be saved to: {results_save_dir}")

#             # Use provided values or defaults
#             fetch_dataset_url = request.data.get("fetch_dataset_url", f"http://localhost:8000/api/data-set/?sku_id={sku_id}&version_id={version_id}&absolute_path=true")
#             max_epochs = request.data.get("max_epochs", 1)

#             # Base arguments
#             args = [
#                 sys.executable,
#                 self.SCRIPT_PATH,
#                 "--model_name", model_name,
#                 "--dataset_name", dataset_name,
#                 "--fetch_dataset_url", fetch_dataset_url,
#                 "--sku_id", str(sku_id),
#                 "--version_id", str(version_id),
#                 "--augmentations", request.data["augmentations"],
#                 "--results_save_dir", results_save_dir,
#                 "--max_epochs", str(max_epochs),
#             ]

#             # Optional arguments with defaults
#             optional_args = {
#                 "seed": 42,
#                 "train_batch_size": 16,
#                 "eval_batch_size": 16,
#                 "devices": 1,
#                 "num_workers": 2,
#             }
#             for key, default in optional_args.items():
#                 value = request.data.get(key, default)
#                 args.extend([f"--{key}", str(value)])

#             # Setup env
#             env = os.environ.copy()
#             env["PYTHONPATH"] = str(settings.BASE_DIR)

#             # Ensure PID dir
#             os.makedirs(self.PID_DIR, exist_ok=True)

#             creationflags = subprocess.CREATE_NEW_PROCESS_GROUP if os.name == 'nt' else 0

#             process = subprocess.Popen(
#                 args,
#                 start_new_session=(os.name != 'nt'),
#                 creationflags=creationflags,
#                 env=env
#             )

#             with open(self.PID_FILE, "w") as f:
#                 f.write(str(process.pid))

#             return Response({
#                 "message": f"✅ Training script started with PID {process.pid}",
#                 "process.pid": process.pid,
#                 "status": status.HTTP_200_OK
#             }, status=status.HTTP_200_OK)

#         except Exception as e:
#             return Response(
#                 {"message": f"❌ Error: {str(e)}"},
#                 status=status.HTTP_500_INTERNAL_SERVER_ERROR
#             )
            
class TrainingRunnerViewSet(viewsets.ViewSet):
    BASE_DIR = settings.BASE_DIR
    PID_DIR = os.path.join(BASE_DIR, "pids")
    PID_FILE = os.path.join(PID_DIR, "train_script.pid")
    SCRIPT_PATH = os.path.join(BASE_DIR, "ml_shell_scripts", "anomaly_detection", "train.py")

    @swagger_auto_schema(
        operation_summary="Run training script with arguments (background)",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["sku_id", "version_id", "augmentations"],
            properties={
                "sku_id": openapi.Schema(type=openapi.TYPE_INTEGER),
                "version_id": openapi.Schema(  # string, comma-separated
                    type=openapi.TYPE_STRING,
                    description="Comma-separated version IDs, e.g., '1,2,3'"
                ),
                "augmentations": openapi.Schema(type=openapi.TYPE_STRING),
                "max_epochs": openapi.Schema(type=openapi.TYPE_INTEGER, default=1),
                "fetch_dataset_url": openapi.Schema(type=openapi.TYPE_STRING, default="http://localhost:8000/api/data-set/"),
                "seed": openapi.Schema(type=openapi.TYPE_INTEGER, default=42),
                "train_batch_size": openapi.Schema(type=openapi.TYPE_INTEGER, default=16),
                "eval_batch_size": openapi.Schema(type=openapi.TYPE_INTEGER, default=16),
                "devices": openapi.Schema(type=openapi.TYPE_INTEGER, default=1),
                "num_workers": openapi.Schema(type=openapi.TYPE_INTEGER, default=2),
                
            }
        ),
        responses={200: "Training script started successfully"}
    )
    def create(self, request):
        sku_id = request.data.get("sku_id")
        version_id_str = request.data.get("version_id")  # now a string
        required_keys = ["sku_id", "version_id", "augmentations"]

        if not all(key in request.data for key in required_keys):
            return Response(
                {"message": f"Missing required fields. Required: {required_keys}"},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not isinstance(version_id_str, str) or not version_id_str.strip():
            return Response(
                {"message": "version_id must be a non-empty comma-separated string of integers."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            try:
                sku = SKU.objects.get(id=sku_id)
                dataset_name = sku.name or f"SKU_{sku.id}"
            except SKU.DoesNotExist:
                return Response({"message": "SKU not found."}, status=status.HTTP_404_NOT_FOUND)

            model_name = "AnomalyDetection1"
            results_save_dir = os.path.join(settings.MEDIA_ROOT, "sku_images", str(sku.id))
            print(f"Results will be saved to: {results_save_dir}")

            fetch_dataset_url = request.data.get(
                "fetch_dataset_url",
                f"http://localhost:8000/api/data-set/?sku_id={sku_id}&version_id={version_id_str}&absolute_path=true"
            )
            max_epochs = request.data.get("max_epochs", 1)
            progress_api = request.data.get("progress_api", "http://localhost:8000/api/training-progress/")
            args = [
                sys.executable,
                self.SCRIPT_PATH,
                "--model_name", model_name,
                "--dataset_name", dataset_name,
                "--fetch_dataset_url", fetch_dataset_url,
                "--sku_id", str(sku_id),
                "--version_id", version_id_str,
                "--augmentations", request.data["augmentations"],
                "--results_save_dir", results_save_dir,
                "--max_epochs", str(max_epochs),
                "--progress_api", progress_api
            ]

            optional_args = {
                "seed": 42,
                "train_batch_size": 16,
                "eval_batch_size": 16,
                "devices": 1,
                "num_workers": 2,
            }
            for key, default in optional_args.items():
                value = request.data.get(key, default)
                args.extend([f"--{key}", str(value)])

            env = os.environ.copy()
            env["PYTHONPATH"] = str(settings.BASE_DIR)

            os.makedirs(self.PID_DIR, exist_ok=True)

            creationflags = subprocess.CREATE_NEW_PROCESS_GROUP if os.name == 'nt' else 0

            process = subprocess.Popen(
                args,
                start_new_session=(os.name != 'nt'),
                creationflags=creationflags,
                env=env
            )

            with open(self.PID_FILE, "w") as f:
                f.write(str(process.pid))

            return Response({
                "message": f"✅ Training script started with PID {process.pid}",
                "process.pid": process.pid,
                "status": status.HTTP_200_OK
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response(
                {"message": f"❌ Error: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @swagger_auto_schema(
        operation_summary="Terminate background training script process",
        responses={200: "Terminated", 404: "Not found", 500: "Error"}
    )
    def destroy(self, request, pk=None):
        if not os.path.exists(self.PID_FILE):
            return Response({"message": "PID file not found."}, status=status.HTTP_404_NOT_FOUND)

        try:
            with open(self.PID_FILE, "r") as f:
                pid = int(f.read().strip())

            if os.name == 'nt':
                os.kill(pid, signal.SIGTERM)
            else:
                os.killpg(pid, signal.SIGTERM)

            os.remove(self.PID_FILE)

            return Response({"message": f"Training process with PID {pid} terminated."}, status=status.HTTP_200_OK)

        except ProcessLookupError:
            os.remove(self.PID_FILE)
            return Response({"message": "Process not found (already exited?)."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"message": f"Error terminating process: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class TestRunnerViewSet(viewsets.ViewSet):
    BASE_DIR = settings.BASE_DIR
    PID_DIR = os.path.join(BASE_DIR, "pids")
    PID_FILE = os.path.join(PID_DIR, "test_script.pid")
    SCRIPT_PATH = os.path.join(BASE_DIR, "ml_shell_scripts", "anomaly_detection", "test.py")

    # @swagger_auto_schema(
    #     operation_summary="Run test script with arguments (background)",
    #     request_body=openapi.Schema(
    #         type=openapi.TYPE_OBJECT,
    #         required=["sku_id", "version_id", "model_name", "ckpt_path"],
    #         properties={
    #             "sku_id": openapi.Schema(type=openapi.TYPE_INTEGER),
    #             "version_id": openapi.Schema(type=openapi.TYPE_INTEGER),
    #             "model_name": openapi.Schema(type=openapi.TYPE_STRING),
    #             "ckpt_path": openapi.Schema(type=openapi.TYPE_STRING),
    #             # "fetch_testset_url": openapi.Schema(type=openapi.TYPE_STRING, default=""),
    #             # "end_point_url": openapi.Schema(type=openapi.TYPE_STRING, default=""),
    #         }
    #     ),
    #     responses={200: "Test script started successfully"}
    # )
    @swagger_auto_schema(
        operation_summary="Run test script for a model",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["sku_id", "version_id", "model_name", "ckpt_path"],
            properties={
                "sku_id": openapi.Schema(type=openapi.TYPE_INTEGER, description="SKU ID"),
                "version_id": openapi.Schema(  # string, comma-separated
                    type=openapi.TYPE_STRING,
                    description="Comma-separated version IDs, e.g., '1,2,3'"
                ),
                "model_name": openapi.Schema(type=openapi.TYPE_STRING, description="Name of the ML model"),
                "ckpt_path": openapi.Schema(type=openapi.TYPE_STRING, description="Checkpoint path for the model"),
                # "fetch_testset_url": openapi.Schema(type=openapi.TYPE_STRING, description="URL to fetch test dataset (optional)"),
            },
        )
    )
    
    
    # def create(self, request):
    #     try:
    #         # Required fields
    #         sku_id = request.data.get("sku_id")
    #         version_id = request.data.get("version_id")
    #         model_name = request.data.get("model_name")
    #         ckpt_path = request.data.get("ckpt_path")

    #         if not all([sku_id, version_id, model_name, ckpt_path]):
    #             return Response(
    #                 {"message": "Missing required fields. 'sku_id', 'version_id', 'model_name', and 'ckpt_path' are required."},
    #                 status=status.HTTP_400_BAD_REQUEST
    #             )

    #         # Optional field
    #         fetch_testset_url = request.data.get(
    #             "fetch_testset_url",
    #             f"http://localhost:8000/api/data-set/?sku_id={sku_id}&version_id={version_id}&absolute_path=true"
    #         )

    #         # Build results save directory path
    #         results_save_dir = os.path.join(settings.MEDIA_ROOT, "sku_images", str(sku_id))
    #         print(f"Results will be saved to: {results_save_dir}")

    #         # Script arguments
    #         args = [
    #             sys.executable,
    #             self.SCRIPT_PATH,
    #             "--sku_id", str(sku_id),
    #             "--version_id", str(version_id),
    #             "--model_name", model_name,
    #             "--ckpt_path", ckpt_path,
    #             "--fetch_testset_url", fetch_testset_url,
    #             "--results_save_dir", results_save_dir,
    #         ]

    #         # Timestamp for result saving (if needed in script)
    #         timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
    #         args.extend(["--save_result_dir_timestamp", timestamp])

    #         # Set up environment
    #         env = os.environ.copy()
    #         env["PYTHONPATH"] = str(settings.BASE_DIR)

    #         # Ensure PID directory exists
    #         os.makedirs(self.PID_DIR, exist_ok=True)

    #         creationflags = subprocess.CREATE_NEW_PROCESS_GROUP if os.name == 'nt' else 0

    #         # Launch subprocess
    #         process = subprocess.Popen(
    #             args,
    #             start_new_session=(os.name != 'nt'),
    #             creationflags=creationflags,
    #             env=env
    #         )

    #         with open(self.PID_FILE, "w") as f:
    #             f.write(str(process.pid))

    #         return Response({
    #             "message": f"Test script started with PID {process.pid}",
    #             "process.pid": process.pid,
    #             "status": status.HTTP_200_OK
    #         }, status=status.HTTP_200_OK)

    #     except Exception as e:
    #         return Response(
    #             {"message": f"Error: {str(e)}"},
    #             status=status.HTTP_500_INTERNAL_SERVER_ERROR
    #         )
    
    def create(self, request):
        try:
            # Required fields
            sku_id = request.data.get("sku_id")
            version_ids = request.data.get("version_id")  # can be comma-separated string
            model_name = request.data.get("model_name")
            ckpt_path = request.data.get("ckpt_path")
            progress_api = request.data.get("progress_api", "http://localhost:8000/api/testing-progress/")
            if not all([sku_id, version_ids, model_name, ckpt_path]):
                return Response(
                    {"message": "Missing required fields. 'sku_id', 'version_id', 'model_name', and 'ckpt_path' are required."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Prepare fetch_testset_url with full version_ids string
            fetch_testset_url = request.data.get(
                "fetch_testset_url",
                f"http://localhost:8000/api/data-set/?sku_id={sku_id}&version_id={version_ids}&absolute_path=true"
            )

            # Build results save directory path
            results_save_dir = os.path.join(settings.MEDIA_ROOT, "sku_images", str(sku_id))
            print(f"Results will be saved to: {results_save_dir}")

            # Script arguments
            args = [
                sys.executable,
                self.SCRIPT_PATH,
                "--sku_id", str(sku_id),
                "--version_id", version_ids,  # send as-is, comma-separated
                "--model_name", model_name,
                "--ckpt_path", ckpt_path,
                "--fetch_testset_url", fetch_testset_url,
                "--results_save_dir", results_save_dir,
                "--progress_api", progress_api
            ]

            # Timestamp for result saving (if needed in script)
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
            args.extend(["--save_result_dir_timestamp", timestamp])

            # Set up environment
            env = os.environ.copy()
            env["PYTHONPATH"] = str(settings.BASE_DIR)

            # Ensure PID directory exists
            os.makedirs(self.PID_DIR, exist_ok=True)

            creationflags = subprocess.CREATE_NEW_PROCESS_GROUP if os.name == 'nt' else 0

            # Launch subprocess (single task for multiple version IDs)
            process = subprocess.Popen(
                args,
                start_new_session=(os.name != 'nt'),
                creationflags=creationflags,
                env=env
            )

            with open(self.PID_FILE, "w") as f:
                f.write(str(process.pid))

            return Response({
                "message": f"Test script started with PID {process.pid}",
                "process.pid": process.pid,
                "status": status.HTTP_200_OK
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response(
                {"message": f"Error: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )



    @swagger_auto_schema(
        operation_summary="Terminate background test script process",
        responses={200: "Terminated", 404: "Not found", 500: "Error"}
    )
    def destroy(self, request, pk=None):
        if not os.path.exists(self.PID_FILE):
            print('PID file path', self.PID_FILE)
            return Response({"message": "PID file not found."}, status=status.HTTP_404_NOT_FOUND)

        try:
            with open(self.PID_FILE, "r") as f:
                pid = int(f.read().strip())

            if os.name == 'nt':
                os.kill(pid, signal.SIGTERM)
            else:
                os.killpg(pid, signal.SIGTERM)

            os.remove(self.PID_FILE)

            return Response({"message": f"Test process with PID {pid} terminated."}, status=status.HTTP_200_OK)

        except ProcessLookupError:
            os.remove(self.PID_FILE)
            return Response({"message": "Process not found (already exited?)."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"message": f"Error terminating process: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class TestResultsViewSet(viewsets.ViewSet):

    @swagger_auto_schema(
        operation_summary="Create TestResult with base64 image and folder",
        operation_description="""
        Upload a base64-encoded image for a specific SKU and Version.

        The image will be saved inside: `sku_images/<sku_id>/<folder_name>/filename.jpg`

        If the folder with given name doesn't exist, it will be created.

        Example `meta_data`: {"source": "camera_1", "timestamp": "2025-07-01T12:00:00Z"}
        """,
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["sku_id", "version_id", "image", "folder_name"],
            properties={
                "sku_id": openapi.Schema(type=openapi.TYPE_INTEGER, description="ID of the SKU"),
                "version_id": openapi.Schema(type=openapi.TYPE_INTEGER, description="ID of the Version"),
                "folder_name": openapi.Schema(type=openapi.TYPE_STRING, description="Name of the subfolder to save the image"),
                "image": openapi.Schema(type=openapi.TYPE_STRING, description="Base64-encoded image string"),
                "meta_data": openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    description="Optional metadata dictionary"
                )
            }
        ),
        responses={
            201: openapi.Response(description="TestResult created successfully"),
            400: openapi.Response(description="Missing required fields or bad request"),
            404: openapi.Response(description="SKU or Version not found"),
            500: openapi.Response(description="Internal server error")
        }
    )
    def create(self, request):
        required_fields = ['sku_id', 'version_id', 'image', 'folder_name']
        if not all(field in request.data for field in required_fields):
            return Response(
                {"message": f"Missing required fields: {required_fields}"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            sku = SKU.objects.get(id=request.data['sku_id'])
            version = Versions.objects.get(id=request.data['version_id'])

            folder_name = request.data['folder_name'].strip()

            # Get or create the folder
            folder, _ = TestResultsFolder.objects.get_or_create(sku=sku, name=folder_name)

            # Decode base64 image
            image_base64 = request.data['image']
            format, imgstr = image_base64.split(';base64,')
            ext = format.split('/')[-1]
            image_name = f"{sku.id}_{version.id}_{TestResults.objects.filter(sku=sku).count()}.{ext}"
            image_file = ContentFile(base64.b64decode(imgstr), name=image_name)

            # Optional meta_data
            meta_data = request.data.get("meta_data", {})

            test_result = TestResults.objects.create(
                sku=sku,
                version=version,
                folder=folder,
                image=image_file,
                meta_data=meta_data
            )

            return Response({
                "message": "✅ TestResult created successfully.",
                "id": test_result.id
            }, status=status.HTTP_201_CREATED)

        except SKU.DoesNotExist:
            return Response({"message": "❌ SKU not found."}, status=status.HTTP_404_NOT_FOUND)
        except Versions.DoesNotExist:
            return Response({"message": "❌ Version not found."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"message": f"❌ Error: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
    @swagger_auto_schema(
        operation_summary="List Test Results",
        operation_description="""
        Returns a list of test results with optional filters:
        - Filter by `sku_id`
        - Filter by `version_id`
        - Search by partial `image` filename (case-insensitive)
        """,
        manual_parameters=[
            openapi.Parameter(
                'sku_id', openapi.IN_QUERY,
                type=openapi.TYPE_INTEGER,
                description='Filter by SKU ID',
                required=False
            ),
            openapi.Parameter(
                'version_id', openapi.IN_QUERY,
                type=openapi.TYPE_INTEGER,
                description='Filter by Version ID',
                required=False
            ),
            openapi.Parameter(
                'search', openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                description='Search in image filename',
                required=False
            ),
        ],
        responses={
            200: openapi.Response(description="List of Test Results"),
            400: openapi.Response(description="Bad Request")
        }
    )
    def list(self, request):
        sku_id = request.query_params.get("sku_id")
        version_id = request.query_params.get("version_id")
        search = request.query_params.get("search")

        test_results = TestResults.objects.all()

        if sku_id:
            test_results = test_results.filter(sku_id=sku_id)
        if version_id:
            test_results = test_results.filter(version_id=version_id)
        if search:
            test_results = test_results.filter(image__icontains=search)

        results = [
            {
                "id": tr.id,
                "sku_id": tr.sku.id if tr.sku else None,
                "version_id": tr.version.id if tr.version else None,
                "folder_id": tr.folder.id if tr.folder else None,
                "image_url": tr.image.url if tr.image else None,
                "meta_data": tr.meta_data
            }
            for tr in test_results
        ]

        return Response({"results": results}, status=status.HTTP_200_OK)

class TestResultsFolderViewSet(viewsets.ViewSet):

    @swagger_auto_schema(
        operation_summary="List Test Results Folders",
        operation_description="""
            Returns a list of test result folders.  
            - Filter by `sku_id` using query param.  
            - Search by `name` (partial match, case-insensitive).
        """,
        manual_parameters=[
            openapi.Parameter(
                'sku_id', openapi.IN_QUERY, description="Filter by SKU ID",
                type=openapi.TYPE_INTEGER, required=False
            ),
            openapi.Parameter(
                'search', openapi.IN_QUERY, description="Search by folder name",
                type=openapi.TYPE_STRING, required=False
            ),
        ],
        responses={
            200: openapi.Response(description="List of folders"),
            400: openapi.Response(description="Bad Request"),
        }
    )
    def list(self, request):
        sku_id = request.query_params.get('sku_id')
        search = request.query_params.get('search')

        folders = TestResultsFolder.objects.all()

        if sku_id:
            folders = folders.filter(sku_id=sku_id)

        if search:
            folders = folders.filter(name__icontains=search)

        results = [
            {
                "id": folder.id,
                "sku_id": folder.sku.id if folder.sku else None,
                "name": folder.name,
            }
            for folder in folders
        ]

        return Response({"results": results}, status=status.HTTP_200_OK)
    

class FileExplorerViewSet(viewsets.ViewSet):    

    @swagger_auto_schema(
        operation_summary="Explore files and folders for a given SKU",
        operation_description="Same as before, but merges model + json with JSON content.",
        manual_parameters=[
            openapi.Parameter(
                'sku_id', openapi.IN_QUERY, description="SKU ID", type=openapi.TYPE_INTEGER, required=True
            ),
            openapi.Parameter(
                'path', openapi.IN_QUERY, description="Relative path inside SKU folder", type=openapi.TYPE_STRING
            ),
        ],
    )
    def list(self, request):
        sku_id = request.query_params.get("sku_id")
        if not sku_id:
            return Response({"message": "sku_id is required."}, status=status.HTTP_400_BAD_REQUEST)

        inner_path = request.query_params.get("path", "")
        rel_path = os.path.join("sku_images", str(sku_id), inner_path)
        abs_path = os.path.abspath(os.path.join(settings.MEDIA_ROOT, rel_path))

        if not abs_path.startswith(os.path.abspath(settings.MEDIA_ROOT)):
            return Response({"message": "Invalid path access."}, status=status.HTTP_400_BAD_REQUEST)
        if not os.path.exists(abs_path):
            return Response({"message": "Path not found."}, status=status.HTTP_404_NOT_FOUND)
        if not os.path.isdir(abs_path):
            return Response({"message": "Provided path is not a directory."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            entries = os.listdir(abs_path)

            # Directories
            directories = [
                {"name": entry, "absolute_path": os.path.abspath(os.path.join(abs_path, entry))}
                for entry in entries if os.path.isdir(os.path.join(abs_path, entry))
            ]

            # Process files - group by base name (without extension)
            file_map = {}
            processed_files = set()  # Keep track of files we've already processed
            
            for entry in entries:
                file_path = os.path.join(abs_path, entry)
                if os.path.isfile(file_path):
                    name, ext = os.path.splitext(entry)
                    
                    # Initialize file entry if not exists
                    if name not in file_map:
                        file_map[name] = {"meta_data": None, "url": None, "absolute_path": None}
                    
                    if ext.lower() == ".json":
                        # Load JSON content
                        try:
                            with open(file_path, "r") as f:
                                file_map[name]["meta_data"] = json.load(f)
                        except Exception as e:
                            file_map[name]["meta_data"] = {"error": str(e)}
                        processed_files.add(entry)
                    
                    elif ext.lower() in [".pt", ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tiff"]:
                        # Handle model files and image files
                        file_map[name]["url"] = request.build_absolute_uri(
                            os.path.join(settings.MEDIA_URL, rel_path, entry).replace("\\", "/")
                        )
                        file_map[name]["absolute_path"] = os.path.abspath(file_path)
                        processed_files.add(entry)

            # Handle any remaining files that don't have pairs
            other_files = []
            for entry in entries:
                file_path = os.path.join(abs_path, entry)
                if os.path.isfile(file_path) and entry not in processed_files:
                    other_files.append({
                        "meta_data": None,
                        "url": request.build_absolute_uri(
                            os.path.join(settings.MEDIA_URL, rel_path, entry).replace("\\", "/")
                        ),
                        "absolute_path": os.path.abspath(file_path)
                    })

            # Combine results - only include file_map entries that have at least one property set
            combined_files = []
            for name, file_data in file_map.items():
                if any(value is not None for value in file_data.values()):
                    combined_files.append(file_data)
            
            combined_files.extend(other_files)

            return Response({
                "sku_id": sku_id,
                "current_path": rel_path,
                "directories": directories,
                "files": combined_files,
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"message": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
# class ModelFileExplorerViewSet(viewsets.ViewSet):

#     @swagger_auto_schema(
#         operation_summary="List all .pt model files for a given SKU (recursively)",
#         operation_description="""
#         This endpoint returns all `.pt` files under `MEDIA_ROOT/sku_images/<sku_id>/`, recursively searching subfolders.

#         - `sku_id` is required.
#         """,
#         manual_parameters=[
#             openapi.Parameter(
#                 'sku_id',
#                 openapi.IN_QUERY,
#                 description="ID of the SKU folder",
#                 type=openapi.TYPE_INTEGER,
#                 required=True
#             ),
#         ],
#         responses={
#             200: openapi.Response(
#                 description="List of .pt model file URLs",
#                 schema=openapi.Schema(
#                     type=openapi.TYPE_OBJECT,
#                     properties={
#                         "sku_id": openapi.Schema(type=openapi.TYPE_INTEGER),
#                         "model_files": openapi.Schema(
#                             type=openapi.TYPE_ARRAY,
#                             items=openapi.Items(type=openapi.TYPE_STRING)
#                         ),
#                     }
#                 )
#             ),
#             400: "Missing or invalid sku_id",
#             404: "Path not found"
#         }
#     )
#     def list(self, request):
#         sku_id = request.query_params.get("sku_id")
#         if not sku_id:
#             return Response({"message": "sku_id is required."}, status=status.HTTP_400_BAD_REQUEST)

#         base_path = os.path.join(settings.MEDIA_ROOT, "sku_images", str(sku_id))
#         if not os.path.exists(base_path):
#             return Response({"message": "SKU folder not found."}, status=status.HTTP_404_NOT_FOUND)

#         model_files = []
#         for root, _, files in os.walk(base_path):
#             for file in files:
#                 if file.endswith((".pt", ".ckpt")):
#                     full_path = os.path.join(root, file)
#                     relative_path = os.path.relpath(full_path, settings.MEDIA_ROOT)
#                     file_url = request.build_absolute_uri(os.path.join(settings.MEDIA_URL, relative_path).replace("\\", "/"))
#                     model_files.append(file_url)

#         return Response({
#             "sku_id": sku_id,
#             "model_files": model_files
#         }, status=status.HTTP_200_OK)

# class ModelFileExplorerViewSet(viewsets.ViewSet):

#     @swagger_auto_schema(
#         operation_summary="List all .pt/.ckpt model files for a given SKU (recursively)",
#         operation_description="""
#         This endpoint returns all `.pt` and `.ckpt` files under `MEDIA_ROOT/sku_images/<sku_id>/`,
#         recursively searching all subdirectories.

#         - `sku_id` is required.
#         """,
#         manual_parameters=[
#             openapi.Parameter(
#                 'sku_id',
#                 openapi.IN_QUERY,
#                 description="ID of the SKU folder",
#                 type=openapi.TYPE_INTEGER,
#                 required=True
#             ),
#         ],
#         responses={
#             200: openapi.Response(
#                 description="List of .pt/.ckpt model files with URLs and absolute paths",
#                 schema=openapi.Schema(
#                     type=openapi.TYPE_OBJECT,
#                     properties={
#                         "sku_id": openapi.Schema(type=openapi.TYPE_INTEGER),
#                         "model_files": openapi.Schema(
#                             type=openapi.TYPE_ARRAY,
#                             items=openapi.Schema(
#                                 type=openapi.TYPE_OBJECT,
#                                 properties={
#                                     "url": openapi.Schema(type=openapi.TYPE_STRING),
#                                     "absolute_path": openapi.Schema(type=openapi.TYPE_STRING),
#                                 }
#                             )
#                         ),
#                     }
#                 )
#             ),
#             400: "Missing or invalid sku_id",
#             404: "Path not found"
#         }
#     )
#     def list(self, request):
#         sku_id = request.query_params.get("sku_id")
#         if not sku_id:
#             return Response({"message": "sku_id is required."}, status=status.HTTP_400_BAD_REQUEST)

#         base_path = os.path.join(settings.MEDIA_ROOT, "sku_images", str(sku_id))
#         if not os.path.exists(base_path):
#             return Response({"message": "SKU folder not found."}, status=status.HTTP_404_NOT_FOUND)

#         model_files = []
#         for root, _, files in os.walk(base_path):
#             for file in files:
#                 if file.endswith((".pt", ".ckpt")):
#                     full_path = os.path.join(root, file)
#                     relative_path = os.path.relpath(full_path, settings.MEDIA_ROOT)
#                     file_url = request.build_absolute_uri(
#                         os.path.join(settings.MEDIA_URL, relative_path).replace("\\", "/")
#                     )
#                     model_files.append({
#                         "url": file_url,
#                         "absolute_path": full_path
#                     })

#         return Response({
#             "sku_id": sku_id,
#             "model_files": model_files
#         }, status=status.HTTP_200_OK)
        
        
# class ModelFileExplorerViewSet(viewsets.ViewSet):

#     @swagger_auto_schema(
#         operation_summary="List all .pt/.ckpt model files for a given SKU (recursively)",
#         operation_description="""
#         This endpoint returns all `.pt` and `.ckpt` files under `MEDIA_ROOT/sku_images/<sku_id>/`,
#         recursively searching all subdirectories.

#         - `sku_id` is required.
#         """,
#         manual_parameters=[
#             openapi.Parameter(
#                 'sku_id',
#                 openapi.IN_QUERY,
#                 description="ID of the SKU folder",
#                 type=openapi.TYPE_INTEGER,
#                 required=True
#             ),
#         ],
#         responses={
#             200: openapi.Response(
#                 description="List of .pt/.ckpt model files with URLs and absolute paths",
#                 schema=openapi.Schema(
#                     type=openapi.TYPE_OBJECT,
#                     properties={
#                         "sku_id": openapi.Schema(type=openapi.TYPE_INTEGER),
#                         "model_files": openapi.Schema(
#                             type=openapi.TYPE_ARRAY,
#                             items=openapi.Schema(
#                                 type=openapi.TYPE_OBJECT,
#                                 properties={
#                                     "name": openapi.Schema(type=openapi.TYPE_STRING),
#                                     "url": openapi.Schema(type=openapi.TYPE_STRING),
#                                     "absolute_path": openapi.Schema(type=openapi.TYPE_STRING),
#                                 }
#                             )
#                         ),
#                     }
#                 )
#             ),
#             400: "Missing or invalid sku_id",
#             404: "Path not found"
#         }
#     )
#     def list(self, request):
#         sku_id = request.query_params.get("sku_id")
#         if not sku_id:
#             return Response({"message": "sku_id is required."}, status=status.HTTP_400_BAD_REQUEST)

#         base_path = os.path.join(settings.MEDIA_ROOT, "sku_images", str(sku_id))
#         if not os.path.exists(base_path):
#             return Response({"message": "SKU folder not found."}, status=status.HTTP_404_NOT_FOUND)

#         model_files = []
#         for root, _, files in os.walk(base_path):
#             for file in files:
#                 if file.endswith((".pt", ".ckpt")):
#                     full_path = os.path.join(root, file)
#                     relative_path = os.path.relpath(full_path, settings.MEDIA_ROOT)
#                     file_url = request.build_absolute_uri(
#                         os.path.join(settings.MEDIA_URL, relative_path).replace("\\", "/")
#                     )
#                     model_files.append({
#                         "name": file,
#                         "url": file_url,
#                         "absolute_path": full_path
#                     })

#         return Response({
#             "sku_id": sku_id,
#             "model_files": model_files
#         }, status=status.HTTP_200_OK)

class ModelFileExplorerViewSet(viewsets.ViewSet):

    @swagger_auto_schema(
        operation_summary="List all .pt/.ckpt model files for a given SKU (recursively, with optional JSON metadata)",
        operation_description="""
        This endpoint returns all `.pt` and `.ckpt` files under `MEDIA_ROOT/sku_images/<sku_id>/`,
        recursively searching all subdirectories.
        If a `.json` file exists in the same directory as the model file, it will be read and added
        to the response as `metadata`.
        """,
        manual_parameters=[
            openapi.Parameter(
                'sku_id',
                openapi.IN_QUERY,
                description="ID of the SKU folder",
                type=openapi.TYPE_INTEGER,
                required=True
            ),
        ],
        responses={
            200: openapi.Response(
                description="List of .pt/.ckpt model files with URLs, absolute paths, and optional metadata",
            ),
            400: "Missing or invalid sku_id",
            404: "Path not found"
        }
    )
    def list(self, request):
        sku_id = request.query_params.get("sku_id")
        if not sku_id:
            return Response({"message": "sku_id is required."}, status=status.HTTP_400_BAD_REQUEST)

        base_path = os.path.join(settings.MEDIA_ROOT, "sku_images", str(sku_id))
        if not os.path.exists(base_path):
            return Response({"message": "SKU folder not found."}, status=status.HTTP_404_NOT_FOUND)

        model_files = []
        for root, _, files in os.walk(base_path):
            for file in files:
                if file.endswith((".pt", ".ckpt")):
                    full_path = os.path.join(root, file)
                    relative_path = os.path.relpath(full_path, settings.MEDIA_ROOT)
                    file_url = request.build_absolute_uri(
                        os.path.join(settings.MEDIA_URL, relative_path).replace("\\", "/")
                    )

                    # Look for JSON file in same folder
                    metadata = None
                    for sibling in files:
                        if sibling.endswith(".json"):
                            json_path = os.path.join(root, sibling)
                            try:
                                with open(json_path, "r") as jf:
                                    metadata = json.load(jf)
                            except Exception as e:
                                metadata = {"error": f"Could not read JSON: {str(e)}"}
                            break

                    model_files.append({
                        "name": file,
                        "url": file_url,
                        "absolute_path": full_path,
                        "meta_data": metadata
                    })

        return Response({
            "sku_id": sku_id,
            "model_files": model_files
        }, status=status.HTTP_200_OK)

import uuid
import time
import json
import datetime
from collections import deque
from django.http import StreamingHttpResponse
from rest_framework import viewsets, status
from rest_framework.response import Response

# Global variables
image_queue = deque(maxlen=1000)
active_streams = {}

class ImageStreamViewSet(viewsets.ViewSet):
    @swagger_auto_schema(
        operation_summary="Uploading base64 image for streaming",
        operation_description="""
        Upload a base64-encoded image for streaming.
        """,
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["sku_id", "version_id", "image", "folder_name"],
            properties={
                "image": openapi.Schema(type=openapi.TYPE_STRING, description="base64-encoded image string"),
            }
        ),
    )
    def create(self, request):
        image_data = request.data.get('image')
        if not image_data:
            return Response({"message": "image is required"}, status=status.HTTP_400_BAD_REQUEST)
        
        image_info = {
            'id': str(uuid.uuid4()),
            'image': image_data,
            'timestamp': datetime.datetime.now().isoformat()
        }
        image_queue.append(image_info)

        return Response({
            "message": "Image sent for streaming",
            "image_id": image_info['id'],
            "timestamp": image_info['timestamp'],
            "queue_length": len(image_queue)
        }, status=status.HTTP_200_OK)

    def list(self, request, *args, **kwargs):
        def event_stream():
            stream_id = str(uuid.uuid4())
            active_streams[stream_id] = {
                'connected': True,
                'last_image_index': len(image_queue) - 1 if image_queue else -1
            }
            print(f"Stream started: {stream_id}")
            yield f"data: {json.dumps({'type': 'connected', 'stream_id': stream_id})}\n\n"

            try:
                while True:
                    current = active_streams.get(stream_id)
                    if not current:
                        break

                    last_index = current['last_image_index']
                    if len(image_queue) > last_index + 1:
                        for i in range(last_index + 1, len(image_queue)):
                            image_data = image_queue[i]
                            yield f"data: {json.dumps({'type': 'image', 'data': image_data})}\n\n"
                        current['last_image_index'] = len(image_queue) - 1
                    else:
                        yield f"data: {json.dumps({'type': 'ping'})}\n\n"
                    time.sleep(0.5)
            except Exception as e:
                print(f"Stream error: {e}")
            finally:
                active_streams.pop(stream_id, None)
                print(f"Stream closed: {stream_id}")
                yield f"data: {json.dumps({'type': 'close', 'message': 'Stream ended'})}\n\n"

        response = StreamingHttpResponse(event_stream(), content_type='text/event-stream; charset=utf-8')
        response['Cache-Control'] = 'no-cache'
        response['Access-Control-Allow-Origin'] = '*'
        response['Access-Control-Allow-Headers'] = 'Cache-Control, Accept, Content-Type'
        response['Access-Control-Allow-Methods'] = 'GET, OPTIONS'
        return response


def stream_images_view(request):
    # print(f"GET /api/stream-images/ from {request.META.get('REMOTE_ADDR')}")
    def event_stream():
        stream_id = str(uuid.uuid4())
        active_streams[stream_id] = {
            'connected': True,
            'last_image_index': len(image_queue) - 1 if image_queue else -1
        }
        print(f"Stream started: {stream_id}")
        yield f"data: {json.dumps({'type': 'connected', 'message': 'Stream started', 'stream_id': stream_id})}\n\n"
        
        try:
            for _ in range(1200):
                if stream_id not in active_streams:
                    break
                current_stream = active_streams[stream_id]
                last_index = current_stream['last_image_index']
                
                if len(image_queue) > last_index + 1:
                    for i in range(last_index + 1, len(image_queue)):
                        image_data = image_queue[i]
                        print(f"Sending image: {image_data['id']}")
                        yield f"data: {json.dumps({'type': 'image', 'data': image_data})}\n\n"
                    active_streams[stream_id]['last_image_index'] = len(image_queue) - 1
                time.sleep(0.5)
        except Exception as e:
            print(f"Stream error: {e}")
        finally:
            if stream_id in active_streams:
                del active_streams[stream_id]
            print(f"Stream closed: {stream_id}")
            yield f"data: {json.dumps({'type': 'close', 'message': 'Stream ended'})}\n\n"
    
    response = StreamingHttpResponse(event_stream(), content_type='text/event-stream; charset=utf-8')
    response['Cache-Control'] = 'no-cache'
    response['Access-Control-Allow-Origin'] = '*'
    response['Access-Control-Allow-Headers'] = 'Cache-Control, Accept, Content-Type'
    response['Access-Control-Allow-Methods'] = 'GET, OPTIONS'
    return response

# Function-based view for serving the stream page
def stream_page_view(request):
    """
    Serve the image stream HTML page
    GET /stream/
    """
    from django.shortcuts import render
    return render(request, 'stream.html')

class VersionDuplicateViewSet(viewsets.ViewSet):

    def create(self, request):
        """
        Duplicate a version along with its associated images.

        POST /api/version-duplicate/
        Required in body:
        - version_id: ID of the original version
        - new_version_name: name for the duplicated version
        """
        version_id = request.data.get("version_id")
        new_version_name = request.data.get("new_version_name")

        if not version_id or not new_version_name:
            return Response({"message": "Both 'version_id' and 'new_version_name' are required."},
                            status=status.HTTP_400_BAD_REQUEST)

        try:
            original_version = Versions.objects.get(id=version_id)
        except Versions.DoesNotExist:
            return Response({"message": "Version not found."}, status=status.HTTP_404_NOT_FOUND)

        if Versions.objects.filter(name__iexact=new_version_name, sku=original_version.sku).exists():
            return Response(
                {"message": f"Version with name '{new_version_name}' already exists for this SKU."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            with transaction.atomic():
                new_version = Versions.objects.create(
                    name=new_version_name,
                    sku=original_version.sku
                )

                original_images = SKUImages.objects.filter(version=original_version)
                duplicated_images_count = 0

                for original_image in original_images:
                    new_image = SKUImages(
                        sku=original_image.sku,
                        tags=original_image.tags,
                        version=new_version,
                        original_filename=original_image.original_filename,
                        content_hash=original_image.content_hash,
                        label=original_image.label,
                        rejected=original_image.rejected,
                        split_label=original_image.split_label,
                        data_set=original_image.data_set
                    )

                    if original_image.image:
                        try:
                            original_image.image.seek(0)
                            image_content = original_image.image.read()
                            filename = original_image.original_filename or original_image.image.name.split('/')[-1]
                            new_image.image.save(
                                filename,
                                ContentFile(image_content),
                                save=False
                            )
                            new_image.content_hash = hashlib.md5(image_content).hexdigest()
                        except Exception as e:
                            print(f"Error copying image file: {e}")
                            continue

                    new_image.save()
                    duplicated_images_count += 1

                return Response({
                    "id": new_version.id,
                    "name": new_version.name,
                    "sku": new_version.sku.id,
                    "duplicated_images_count": duplicated_images_count,
                    "message": f"Version '{new_version_name}' created successfully with {duplicated_images_count} images duplicated."
                }, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response(
                {"message": f"Error duplicating version: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
            

progress_queue = deque(maxlen=1000)
active_streams = {}

class TrainingProgressViewSet(viewsets.ViewSet):
    """
    Handles training progress updates and Server-Sent Events (SSE) streaming
    """

    @swagger_auto_schema(
        operation_summary="Push training progress update",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["job_id", "progress", "status"],
            properties={
                "job_id": openapi.Schema(type=openapi.TYPE_STRING, description="Job UUID"),
                "progress": openapi.Schema(type=openapi.TYPE_NUMBER, description="Progress percentage"),
                "status": openapi.Schema(type=openapi.TYPE_STRING, description="Status of the job"),
            },
        ),
        responses={200: openapi.Response(description="Progress update added")}
    )
    def create(self, request):
        job_id = request.data.get("job_id")
        progress = request.data.get("progress")
        status_msg = request.data.get("status")

        if not job_id or progress is None or not status_msg:
            return Response(
                {"message": "job_id, progress and status are required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        update = {
            "id": str(uuid.uuid4()),
            "job_id": job_id,
            "progress": progress,
            "status": status_msg,
            "timestamp": time.time()
        }
        progress_queue.append(update)

        return Response({
            "message": "Progress update added",
            "data": update
        }, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        operation_summary="Stream progress updates using SSE",
        manual_parameters=[],
        responses={200: 'Streaming SSE'}
    )
    def list(self, request, *args, **kwargs):
        def event_stream():
            stream_id = str(uuid.uuid4())
            active_streams[stream_id] = {
                'connected': True,
                'last_index': len(progress_queue) - 1
            }

            yield f"data: {json.dumps({'type': 'connected', 'stream_id': stream_id})}\n\n"

            try:
                while True:
                    current = active_streams.get(stream_id)
                    if not current:
                        break

                    last_index = current['last_index']
                    if len(progress_queue) > last_index + 1:
                        for i in range(last_index + 1, len(progress_queue)):
                            item = progress_queue[i]
                            yield f"data: {json.dumps({'type': 'progress', 'data': item})}\n\n"
                        current['last_index'] = len(progress_queue) - 1
                    else:
                        yield f"data: {json.dumps({'type': 'ping'})}\n\n"

                    time.sleep(1)

            except GeneratorExit:
                pass
            finally:
                active_streams.pop(stream_id, None)
                yield f"data: {json.dumps({'type': 'close', 'message': 'Stream ended'})}\n\n"

        response = StreamingHttpResponse(event_stream(), content_type='text/event-stream')
        response['Cache-Control'] = 'no-cache'
        response['Access-Control-Allow-Origin'] = '*'
        return response

progress_streams = {}    

def stream_progress_view(request):
    def event_stream():
        stream_id = str(uuid.uuid4())
        progress_streams[stream_id] = {
            'connected': True,
            'last_progress_index': len(progress_queue) - 1 if progress_queue else -1
        }
        print(f"[PROGRESS] Stream started: {stream_id}")
        yield f"data: {json.dumps({'type': 'connected', 'message': 'Progress stream started', 'stream_id': stream_id})}\n\n"

        try:
            for _ in range(1200):  # 10 minutes with 0.5s sleep
                if stream_id not in progress_streams:
                    break
                current_stream = progress_streams[stream_id]
                last_index = current_stream['last_progress_index']

                if len(progress_queue) > last_index + 1:
                    for i in range(last_index + 1, len(progress_queue)):
                        progress_data = progress_queue[i]
                        print(f"[PROGRESS] Sending: {progress_data}")
                        yield f"data: {json.dumps({'type': 'progress', 'data': progress_data})}\n\n"
                    progress_streams[stream_id]['last_progress_index'] = len(progress_queue) - 1

                time.sleep(0.5)
        except Exception as e:
            print(f"[PROGRESS] Stream error: {e}")
        finally:
            progress_streams.pop(stream_id, None)
            print(f"[PROGRESS] Stream closed: {stream_id}")
            yield f"data: {json.dumps({'type': 'close', 'message': 'Progress stream ended'})}\n\n"

    response = StreamingHttpResponse(event_stream(), content_type='text/event-stream; charset=utf-8')
    response['Cache-Control'] = 'no-cache'
    response['Access-Control-Allow-Origin'] = '*'
    response['Access-Control-Allow-Headers'] = 'Cache-Control, Accept, Content-Type'
    response['Access-Control-Allow-Methods'] = 'GET, OPTIONS'
    return response
  
def stream_page(request):
    """
    Serve the training progress HTML page
    GET /stream-progress/
    """
    from django.shortcuts import render
    return render(request, 'progress.html')




progress_queue = deque(maxlen=1000)
active_streams = {}

class TestingProgressViewset(viewsets.ViewSet):
    """
    Handles training progress updates and Server-Sent Events (SSE) streaming
    """

    @swagger_auto_schema(
        operation_summary="Push training progress update",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["job_id", "progress", "status"],
            properties={
                "job_id": openapi.Schema(type=openapi.TYPE_STRING, description="Job UUID"),
                "progress": openapi.Schema(type=openapi.TYPE_NUMBER, description="Progress percentage"),
                "status": openapi.Schema(type=openapi.TYPE_STRING, description="Status of the job"),
            },
        ),
        responses={200: openapi.Response(description="Progress update added")}
    )
    def create(self, request):
        job_id = request.data.get("job_id")
        progress = request.data.get("progress")
        status_msg = request.data.get("status")

        if not job_id or progress is None or not status_msg:
            return Response(
                {"message": "job_id, progress and status are required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        update = {
            "id": str(uuid.uuid4()),
            "job_id": job_id,
            "progress": progress,
            "status": status_msg,
            "timestamp": time.time()
        }
        progress_queue.append(update)

        return Response({
            "message": "Progress update added",
            "data": update
        }, status=status.HTTP_200_OK)

progress_streams = {}    

def stream_test_progress_view(request):
    def event_stream():
        stream_id = str(uuid.uuid4())
        progress_streams[stream_id] = {
            'connected': True,
            'last_progress_index': len(progress_queue) - 1 if progress_queue else -1
        }
        print(f"[PROGRESS] Stream started: {stream_id}")
        yield f"data: {json.dumps({'type': 'connected', 'message': 'Progress stream started', 'stream_id': stream_id})}\n\n"

        try:
            for _ in range(1200):  # 10 minutes with 0.5s sleep
                if stream_id not in progress_streams:
                    break
                current_stream = progress_streams[stream_id]
                last_index = current_stream['last_progress_index']

                if len(progress_queue) > last_index + 1:
                    for i in range(last_index + 1, len(progress_queue)):
                        progress_data = progress_queue[i]
                        print(f"[PROGRESS] Sending: {progress_data}")
                        yield f"data: {json.dumps({'type': 'progress', 'data': progress_data})}\n\n"
                    progress_streams[stream_id]['last_progress_index'] = len(progress_queue) - 1

                time.sleep(0.5)
        except Exception as e:
            print(f"[PROGRESS] Stream error: {e}")
        finally:
            progress_streams.pop(stream_id, None)
            print(f"[PROGRESS] Stream closed: {stream_id}")
            yield f"data: {json.dumps({'type': 'close', 'message': 'Progress stream ended'})}\n\n"

    response = StreamingHttpResponse(event_stream(), content_type='text/event-stream; charset=utf-8')
    response['Cache-Control'] = 'no-cache'
    response['Access-Control-Allow-Origin'] = '*'
    response['Access-Control-Allow-Headers'] = 'Cache-Control, Accept, Content-Type'
    response['Access-Control-Allow-Methods'] = 'GET, OPTIONS'
    return response



