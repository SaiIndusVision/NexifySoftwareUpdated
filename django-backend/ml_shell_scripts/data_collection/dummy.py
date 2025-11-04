import logging
import argparse

from offline_camera import OfflineCamera
from huateng_camera import HuaTengCamera
from image_collector import ImageCollector


def main(args: dict) -> None:
    collector = ImageCollector(args)

    # Set up Offline Camera
    image_folder = r"D:\AIVOLVED-JOB\v-anot\nexify-local\backend-local\NexifySoftware\django-backend\ml_shell_scripts\data_collection\offline_images"
    camera = OfflineCamera(image_folder, delay=1.0)

    # Set up HuaTeng Camera
    # camera = HuaTengCamera(args.camera_config_file)
    
    camera.set_image_callback(collector.send)


if __name__ == "__main__":
    logger = logging.getLogger(__name__)
    logger.info("Started!")

    parser = argparse.ArgumentParser()

    parser.add_argument("--sku_id", type=str, required=True)
    parser.add_argument("--version_id", type=str, required=True)
    parser.add_argument("--tag_name", type=str, required=True)
    parser.add_argument("--end_point_url", type=str, required=True)
    parser.add_argument("--streaming_endpoint_url", type=str, required=True)
    parser.add_argument("--camera_config_file", type=str, required=True, help="Path to folder containing images")

    args = parser.parse_args()
    main(args)
