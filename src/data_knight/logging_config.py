"""
Module for configuring logger for entire lambda function.
"""
import logging


class LoggerConfig:

    def __init__(self):
        pass

    def configure_logger(self, class_name):
        logger = logging.getLogger(class_name)
        handler = logging.StreamHandler()
        handler.setLevel(logging.DEBUG)
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)

        return logger