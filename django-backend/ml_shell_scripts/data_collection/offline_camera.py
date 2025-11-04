import os
import time

import cv2
from typing import Callable


class OfflineCamera:
    def __init__(self, image_folder: str, delay: float = 1.0):
        self.image_folder = image_folder
        self.delay = delay
        self.callback = None

    def set_image_callback(self, callback: Callable):
        self.callback = callback
        self._start_stream()

    def _start_stream(self):
        image_files = [
            f
            for f in os.listdir(self.image_folder)
            if f.lower().endswith((".jpg", ".jpeg", ".png"))
        ]
        image_files.sort()

        if not image_files:
            raise ValueError("No image files found in the folder.")

        while True:
            for image_name in image_files:
                image_path = os.path.join(self.image_folder, image_name)
                image = cv2.imread(image_path)

                if image is not None and self.callback:
                    self.callback(image)
                else:
                    print(f"Failed to read image: {image_path}")

                time.sleep(self.delay)
