"""
Module to configure the boto session based on environment.
"""
import boto3


class BotoConfig:
    """
    This class is responsible for creating a session for boto3.
    This could be customized to the user's specification depending on what they're using.
    """

    def __init__(self):
        pass

    @staticmethod
    def get_session():
        return boto3.Session()
