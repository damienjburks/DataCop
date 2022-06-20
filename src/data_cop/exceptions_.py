"""
Module for project based exceptions.
"""


class MacieLogParseError(Exception):
    """
    Custom exception handler for Macie Log parsing.
    """

    def __init__(self, file_name, message):
        self.file_name = file_name
        self.message = message
        super().__init__(self.message)


class FileParsingError(Exception):
    """
    Custom exception handler for parsing files downloaded from S3.
    """

    def __init__(self, file_name, message):
        self.file_name = file_name
        self.message = message
        super().__init__(self.message)
