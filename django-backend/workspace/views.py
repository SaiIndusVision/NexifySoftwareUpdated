from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from django.utils import timezone
from django.contrib.auth import get_user_model
from .models import Workspace
from django.utils.timezone import localtime
from rest_framework_simplejwt.authentication import JWTAuthentication
import secrets
from datetime import timedelta
from django.utils.timezone import now, localtime
from PIL import Image, UnidentifiedImageError
from .models import TrainingImage
from users.models import CustomUser
from sku.models import SKU
User = get_user_model()

class WorkspaceViewSet(viewsets.ViewSet):
    # authentication_classes = [JWTAuthentication]
    # permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="List all workspaces (with optional created_by filter)",
        manual_parameters=[
            openapi.Parameter(
                'created_by', openapi.IN_QUERY,
                description="Filter workspaces by creator's user ID",
                type=openapi.TYPE_INTEGER
            )
        ],
        responses={200: openapi.Response(description="List of workspaces")}
    )
    def list(self, request):
        created_by_id = request.query_params.get("created_by")
        
        raw_workspaces = Workspace.objects.all().order_by('-id')

        if created_by_id:
            raw_workspaces = raw_workspaces.filter(created_by__id=created_by_id)

        workspaces = []
        for ws in raw_workspaces:
            workspaces.append({
                "id": ws.id,
                "name": ws.name,
                "created_at": localtime(ws.created_at).strftime('%Y-%m-%dT%H:%M:%S'),
                "created_by_id": ws.created_by.id if ws.created_by else None,
                "created_by_name": f"{ws.created_by.first_name} {ws.created_by.last_name}".strip() if ws.created_by else None,
                "is_activated": ws.is_activated,
                "activation_key": ws.activation_key,
                "activation_key_expiry": ws.activation_key_expiry,
                "failed_activation_attempts": ws.failed_activation_attempts,
                "field_assistant_id": ws.field_assistant.id if ws.field_assistant else None,
                "field_assistant_name": f"{ws.field_assistant.first_name} {ws.field_assistant.last_name}".strip() if ws.field_assistant else None,
                "field_assistant_phone_number": ws.field_assistant.phone_number if ws.field_assistant else None,
                "sku_count": SKU.objects.filter(workspace=ws).count() ,
                "sku_total_count":ws.sku_count,
            })

        return Response({"results": workspaces, "status": status.HTTP_200_OK}, status=status.HTTP_200_OK)


    @swagger_auto_schema(
        operation_summary="Retrieve a workspace by ID",
        responses={200: openapi.Response(description="Workspace details")}
    )
    def retrieve(self, request, pk=None):
        try:
            ws = Workspace.objects.get(id=pk)
            workspace = {
                "id": ws.id,
                "name": ws.name,
                "created_at": localtime(ws.created_at).strftime('%Y-%m-%dT%H:%M:%S'),
                "created_by_id": ws.created_by.id if ws.created_by else None,
                "created_by_name": f"{ws.created_by.first_name} {ws.created_by.last_name}".strip() if ws.created_by else None,
                "is_activated": ws.is_activated,
                "activation_key": ws.activation_key,
                "activation_key_expiry": ws.activation_key_expiry,
                "failed_activation_attempts": ws.failed_activation_attempts,
                "field_assistant_id": ws.field_assistant.id if ws.field_assistant else None,
                "field_assistant_name": f"{ws.field_assistant.first_name} {ws.field_assistant.last_name}".strip() if ws.field_assistant else None,
                "field_assistant_phone_number": ws.field_assistant.phone_number if ws.field_assistant else None,
                "sku_count": SKU.objects.filter(workspace=ws).count() ,
                "sku_total_count":ws.sku_count,
                
            }
            return Response({"results": workspace, "status": status.HTTP_200_OK}, status=status.HTTP_200_OK)
        except Workspace.DoesNotExist:
            return Response({"message": "Workspace not found", "status": status.HTTP_404_NOT_FOUND}, status=status.HTTP_404_NOT_FOUND)


    @swagger_auto_schema(
        operation_summary="Create a new workspace",
        operation_description="Creates a workspace. The `name` must be unique. `created_by` must be user ID. Only authorized users can create a workspace.",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["name", "created_by"],
            properties={
                "name": openapi.Schema(type=openapi.TYPE_STRING, description="Unique name of the workspace"),
                # "created_by": openapi.Schema(type=openapi.TYPE_INTEGER, description="User ID creating the workspace"),
            }
        ),
        responses={
            201: openapi.Response(description="Workspace created successfully"),
            400: openapi.Response(description="Validation error"),
            403: openapi.Response(description="User not authorized to create workspace"),
        }
    )
    def create(self, request):
        name = request.data.get("name")
        # created_by_id = request.data.get("created_by")

        if not name:
            return Response(
                {"message": "Both 'name' and 'created_by' are required.","status":status.HTTP_400_BAD_REQUEST},
                status=status.HTTP_400_BAD_REQUEST
            )

        if Workspace.objects.filter(name__iexact=name).exists():
            return Response(
                {"message": "Workspace name must be unique", "status": status.HTTP_400_BAD_REQUEST},
                status=status.HTTP_400_BAD_REQUEST
            )

        # try:
        #     creator = User.objects.get(pk=created_by_id)
        # except User.DoesNotExist:
        #     return Response(
        #         {"message": "Invalid creator user ID.","status":status.HTTP_400_BAD_REQUEST},
        #         status=status.HTTP_400_BAD_REQUEST
        #     )

        # if not creator.is_authorized:
        #     return Response(
        #         {"message": "User is not authorized to create a workspace.","status":status.HTTP_400_BAD_REQUEST},
        #         status=status.HTTP_403_FORBIDDEN
        #     )

        workspace = Workspace.objects.create(
            name=name,
            created_at=timezone.now()
        )

        return Response({
            "message": "Workspace created successfully",
            "workspace": {
                "id": workspace.id,
                "name": workspace.name,
                "created_at": localtime(workspace.created_at).strftime('%Y-%m-%dT%H:%M:%S'),
                "is_activated": workspace.is_activated
            },
            "status": status.HTTP_201_CREATED
        }, status=status.HTTP_201_CREATED)



class WorkspaceActivationViewSet(viewsets.ViewSet):

    @swagger_auto_schema(
        operation_summary="Generate activation key for a workspace",
        operation_description="Provide workspace ID and assistant ID to generate activation key (valid for 30 mins).",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["workspace_id", "field_assistant"],
            properties={
                "workspace_id": openapi.Schema(type=openapi.TYPE_INTEGER, description="ID of the workspace"),
                "field_assistant": openapi.Schema(type=openapi.TYPE_INTEGER, description="ID of the field assistant (CustomUser)"),
            }
        ),
        responses={
            200: openapi.Response(description="Activation key generated successfully"),
            400: openapi.Response(description="Validation error or workspace not found")
        }
    )
    def create(self, request):
        workspace_id = request.data.get("workspace_id")
        # assistant_id = request.data.get("field_assistant")

        if not workspace_id :
            return Response({"message": "workspace_id and field_assistant ID are required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            workspace = Workspace.objects.get(id=workspace_id)
        except Workspace.DoesNotExist:
            return Response({"message": "Workspace not found"}, status=status.HTTP_400_BAD_REQUEST)

        # try:
        #     assistant = CustomUser.objects.get(id=assistant_id)
        # except CustomUser.DoesNotExist:
        #     return Response({"message": "Field assistant with this ID not found"}, status=status.HTTP_400_BAD_REQUEST)

        # Generate activation key and expiry
        activation_key = secrets.token_urlsafe(16)
        expiry_time = timezone.now() + timedelta(minutes=30)

        # Assign and save
        workspace.activation_key = activation_key
        workspace.activation_key_expiry = expiry_time
        # workspace.field_assistant = assistant
        workspace.save()

        return Response({
            "message": "Activation key generated successfully",
            "workspace_id": workspace.id,
            "activation_key": activation_key,
            "activation_key_expiry": localtime(expiry_time).strftime("%Y-%m-%dT%H:%M:%S"),
            # "field_assistant_id": assistant.id
        }, status=status.HTTP_200_OK)

        
        

class WorkspaceValidateViewSet(viewsets.ViewSet):
    """
    POST API to validate and activate a workspace using workspace_id and workspace_activate flag.
    """

    @swagger_auto_schema(
        operation_summary="Validate and Activate Workspace",
        operation_description="Activates the workspace if workspace_activate is true and conditions are met.",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["workspace_id", "workspace_activate"],
            properties={
                "workspace_id": openapi.Schema(type=openapi.TYPE_INTEGER, description="Workspace ID"),
                "workspace_activate": openapi.Schema(type=openapi.TYPE_BOOLEAN, description="Activation trigger flag")
            }
        ),
        responses={
            200: openapi.Response(description="Validation result."),
            400: openapi.Response(description="Invalid request or expired workspace."),
            404: openapi.Response(description="Workspace not found.")
        }
    )
    def create(self, request):
        workspace_id = request.data.get("workspace_id")
        workspace_activate = request.data.get("workspace_activate")

        if workspace_id is None or workspace_activate is None:
            return Response({
                "message": "'workspace_id' and 'workspace_activate' are required."
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            workspace = Workspace.objects.get(id=workspace_id)
        except Workspace.DoesNotExist:
            return Response({
                "message": "Workspace not found."
            }, status=status.HTTP_404_NOT_FOUND)

        # If already activated
        if workspace.is_activated:
            return Response({
                "workspace_validated": True,
                "message": "Workspace is already activated."
            }, status=status.HTTP_200_OK)

        # If flag is true, and expiry is valid
        if workspace_activate is True:
            # if not workspace.activation_key_expiry or workspace.activation_key_expiry < now():
            #     return Response({
            #         "workspace_validated": False,
            #         "message": "Activation window has expired."
            #     }, status=status.HTTP_200_OK)

            # Activate
            workspace.is_activated = True
            workspace.failed_activation_attempts = 0
            workspace.save()

            return Response({
                "workspace_validated": True,
                "message": "Workspace successfully activated."
            }, status=status.HTTP_200_OK)

        # If workspace_activate is False or invalid case
        return Response({
            "workspace_validated": False,
            "message": "Workspace activation flag is not set or invalid."
        }, status=status.HTTP_200_OK)

        
        
from django.db import transaction
from PIL import Image, UnidentifiedImageError
from rest_framework import viewsets, status, parsers
from rest_framework.response import Response
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
import os

class ImageUploadViewSet(viewsets.ViewSet):
    """
    Upload up to 300 training images with automatic validation.
    Skips corrupt/unreadable images to protect training pipeline.
    """
    parser_classes = [parsers.MultiPartParser]
    
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
    ALLOWED_CONTENT_TYPES = [
        'image/jpeg',
        'image/png',
        'image/gif',
        'image/webp',
    ]

    @swagger_auto_schema(
        operation_summary="Upload training images",
        operation_description="Uploads up to 300 images. Corrupted or unreadable images will be skipped.",
        manual_parameters=[
            openapi.Parameter(
                name='images',
                in_=openapi.IN_FORM,
                type=openapi.TYPE_FILE,
                required=True,
                description='Multiple images may be sent using the same field name'
            )
        ],
        responses={
            201: openapi.Response(
                description='Upload results',
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'message': openapi.Schema(type=openapi.TYPE_STRING),
                        'valid_images': openapi.Schema(type=openapi.TYPE_INTEGER),
                        'invalid_images': openapi.Schema(type=openapi.TYPE_INTEGER),
                        'skipped_files': openapi.Schema(
                            type=openapi.TYPE_ARRAY,
                            items=openapi.Schema(
                                type=openapi.TYPE_OBJECT,
                                properties={
                                    'filename': openapi.Schema(type=openapi.TYPE_STRING),
                                    'reason': openapi.Schema(type=openapi.TYPE_STRING)
                                }
                            )
                        ),
                        'warnings': openapi.Schema(type=openapi.TYPE_STRING)
                    }
                )
            ),
            400: openapi.Response(
                description='Bad request',
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'message': openapi.Schema(type=openapi.TYPE_STRING)
                    }
                )
            )
        }
    )
    @transaction.atomic
    def create(self, request):
        files = request.FILES.getlist("images")

        if not files:
            return Response(
                {"message": "No images provided."},
                status=status.HTTP_400_BAD_REQUEST
            )

        if len(files) > 300:
            return Response(
                {"message": "You can upload a maximum of 300 images."},
                status=status.HTTP_400_BAD_REQUEST
            )

        valid_count = 0
        invalid_count = 0
        failed_files = []
        valid_images = []

        for file in files:
            try:
                # Validate file size
                if file.size > self.MAX_FILE_SIZE:
                    raise ValueError(f"File size exceeds {self.MAX_FILE_SIZE/1024/1024}MB limit")

                # Validate content type
                if file.content_type not in self.ALLOWED_CONTENT_TYPES:
                    raise ValueError(f"Unsupported content type: {file.content_type}")

                # Validate image integrity
                img = Image.open(file)
                img.verify()
                
                # Rewind the file pointer after verification
                if hasattr(file, 'seekable') and file.seekable():
                    file.seek(0)
                
                valid_images.append(file)
                valid_count += 1
                
            except (UnidentifiedImageError, IOError, ValueError) as e:
                invalid_count += 1
                failed_files.append({
                    'filename': file.name,
                    'reason': str(e) if str(e) else "Invalid image file"
                })
                continue

        if valid_images:
            training_images = [
                TrainingImage(image=file) 
                for file in valid_images
            ]
            TrainingImage.objects.bulk_create(training_images)

        response_data = {
            "message": "Upload complete.",
            "valid_images": valid_count,
            "invalid_images": invalid_count,
            "skipped_files": failed_files
        }

        if any(f.size > 5*1024*1024 for f in valid_images):
            response_data["warnings"] = "Large files detected - processing may take longer"

        return Response(response_data, status=status.HTTP_201_CREATED)                     


class FielEngineerVerification(viewsets.ViewSet):

    @swagger_auto_schema(
        operation_description="Verify if the given phone number belongs to the field engineer assigned to the workspace.",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['workspace_id', 'phone_number'],
            properties={
                'workspace_id': openapi.Schema(type=openapi.TYPE_INTEGER, description='ID of the workspace'),
                'phone_number': openapi.Schema(type=openapi.TYPE_STRING, description='Phone number of the field engineer'),
            },
        ),
        responses={
            200: openapi.Response(
                description="Verification Result",
                examples={
                    "application/json": {
                        "status": True,
                        "message": "Field assistant is correctly assigned."
                    }
                }
            ),
            400: "Invalid input or data not found"
        }
    )
    def create(self, request):
        workspace_id = request.data.get("workspace_id")
        phone_number = request.data.get("phone_number")

        if not workspace_id or not phone_number:
            return Response(
                {"status": False, "message": "workspace_id and phone_number are required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            workspace = Workspace.objects.get(id=workspace_id)
        except Workspace.DoesNotExist:
            return Response(
                {"status": False, "message": "Workspace not found."},
                status=status.HTTP_404_NOT_FOUND
            )

        if not workspace.field_assistant:
            return Response(
                {"status": False, "message": "No field assistant assigned to this workspace."},
                status=status.HTTP_400_BAD_REQUEST
            )

        if workspace.field_assistant.phone_number == phone_number:
            return Response({"status": True, "message": "Field assistant is correctly assigned."})
        else:
            return Response({"status": False, "message": "Incorrect field assistant."}, status=status.HTTP_400_BAD_REQUEST)


import subprocess
import platform
from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework import status
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi


class SerialNumberViewset(viewsets.ViewSet):

    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter(
                'sudo_password',
                openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description="Sudo password (Linux only)"
            )
        ],
        operation_summary="Get device serial number",
        operation_description="Returns BIOS serial number for Windows/Linux machines."
    )
    def list(self, request):
        try:
            system_platform = platform.system()
            sudo_password = request.query_params.get("sudo_password", "")

            if system_platform == "Windows":
                result = subprocess.check_output("wmic bios get serialnumber", shell=True)
                serial = result.decode().split("\n")[1].strip()

            elif system_platform == "Linux":
                # Command with password piped into sudo
                command = f'echo {sudo_password} | sudo -S dmidecode -s system-serial-number'
                result = subprocess.check_output(command, shell=True)
                serial = result.decode().strip()

            else:
                return Response({"error": f"Unsupported OS: {system_platform}"}, status=400)

            return Response({"serial_number": serial})

        except subprocess.CalledProcessError as e:
            return Response({"error": f"Command failed: {str(e)}"}, status=500)
        except Exception as e:
            return Response({"error": str(e)}, status=500)
