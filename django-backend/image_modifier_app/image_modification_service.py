import base64
from typing import Dict, Any, List

import numpy as np
from io import BytesIO
from PIL import Image
from torchvision.transforms import v2
from django.core.files.uploadedfile import UploadedFile

from .list_modifiers import AUGMENTATIONS, PREPROCESSING, ALL_TRANSFORMS

class ImageUtils:
    @staticmethod
    def file_to_pil_image(image_file: UploadedFile) -> Image.Image:
        image = Image.open(image_file)
        if image.mode == "RGBA":
            image = image.convert("RGB")
        return image


    @staticmethod
    def pil_to_base64(image: Image.Image) -> str:
        buffered = BytesIO()
        image.save(buffered, format="PNG")
        return base64.b64encode(buffered.getvalue()).decode("utf-8")


class ImageModificationService:
    @classmethod
    def list_supported_augmentations(cls) -> Dict[str, Any]:
        return {
            aug_type: {
                "description": config.get("description", ""),
                "dual_mode": config.get("dual_mode", False),
                "parameters": config.get("parameters", []),
            }
            for aug_type, config in AUGMENTATIONS.items()
        }

    @classmethod
    def list_supported_preprocessors(cls) -> Dict[str, Any]:
        return {
            preprocessor_type: {
                "description": config.get("description", ""),
                "dual_mode": config.get("dual_mode", False),
                "parameters": config.get("parameters", []),
            }
            for preprocessor_type, config in PREPROCESSING.items()
        }

    @classmethod
    def apply_dual_mode_transform(cls, image, transform_name, params, positive=True):

        transform_config = ALL_TRANSFORMS[transform_name]
        transform_class = transform_config["transform_class"]

        try:
            if transform_name == "brightness":
                brightness_val = params.get("brightness", 0.3)
                # For dual mode: positive = brighter, negative = darker
                if positive:
                    transform = transform_class(
                        brightness=(1 + brightness_val, 1 + brightness_val)
                    )
                else:
                    transform = transform_class(
                        brightness=(1 - brightness_val, 1 - brightness_val)
                    )

            elif transform_name == "contrast":
                contrast_val = params.get("contrast", 0.3)
                # For dual mode: positive = higher contrast, negative = lower contrast
                if positive:
                    transform = transform_class(
                        contrast=(1 + contrast_val, 1 + contrast_val)
                    )
                else:
                    transform = transform_class(
                        contrast=(1 - contrast_val, 1 - contrast_val)
                    )

            elif transform_name == "hue":
                hue_val = params.get("hue", 0.2)
                # For dual mode: positive and negative hue shifts
                if positive:
                    transform = transform_class(hue=(hue_val, hue_val))
                else:
                    transform = transform_class(hue=(-hue_val, -hue_val))

            elif transform_name == "saturation":
                saturation_val = params.get("saturation", 0.3)
                # For dual mode: positive = more saturated, negative = less saturated
                if positive:
                    transform = transform_class(
                        saturation=(1 + saturation_val, 1 + saturation_val)
                    )
                else:
                    transform = transform_class(
                        saturation=(1 - saturation_val, 1 - saturation_val)
                    )

            elif transform_name == "rotation":
                degrees=params.get("degrees", 0)
                # For dual_mode: postive = clockwise rotation, negative = anticlockwise rotation
                if positive:
                    degrees = (degrees, degrees)
                    transform = transform_class(degrees=degrees)
                else:
                    degrees = (-degrees, -degrees)
                    transform = transform_class(degrees=degrees)

            elif transform_name == "affine_shear":
                shear_x = params.get("shear_x", 10)
                shear_y = params.get("shear_y", 10)
                # For dual mode: positive and negative shear
                if positive:
                    shear = [shear_x, shear_x, shear_y, shear_y]
                    transform = transform_class(degrees=0, shear=shear)
                else:
                    shear = [-shear_x, -shear_x, -shear_y, -shear_y]
                    transform = transform_class(degrees=0, shear=shear)

            else:
                return cls.apply_single_mode_transform(image, transform_name, params)

            return transform(image)

        except Exception as e:
            print(f"Error applying {transform_name}: {str(e)}")
            return image

    @classmethod
    def apply_single_mode_transform(cls, image, transform_name, params):
        transform_config = ALL_TRANSFORMS[transform_name]
        transform_class = transform_config["transform_class"]

        try:
            if transform_name == "horizontal_flip":
                transform = transform_class(p=params.get("p", 1.0))

            elif transform_name == "vertical_flip":
                transform = transform_class(p=params.get("p", 1.0))

            elif transform_name == "grayscale":
                transform = transform_class(p=params.get("p", 1.0))

            elif transform_name == "noise":
                transform = transform_class(
                    mean=params.get("mean", 0.0),
                    std=params.get("std", 0.1)
                )

            elif transform_name == "blur":
                kernel_size = params.get("kernel_size", 5)
                if kernel_size % 2 == 0:
                    kernel_size += 1
                transform = transform_class(
                    kernel_size=kernel_size,
                    sigma=params.get("sigma", 1.0)
                )

            elif transform_name == "affine_scale":
                transform = transform_class(degrees=0, scale=(params.get("scale", 1.0),)*2)

            elif transform_name == "resize_maintain_aspect":
                transform = transform_class(size=params.get("size", 224))

            elif transform_name == "resize_distort":
                transform = transform_class(
                    size=(params.get("height", 224), params.get("width", 224))
                )

            elif transform_name == "invert":
                transform = transform_class(p=params.get("p", 1.0))

            elif transform_name == "sharpen":
                transform = transform_class(
                    sharpness_factor=params.get("sharpness_factor", 1.0),
                    p=params.get("p", 1.0)
                )

            return transform(image)

        except Exception as e:
            print(f"Error applying {transform_name}: {str(e)}")
            return image

    @classmethod
    def apply_single_modifier(
        cls, image_file: UploadedFile, modifier_type: str, parameters: Dict = None
    ) -> np.ndarray:
        image = ImageUtils.file_to_pil_image(image_file)

        if parameters.get("dual_mode", True):
            transformed_image_pos = cls.apply_dual_mode_transform(
                image, modifier_type, parameters, positive=True
            )
            transformed_image_neg = cls.apply_dual_mode_transform(
                image, modifier_type, parameters, positive=False
            )

            original_base64 = ImageUtils.pil_to_base64(image)
            pos_base64 = ImageUtils.pil_to_base64(transformed_image_pos)
            neg_base64 = ImageUtils.pil_to_base64(transformed_image_neg)

            return original_base64, pos_base64, neg_base64
        else:
            transformed_image = cls.apply_single_mode_transform(
                image, modifier_type, parameters
            )
            original_base64 = ImageUtils.pil_to_base64(image)
            transformed_base64 = ImageUtils.pil_to_base64(transformed_image)
            return original_base64, transformed_base64

class ImageModificationPipeline:

    @staticmethod
    def create_transform_instance(transform_name, params):
        transform_config = ALL_TRANSFORMS[transform_name]
        transform_class = transform_config["transform_class"]

        if transform_name == "horizontal_flip":
            p = params.get("p", 1.0)
            return transform_class(p=p)

        elif transform_name == "vertical_flip":
            p = params.get("p", 1.0)
            return transform_class(p=p)

        elif transform_name == "grayscale":
            p = params.get("p", 1.0)
            return transform_class(p=p)

        elif transform_name == "rotation":
            degrees = params.get("degrees", 1.0)
            return transform_class(degrees=degrees)

        elif transform_name == "brightness":
            brightness_val = params.get("brightness", 0.3)
            brightness_range = (max(0, 1 - brightness_val), 1 + brightness_val)
            return transform_class(brightness=brightness_range)

        elif transform_name == "contrast":
            contrast_val = params.get("contrast", 0.3)
            contrast_range = (max(0, 1 - contrast_val), 1 + contrast_val)
            return transform_class(contrast=contrast_range)

        elif transform_name == "hue":
            hue_val = params.get("hue", 0.2)
            hue_range = (-hue_val, hue_val)
            return transform_class(hue=hue_range)

        elif transform_name == "saturation":
            saturation_val = params.get("saturation", 0.3)
            saturation_range = (max(0, 1 - saturation_val), 1 + saturation_val)
            return transform_class(saturation=saturation_range)

        elif transform_name == "noise":
            transform_class = transform_config
            mean = params.get("mean", 0.0)
            std = params.get("std", 0.1)
            return transform_class(mean=mean, std=std)

        elif transform_name == "blur":
            kernel_size = params.get("kernel_size", 5)
            if kernel_size % 2 == 0:
                kernel_size += 1
            sigma = params.get("sigma", 1.0)
            return transform_class(kernel_size=kernel_size, sigma=sigma)

        elif transform_name == "affine_scale":
            scale = max(1.0, params.get("scale", 1.0))
            return transform_class(degrees=0, scale=(1.0, scale))

        elif transform_name == "resize_maintain_aspect":
            size = params.get("size", 224)
            return transform_class(size=size)

        elif transform_name == "resize_distort":
            width = params.get("width", 224)
            height = params.get("height", 224)
            return transform_class(size=(height, width))

        elif transform_name == "invert":
            p = params.get("p", 1.0)
            return transform_class(p=p)

        elif transform_name == "sharpen":
            sharpness_factor = params.get("sharpness_factor", 1.0)
            p = params.get("p", 1.0)
            return transform_class(sharpness_factor=sharpness_factor, p=p)

        elif transform_name == "affine_shear":
            shear_x = params.get("shear_x", 10)
            shear_y = params.get("shear_y", 10)
            shear = [-shear_x, shear_x, -shear_y, shear_y]
            return transform_class(degrees=0, shear=shear)

        else:
            return
    
    @classmethod
    def build_pipeline_modifier(cls, modifications_config: List[Dict]) -> v2.Compose:
        transform_list = []

        for mod_config in modifications_config:
            modifier_type = mod_config.get("modifier_type")
            if not mod_config:
                raise ValueError("Each augmentation must have a 'modifier_type' field")

            parameters = mod_config.get("parameters", {})
            transform = cls.create_transform_instance(modifier_type, parameters)
            transform_list.append(transform)

        return v2.Compose(transform_list)

    @classmethod
    def apply_multiple_modifiers(cls, image_file, modifications_config: List[Dict]):
        image = ImageUtils.file_to_pil_image(image_file)
        transform = cls.build_pipeline_modifier(modifications_config) 

        transformed_image = transform(image)
        original_base64 = ImageUtils.pil_to_base64(image)
        transformed_base64 = ImageUtils.pil_to_base64(transformed_image)
        return original_base64, transformed_base64
