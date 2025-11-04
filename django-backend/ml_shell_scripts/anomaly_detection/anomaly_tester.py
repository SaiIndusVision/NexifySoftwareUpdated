import cv2
import torch
import numpy as np
from PIL import Image
from torchvision import transforms
from anomalib.models import Padim, Patchcore, ReverseDistillation

class AnomalyTester:
    def __init__(self, model_name: str, ckpt_path: str):
        self.model_name = model_name.lower()
        self.model = self._load_model(self.model_name, ckpt_path)
        self.model.eval()
        self.transform = transforms.ToTensor()

    def _load_model(self, model_name, ckpt_path):
        model_name = model_name.lower()
        model_cls_map = {
            "padim": Padim,
            "anomalydetection1": Padim,
            "patchcore": Patchcore,
            "reversedistillation": ReverseDistillation
        }

        if model_name not in model_cls_map:
            raise ValueError(f"Unsupported model: {model_name}")

        model = model_cls_map[model_name]()
        ckpt = torch.load(ckpt_path, map_location=torch.device('cpu'))

        if model_name == "patchcore":
            state_dict = ckpt["model"].state_dict()
        else:
            state_dict = ckpt["state_dict"]

        model.load_state_dict(state_dict)
        return model

    def _prepare_image(self, image_path):
        image = Image.open(image_path).convert("RGB")
        return self.transform(image).unsqueeze(0), np.array(image)

    def _post_process(self, item, original_image):
        mask = item.pred_mask.cpu().numpy().squeeze().astype(np.uint8) * 255
        anomaly_map = item.anomaly_map.cpu().numpy().squeeze()
        pred_label = item.pred_label.item()
        print(pred_label)
        pred_score = item.pred_score.item()

        original_image = cv2.cvtColor(original_image, cv2.COLOR_RGB2BGR)
        original_image = cv2.resize(original_image, (anomaly_map.shape[1], anomaly_map.shape[0]))

        mask_colored = cv2.cvtColor(mask, cv2.COLOR_GRAY2BGR)
        anomaly_map_norm = cv2.normalize(anomaly_map, None, 0, 255, cv2.NORM_MINMAX)
        anomaly_map_colored = cv2.applyColorMap(anomaly_map_norm.astype(np.uint8), cv2.COLORMAP_JET)

        overlay = cv2.addWeighted(original_image, 0.6, anomaly_map_colored, 0.4, 0)
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        cv2.drawContours(overlay, contours, -1, (0, 0, 255), 2)
        result_image = cv2.hconcat([original_image,overlay])

        return {
            "result_image": result_image,
            "predicted_label": pred_label,
            "predicted_score": pred_score
        }

    def infer(self, image_path: str) -> dict:
        input_tensor, original_image = self._prepare_image(image_path)
        with torch.no_grad():
            item = self.model(input_tensor)
        return self._post_process(item, original_image)
