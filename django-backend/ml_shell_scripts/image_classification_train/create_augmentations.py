from typing import Dict, List
from torchvision.transforms import v2

from list_modifiers import *

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