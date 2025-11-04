# logger_config.py
import os
import logging
from datetime import datetime

LOG_FORMAT = (
    "[%(asctime)s] "
    "[%(name)-15s] "
    "[%(levelname)-7s] "
    "[%(thread)d] "
    "[%(filename)-12s] "
    "[%(lineno)-4d] "
    "[%(message)s]"
)

def setup_logger(log_dir : str = './logs') -> None:
    os.makedirs(log_dir,exist_ok=True)

    logging_level = logging.DEBUG   # Or INFO in production
    logger = logging.getLogger()
    logger.setLevel(logging_level)

    if not logger.handlers:
        formatter = logging.Formatter(LOG_FORMAT, "%Y-%m-%d %H:%M:%S")

        ch = logging.StreamHandler()
        ch.setLevel(logging_level)
        ch.setFormatter(formatter)
        logger.addHandler(ch)

        filename = os.path.join(log_dir, "{}.log".format(datetime.now().strftime("%Y-%m-%d_%H-%M-%S")))
        fh = logging.FileHandler(filename)
        fh.setLevel(logging_level)
        fh.setFormatter(formatter)
        logger.addHandler(fh)