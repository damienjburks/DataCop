"""
Module to configure the boto session based on environment.
"""
import boto3


class BotoConfig:
    def __init__(self):
        pass

    def get_session(self):
        return boto3.Session()