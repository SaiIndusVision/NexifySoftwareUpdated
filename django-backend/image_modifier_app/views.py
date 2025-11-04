import json

from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.decorators import action

from .image_modification_service import ImageModificationService, ImageModificationPipeline
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

# class ImageModificationVisualizerAPI(viewsets.ViewSet):
#     # parser_classes = [MultiPartParser, FormParser]

#     @action(detail=False, methods=["get"], url_path="list_transform")
#     def list_transform(self, request):
#         """
#         GET api/image_modifier/list_transform
#         """
#         try:
#             augmentations = ImageModificationService.list_supported_augmentations()

#             return Response(
#                 {
#                     "status": status.HTTP_200_OK,
#                     "augmentations": augmentations,
#                     "total_count": len(augmentations),
#                 }
#             )

#         except Exception as e:
#             return Response(
#                 {
#                     "status": status.HTTP_500_INTERNAL_SERVER_ERROR,
#                     "error": f"Failed to get augmentations: {str(e)}",
#                 },
#                 status=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             )

#     @action(detail=False, methods=["get"], url_path="list_preprocessor")
#     def list_preprocessor(self, request):
#         """
#         GET api/image_modifier/list_preprocessor
#         """
#         try:
#             preprocessors = ImageModificationService.list_supported_preprocessors()

#             return Response(
#                 {
#                     "status": status.HTTP_200_OK,
#                     "preprocessors": preprocessors,
#                     "total_count": len(preprocessors),
#                 }
#             )

#         except Exception as e:
#             return Response(
#                 {
#                     "status": status.HTTP_500_INTERNAL_SERVER_ERROR,
#                     "error": f"Failed to get preprocessors: {str(e)}",
#                 },
#                 status=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             )

#     @action(detail=False, methods=["post"], url_path="single_modifier")
#     def single_transform(self, request):
#         """
#         POST api/image_modifier/single_transform
#         """
#         try:
#             image_file = request.FILES.get("image")
#             if not image_file:
#                 return Response(
#                     {
#                         "status": status.HTTP_400_BAD_REQUEST,
#                         "error": "No image provided.",
#                     },
#                     status=status.HTTP_400_BAD_REQUEST,
#                 )

#             modifier_type = request.POST.get("modifier_type")
#             if not modifier_type:
#                 return Response(
#                     {
#                         "status": status.HTTP_400_BAD_REQUEST,
#                         "error": "modifier_type type is required.",
#                     },
#                     status=status.HTTP_400_BAD_REQUEST,
#                 )

#             parameters = {}
#             if "parameters" in request.POST:
#                 try:
#                     parameters = json.loads(request.POST.get("parameters"))
#                 except json.JSONDecodeError:
#                     return Response(
#                         {
#                             "status": status.HTTP_400_BAD_REQUEST,
#                             "error": "Invalid JSON in parameters",
#                         },
#                         status=status.HTTP_400_BAD_REQUEST,
#                     )

#             base_64_imgs = (
#                 ImageModificationService.apply_single_modifier(
#                     image_file, modifier_type, parameters
#                 )
#             )

#             if len(base_64_imgs) == 2:
#                 return Response(
#                     {
#                         "status": status.HTTP_200_OK,
#                         "modifier_type": modifier_type,
#                         "original_image": base_64_imgs[0],
#                         "transformed_image": base_64_imgs[1]
#                     },
#                     status=status.HTTP_200_OK,
#                 )
#             else:
#                 return Response(
#                     {
#                         "status": status.HTTP_200_OK,
#                         "modifier_type": modifier_type,
#                         "original_image": base_64_imgs[0],
#                         "transformed_pos_image": base_64_imgs[1],
#                         "transformed_neg_image": base_64_imgs[2]
#                     },
#                     status=status.HTTP_200_OK,
#                 )
#         except Exception as e:
#             return Response(
#                 {
#                     "status": status.HTTP_500_INTERNAL_SERVER_ERROR,
#                     "error": f"Failed to process image: {str(e)}",
#                 },
#                 status=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             )
        
#     @action(detail=False, methods=["post"], url_path="multiple_modifier")
#     def multiple_modifier(self, request):
#         """
#         POST api/image_modifier/multiple_modifier
#         """
#         try:
#             image_file = request.FILES.get("image")
#             if not image_file:
#                 return Response(
#                     {
#                         "status": status.HTTP_400_BAD_REQUEST,
#                         "error": "No image provided.",
#                     },
#                     status=status.HTTP_400_BAD_REQUEST,
#                 )

#             modifier_config = json.loads(
#                 request.POST.get("modifier_config")
#             )
#             if not modifier_config:
#                 return Response(
#                     {
#                         "status": status.HTTP_400_BAD_REQUEST,
#                         "error": "modifier_config type is required.",
#                     },
#                     status=status.HTTP_400_BAD_REQUEST,
#                 )

#             parameters = {}
#             if "parameters" in request.POST:
#                 try:
#                     parameters = json.loads(request.POST.get("parameters"))
#                 except json.JSONDecodeError:
#                     return Response(
#                         {
#                             "status": status.HTTP_400_BAD_REQUEST,
#                             "error": "Invalid JSON in parameters",
#                         },
#                         status=status.HTTP_400_BAD_REQUEST,
#                     )

#             original_b64, augmented_b64 = ImageModificationPipeline.apply_multiple_modifiers(
#                     image_file, modifier_config
#                 )

#             return Response(
#                 {
#                     "status": status.HTTP_200_OK,
#                     "modifier_config": modifier_config,
#                     "original_image": original_b64,
#                     "augmented_image": augmented_b64,
#                 },
#                 status=status.HTTP_200_OK,
#             )
#         except Exception as e:
#             return Response(
#                 {
#                     "status": status.HTTP_500_INTERNAL_SERVER_ERROR,
#                     "error": f"Failed to process image: {str(e)}",
#                 },
#                 status=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             )



class ImageModificationVisualizerAPI(viewsets.ViewSet):
    # parser_classes = [MultiPartParser, FormParser]

    @swagger_auto_schema(
        operation_summary="List supported image augmentations",
        operation_description="Retrieves a list of all supported image augmentation types.",
        responses={
            200: openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'status': openapi.Schema(type=openapi.TYPE_INTEGER, description="HTTP status code"),
                    'augmentations': openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Items(type=openapi.TYPE_STRING), description="List of augmentation names"),
                    'total_count': openapi.Schema(type=openapi.TYPE_INTEGER, description="Total number of augmentations"),
                }
            ),
            500: openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'status': openapi.Schema(type=openapi.TYPE_INTEGER, description="HTTP status code"),
                    'error': openapi.Schema(type=openapi.TYPE_STRING, description="Error message"),
                }
            ),
        }
    )
    @action(detail=False, methods=["get"], url_path="list_transform")
    def list_transform(self, request):
        """
        GET api/image_modifier/list_transform
        """
        try:
            augmentations = ImageModificationService.list_supported_augmentations()

            return Response(
                {
                    "status": status.HTTP_200_OK,
                    "augmentations": augmentations,
                    "total_count": len(augmentations),
                }
            )

        except Exception as e:
            return Response(
                {
                    "status": status.HTTP_500_INTERNAL_SERVER_ERROR,
                    "error": f"Failed to get augmentations: {str(e)}",
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @swagger_auto_schema(
        operation_summary="List supported image preprocessors",
        operation_description="Retrieves a list of all supported image preprocessor types.",
        responses={
            200: openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'status': openapi.Schema(type=openapi.TYPE_INTEGER, description="HTTP status code"),
                    'preprocessors': openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Items(type=openapi.TYPE_STRING), description="List of preprocessor names"),
                    'total_count': openapi.Schema(type=openapi.TYPE_INTEGER, description="Total number of preprocessors"),
                }
            ),
            500: openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'status': openapi.Schema(type=openapi.TYPE_INTEGER, description="HTTP status code"),
                    'error': openapi.Schema(type=openapi.TYPE_STRING, description="Error message"),
                }
            ),
        }
    )
    @action(detail=False, methods=["get"], url_path="list_preprocessor")
    def list_preprocessor(self, request):
        """
        GET api/image_modifier/list_preprocessor
        """
        try:
            preprocessors = ImageModificationService.list_supported_preprocessors()

            return Response(
                {
                    "status": status.HTTP_200_OK,
                    "preprocessors": preprocessors,
                    "total_count": len(preprocessors),
                }
            )

        except Exception as e:
            return Response(
                {
                    "status": status.HTTP_500_INTERNAL_SERVER_ERROR,
                    "error": f"Failed to get preprocessors: {str(e)}",
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @swagger_auto_schema(
        operation_summary="Apply a single image modifier",
        operation_description="Applies a single augmentation or preprocessor to an uploaded image with optional parameters.",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['image', 'modifier_type'],
            properties={
                'image': openapi.Schema(type=openapi.TYPE_FILE, description="Image file to be modified"),
                'modifier_type': openapi.Schema(type=openapi.TYPE_STRING, description="Type of modifier (augmentation or preprocessor)"),
                'parameters': openapi.Schema(type=openapi.TYPE_STRING, description="JSON string of modifier parameters", nullable=True),
            },
        ),
        responses={
            200: openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'status': openapi.Schema(type=openapi.TYPE_INTEGER, description="HTTP status code"),
                    'modifier_type': openapi.Schema(type=openapi.TYPE_STRING, description="Applied modifier type"),
                    'original_image': openapi.Schema(type=openapi.TYPE_STRING, description="Base64-encoded original image"),
                    'transformed_image': openapi.Schema(type=openapi.TYPE_STRING, description="Base64-encoded transformed image", nullable=True),
                    'transformed_pos_image': openapi.Schema(type=openapi.TYPE_STRING, description="Base64-encoded positive transformed image (if applicable)", nullable=True),
                    'transformed_neg_image': openapi.Schema(type=openapi.TYPE_STRING, description="Base64-encoded negative transformed image (if applicable)", nullable=True),
                }
            ),
            400: openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'status': openapi.Schema(type=openapi.TYPE_INTEGER, description="HTTP status code"),
                    'error': openapi.Schema(type=openapi.TYPE_STRING, description="Error message"),
                }
            ),
            500: openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'status': openapi.Schema(type=openapi.TYPE_INTEGER, description="HTTP status code"),
                    'error': openapi.Schema(type=openapi.TYPE_STRING, description="Error message"),
                }
            ),
        }
    )
    @action(detail=False, methods=["post"], url_path="single_modifier")
    def single_transform(self, request):
        """
        POST api/image_modifier/single_transform
        """
        try:
            image_file = request.FILES.get("image")
            if not image_file:
                return Response(
                    {
                        "status": status.HTTP_400_BAD_REQUEST,
                        "error": "No image provided.",
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            modifier_type = request.POST.get("modifier_type")
            if not modifier_type:
                return Response(
                    {
                        "status": status.HTTP_400_BAD_REQUEST,
                        "error": "modifier_type is required.",
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            parameters = {}
            if "parameters" in request.POST:
                try:
                    parameters = json.loads(request.POST.get("parameters"))
                except json.JSONDecodeError:
                    return Response(
                        {
                            "status": status.HTTP_400_BAD_REQUEST,
                            "error": "Invalid JSON in parameters",
                        },
                        status=status.HTTP_400_BAD_REQUEST,
                    )

            base_64_imgs = ImageModificationService.apply_single_modifier(
                image_file, modifier_type, parameters
            )

            if len(base_64_imgs) == 2:
                return Response(
                    {
                        "status": status.HTTP_200_OK,
                        "modifier_type": modifier_type,
                        "original_image": base_64_imgs[0],
                        "transformed_image": base_64_imgs[1]
                    },
                    status=status.HTTP_200_OK,
                )
            else:
                return Response(
                    {
                        "status": status.HTTP_200_OK,
                        "modifier_type": modifier_type,
                        "original_image": base_64_imgs[0],
                        "transformed_pos_image": base_64_imgs[1],
                        "transformed_neg_image": base_64_imgs[2]
                    },
                    status=status.HTTP_200_OK,
                )
        except Exception as e:
            return Response(
                {
                    "status": status.HTTP_500_INTERNAL_SERVER_ERROR,
                    "error": f"Failed to process image: {str(e)}",
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        
    @swagger_auto_schema(
        operation_summary="Apply multiple image modifiers",
        operation_description="Applies a sequence of augmentations or preprocessors to an uploaded image based on the provided configuration.",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['image', 'modifier_config'],
            properties={
                'image': openapi.Schema(type=openapi.TYPE_FILE, description="Image file to be modified"),
                'modifier_config': openapi.Schema(type=openapi.TYPE_STRING, description="JSON string defining the sequence of modifiers"),
                'parameters': openapi.Schema(type=openapi.TYPE_STRING, description="JSON string of modifier parameters", nullable=True),
            },
        ),
        responses={
            200: openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'status': openapi.Schema(type=openapi.TYPE_INTEGER, description="HTTP status code"),
                    'modifier_config': openapi.Schema(type=openapi.TYPE_OBJECT, description="Applied modifier configuration"),
                    'original_image': openapi.Schema(type=openapi.TYPE_STRING, description="Base64-encoded original image"),
                    'augmented_image': openapi.Schema(type=openapi.TYPE_STRING, description="Base64-encoded augmented image"),
                }
            ),
            400: openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'status': openapi.Schema(type=openapi.TYPE_INTEGER, description="HTTP status code"),
                    'error': openapi.Schema(type=openapi.TYPE_STRING, description="Error message"),
                }
            ),
            500: openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'status': openapi.Schema(type=openapi.TYPE_INTEGER, description="HTTP status code"),
                    'error': openapi.Schema(type=openapi.TYPE_STRING, description="Error message"),
                }
            ),
        }
    )
    @action(detail=False, methods=["post"], url_path="multiple_modifier")
    def multiple_modifier(self, request):
        """
        POST api/image_modifier/multiple_modifier
        """
        try:
            image_file = request.FILES.get("image")
            if not image_file:
                return Response(
                    {
                        "status": status.HTTP_400_BAD_REQUEST,
                        "error": "No image provided.",
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            modifier_config = json.loads(
                request.POST.get("modifier_config")
            )
            if not modifier_config:
                return Response(
                    {
                        "status": status.HTTP_400_BAD_REQUEST,
                        "error": "modifier_config is required.",
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            parameters = {}
            if "parameters" in request.POST:
                try:
                    parameters = json.loads(request.POST.get("parameters"))
                except json.JSONDecodeError:
                    return Response(
                        {
                            "status": status.HTTP_400_BAD_REQUEST,
                            "error": "Invalid JSON in parameters",
                        },
                        status=status.HTTP_400_BAD_REQUEST,
                    )

            original_b64, augmented_b64 = ImageModificationPipeline.apply_multiple_modifiers(
                image_file, modifier_config
            )

            return Response(
                {
                    "status": status.HTTP_200_OK,
                    "modifier_config": modifier_config,
                    "original_image": original_b64,
                    "augmented_image": augmented_b64,
                },
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            return Response(
                {
                    "status": status.HTTP_500_INTERNAL_SERVER_ERROR,
                    "error": f"Failed to process image: {str(e)}",
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )