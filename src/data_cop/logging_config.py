"""
Module for configuring logger for entire lambda function.
"""
import logging


class LoggerConfig:
    """
    This class is responsible for configuring project level logging.
    """

    def __init__(self):
        pass

    @staticmethod
    def configure(class_name):
        logger = logging.getLogger(class_name)
        handler = logging.StreamHandler()
        handler.setLevel(logging.DEBUG)
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)

        return logger
