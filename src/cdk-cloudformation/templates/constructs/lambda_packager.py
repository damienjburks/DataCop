import os
import logging

from os.path import basename
from zipfile import ZipFile

ZIP_FILE_NAME = "./data_knight_lambda.zip"

class LambdaPackager:
    """
    Class that packages entire lambda file
    """

    def __init__(self, path):
        self.path = path
        self.logging = logging.getLogger(__name__)

    def package(self):
        self.logging.debug("Creating lambda for Data Knight...")
        with ZipFile(ZIP_FILE_NAME, 'w') as zip_file:
            # Iterate over all the files in directory
            for folder_name, sub_folders, file_names in os.walk(self.path):
                for file_name in file_names:
                    # create complete filepath of file in directory
                    file_path = os.path.join(folder_name, file_name)
                    # Add file to zip
                    zip_file.write(file_path, basename(file_path))
                    self.logging.debug("File writing now: %s", file_name)
        self.logging.debug("Created lambda successfully!")

        return ZIP_FILE_NAME