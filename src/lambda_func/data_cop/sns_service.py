"""
Module that contains logic for
publishing messages to the SNS topic
"""

from data_cop.logging_config import LoggerConfig


class SnsService:
    """
    This class contains logic for interacting with
    SNS APIs for AWS.
    """

    def __init__(self, boto_session):
        self.sns_client = boto_session.client("sns")
        self.logger = LoggerConfig().configure(type(self).__name__)
        self.account_id = (
            boto_session.client("sts").get_caller_identity().get("Account")
        )
        self.topic_arn = self.get_topic_arn()

    def get_topic_arn(self):
        topic_arn = None
        response = self.sns_client.list_topics()

        for topic in response["Topics"]:
            if "datacop" in topic["TopicArn"].lower():
                topic_arn = topic["TopicArn"]
                self.logger.debug("Obtained topic ARN: %s", topic_arn)
                break

        return topic_arn

    def send_email(self, subject, message):
        """
        This function will publish a message to the topic
        """
        message_id = self.sns_client.publish(
            TopicArn=self.topic_arn,
            Message=message,
            Subject=subject,
        )["MessageId"]

        self.logger.debug(
            "Message has been published to topic successfully: %s", message_id
        )

        return message_id
