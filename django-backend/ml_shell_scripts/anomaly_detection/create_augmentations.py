import torch
from torchvision.transforms import v2

class GaussianNoise:
    def __init__(self, mean=0.0, std=0.1):
        self.mean = mean
        self.std = std
    
    def __call__(self, img):
        to_tensor = v2.ToTensor()
        to_pil = v2.ToPILImage()

        tensor_img = to_tensor(img)
        noise = torch.randn(tensor_img.size()) * self.std + self.mean
        noisy_tensor = tensor_img + noise

        clamped_tensor = torch.clamp(noisy_tensor, 0, 1)
        return to_pil(clamped_tensor)

AUGMENTATIONS = {
    "horizontal_flip": {
        "description": "Flips the image horizontally (left-right).",
        "transform_class": v2.RandomHorizontalFlip,
        "dual_mode": False,
        "parameters": {
            "p": {"min": 0.0, "max": 1.0, "default": 1.0, "step": 0.1}
        },
    },
    "vertical_flip": {
        "description": "Flips the image vertically (top-bottom).",
        "transform_class": v2.RandomVerticalFlip,
        "dual_mode": False,
        "parameters": {
            "p": {"min": 0.0, "max": 1.0, "default": 1.0, "step": 0.1}
        },
    },
    "grayscale": {
        "description": "Converts image to grayscale with specified probability.",
        "transform_class": v2.RandomGrayscale,
        "dual_mode": False,
        "parameters": {
            "p": {"min": 0.0, "max": 1.0, "default": 1.0, "step": 0.1}
        },
    },
    "rotation": {
        "description": "Rotates the image by a specific angle.",
        "transform_class": v2.RandomRotation,
        "dual_mode": True,
        "parameters": {
            "degrees": {"min": -180, "max": 180, "default": 0, "step": 15}
        },
    },
    # "noise": {
    #     "description": "Adds Gaussian noise to the image.",
    #     "transform_class": GaussianNoise,
    #     "dual_mode": False,
    #     "parameters": {
    #         "mean": {"min": -0.5, "max": 0.5, "default": 0.0, "step": 0.1},
    #         "std": {"min": 0.0, "max": 1.0, "default": 0.1, "step": 0.05}
    #     },
    # },
    "blur": {
        "description": "Applies Gaussian blur to the image.",
        "transform_class": v2.GaussianBlur,
        "dual_mode": False,
        "parameters": {
            "kernel_size": {"min": 3, "max": 15, "default": 5, "step": 2},
            "sigma": {"min": 0.1, "max": 5.0, "default": 1.0, "step": 0.1}
        },
    },
    "brightness": {
        "description": "Adjusts the brightness of the image. Shows both brighter and darker versions.",
        "transform_class": v2.ColorJitter,
        "dual_mode": True,
        "parameters": {
            "brightness": {"min": 0.0, "max": 1.0, "default": 0.3, "step": 0.1}
        },
    },
    "contrast": {
        "description": "Adjusts the contrast of the image. Shows both higher and lower contrast versions.",
        "transform_class": v2.ColorJitter,
        "dual_mode": True,
        "parameters": {
            "contrast": {"min": 0.0, "max": 1.0, "default": 0.3, "step": 0.1}
        },
    },
    "hue": {
        "description": "Shifts hue of the image. Shows both positive and negative hue shifts.",
        "transform_class": v2.ColorJitter,
        "dual_mode": True,
        "parameters": {
            "hue": {"min": 0.0, "max": 0.5, "default": 0.2, "step": 0.1}
        },
    },
    "saturation": {
        "description": "Adjusts saturation of the image. Shows both higher and lower saturation versions.",
        "transform_class": v2.ColorJitter,
        "dual_mode": True,
        "parameters": {
            "saturation": {"min": 0.0, "max": 1.0, "default": 0.3, "step": 0.1}
        },
    },
    "affine_scale": {
        "description": "Applies affine scaling transformation.",
        "transform_class": v2.RandomAffine,
        "dual_mode": False,
        "parameters": {
            "scale": {"min": 1.0, "max": 2.0, "default": 1.0, "step": 0.1}
        },
    },
    "affine_shear": {
        "description": "Applies affine shear transformation. Shows both positive and negative shear.",
        "transform_class": v2.RandomAffine,
        "dual_mode": True,
        "parameters": {
            "shear_x": {"min": 0, "max": 30, "default": 10, "step": 1},
            "shear_y": {"min": 0, "max": 30, "default": 10, "step": 1}
        },
    }
}


PREPROCESSING = {
    "resize_maintain_aspect": {
        "description": "Resizes image while maintaining aspect ratio.",
        "transform_class": v2.Resize,
        "dual_mode": False,
        "parameters": {
            "size": {"min": 64, "max": 1024, "default": 224, "step": 1}
        },
    },
    "resize_distort": {
        "description": "Resizes image without maintaining aspect ratio.",
        "transform_class": v2.Resize,
        "dual_mode": False,
        "parameters": {
            "width": {"min": 64, "max": 1024, "default": 224, "step": 1},
            "height": {"min": 64, "max": 1024, "default": 224, "step": 1}
        },
    },
    "invert": {
        "description": "Inverts the colors of the image.",
        "transform_class": v2.RandomInvert,
        "dual_mode": False,
        "parameters": {
            "p": {"min": 0.0, "max": 1.0, "default": 1.0, "step": 0.1}
        },
    },
    "sharpen": {
        "description": "Sharpens the image.",
        "transform_class": v2.RandomAdjustSharpness,
        "dual_mode": False,
        "parameters": {
            "sharpness_factor": {"min": 1.0, "max": 3.0, "default": 1.0, "step": 0.1},
            "p": {"min": 0.0, "max": 1.0, "default": 1.0, "step": 0.1}
        },
    },
}

ALL_TRANSFORMS = AUGMENTATIONS | PREPROCESSING

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
    def build_pipeline_modifier(cls, modifications_config: list[dict]) -> v2.Compose:
        transform_list = []

        for mod_config in modifications_config:
            modifier_type = mod_config.get("modifier_type")
            if not mod_config:
                raise ValueError("Each augmentation must have a 'modifier_type' field")

            parameters = mod_config.get("parameters", {})
            transform = cls.create_transform_instance(modifier_type, parameters)
            transform_list.append(transform)

        return v2.Compose(transform_list)