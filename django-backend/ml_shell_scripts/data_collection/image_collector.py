import base64
import logging

import cv2
import requests
import numpy as np

logger = logging.getLogger(__name__)


class ImageCollector:
    def __init__(
            self, sku_id: int, version_id: int, end_point_url: str, streaming_endpoint_url: str, tag_name: str
        ):
        self.sku_id = sku_id
        self.version_id = version_id
        self.end_point_url = end_point_url
        self.streaming_endpoint_url = streaming_endpoint_url
        self.tag_name = tag_name

    def send(self, image: np.ndarray, format: str = "png") -> bool:
        try:
            format = format.lower()
            valid_formats = ["png", "jpg", "jpeg", "webp"]
            if format not in valid_formats:
                logger.warning(f"Unsupported image format '{format}'. Falling back to 'png'.")
                format = "png"

            # Encode image
            success, buffer = cv2.imencode(f".{format}", image)
            if not success:
                logger.warning("Failed to encode image.")
                return False

            byte_data = buffer.tobytes()

            # Base64 encode and add MIME type
            mime_type = f"image/{'jpeg' if format == 'jpg' else format}"
            base64_image = base64.b64encode(byte_data).decode("utf-8")
            encoded_image = f"data:{mime_type};base64,{base64_image}"

            payload = {
                "image": encoded_image,
                "sku_id": self.sku_id,
                "version_id": self.version_id,
                "tags": self.tag_name,
            }

            streaming_payload = {
                "image": encoded_image
            }
            
            stream_response = requests.post(self.streaming_endpoint_url, json=streaming_payload)
            response = requests.post(self.end_point_url, json=payload)

            if response.status_code in {200, 201}:
                logger.info("Image sent successfully.")
                return True
            else:
                logger.warning(
                    f"Failed to send image. Status code: {response.status_code}, Response: {response.text}"
                )
                return False

        except Exception as e:
            logger.error(f"Exception while sending image: {str(e)}")
            return False
