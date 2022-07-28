"""
Module for interacting with SSM
"""

from data_cop.logging_config import LoggerConfig


class SSMService:
    """
    This class is responsible for interacting with AWS SSM APIs.
    """

    def __init__(self, boto_session):
        self.ssm_client = boto_session.client("ssm")
        self.logger = LoggerConfig().configure(type(self).__name__)

    def get_severity(self):
        """
        Obtain the severity from the SSM Parameter: DataCopSeverity
        """
        response = self.ssm_client.get_parameter(
            Name="DataCopSeverity",
        )
        severity = response["Parameter"]["Value"]
        self.logger.debug("Obtained the severity from SSM: %s", severity)
        self.logger.debug(response)

        return severity
