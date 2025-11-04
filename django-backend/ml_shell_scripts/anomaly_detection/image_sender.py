import base64

import cv2
import requests


class ImageSender:
    def __init__(
        self, sku_id: int, version_id: int, end_point_url: str, dir_timestamp: str
    ):
        self.sku_id = sku_id
        self.version_id = version_id
        self.end_point_url = end_point_url
        self.dir_timestamp = dir_timestamp

    def send(self, result: dict, format: str = "png") -> bool:
        try:
            format = format.lower()
            valid_formats = ["png", "jpg", "jpeg", "webp", "bmp"]
            if format not in valid_formats:
                print(f"Unsupported image format '{format}'. Falling back to 'png'.")
                format = "png"

            # Encode image
            success, buffer = cv2.imencode(f".{format}", result["result_image"])
            if not success:
                print("Failed to encode image.")
                return False
            byte_data = buffer.tobytes()

            # Base64 encode and add MIME type
            mime_type = f"image/{'jpeg' if format == 'jpg' else format}"
            base64_image = base64.b64encode(byte_data).decode("utf-8")
            encoded_image = f"data:{mime_type};base64,{base64_image}"

            payload = {
                "sku_id": self.sku_id,
                "version_id": self.version_id,
                "folder_name": self.dir_timestamp,
                "image": encoded_image,
                "meta_data": {
                    "label_id": result["label_id"],
                    "predicted_label": result["predicted_label"],
                    "predicted_score": result["predicted_score"],
                },
            }

            response = requests.post(self.end_point_url, json=payload)

            if response.status_code in {200, 201}:
                print("Image sent successfully.")
                return True
            else:
                print(
                    f"Failed to send image. Status code: {response.status_code}, Response: {response.text}"
                )
                return False

        except Exception as e:
            print(f"Exception while sending image: {str(e)}")
            return False
