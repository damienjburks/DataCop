"""
Module that contains logic to package the lambda function.
"""
import logging
import shutil

FILE_NAME = "data_cop_lambda"
ZIP_FILE_NAME = f"./{FILE_NAME}.zip"


class LambdaPackager:
    """
    Class that packages entire lambda file
    """

    def __init__(self, path):
        self.path = path
        self.logging = logging.getLogger(__name__)

    def package(self):
        """
        Packages the lambda function
        """
        self.logging.debug("Creating lambda for Data Cop...")
        shutil.make_archive(FILE_NAME, "zip", self.path)
        self.logging.debug("Created lambda successfully!")

        return ZIP_FILE_NAME
