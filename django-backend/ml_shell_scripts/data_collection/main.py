import logging
import argparse

from image_collector import ImageCollector
from huateng_camera import HuaTengCamera


def main(args: dict) -> None:

    collector = ImageCollector(
        args.sku_id, args.version_id, args.end_point_url, args.tag_name
    )
    camera = HuaTengCamera(args.camera_config_file)

    camera.set_image_callback(collector.send)

    while True:
        pass

if __name__ == "__main__":
    logger = logging.getLogger(__name__)
    logger.info('Started!')

    parser = argparse.ArgumentParser()

    parser.add_argument('--sku_id', type=str, required=True)
    parser.add_argument('--version_id', type=str, required=True)
    parser.add_argument('--tag_name', type=str, required=True)
    parser.add_argument('--end_point_url', type=str, required=True)
    parser.add_argument('--camera_config_file', type=str, required=True)

    args = parser.parse_args()
    main(args)
