"""
Module for calling Comprehend APIs.
"""

from data_cop.logging_config import LoggerConfig


class ComprehendService:
    """
    This class is responsible for interacting with AWS Comprehend APIs.
    """

    def __init__(self, boto_session):
        self.comprehend_client = boto_session.client("comprehend")
        self.logger = LoggerConfig().configure(type(self).__name__)

    def detect_pii(self, text):
        """
        Detect PII from the supplied text
        """
        response = self.comprehend_client.detect_pii_entities(
            Text=text, LanguageCode="en"
        )

        if response["Entities"]:
            return True
        return False
