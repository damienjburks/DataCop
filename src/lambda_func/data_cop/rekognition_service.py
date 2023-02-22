"""
Module for calling Rekognition APIs.
"""

from data_cop.logging_config import LoggerConfig


class RekognitionService:
    """
    This class is responsible for interacting with AWS Rekognition APIs.
    """

    def __init__(self, boto_session):
        self.rekognition_client = boto_session.client("rekognition")
        self.logger = LoggerConfig().configure(type(self).__name__)

    def detect_image_text(self, target_bucket_name, target_obj_path):
        """
        Function that will detect text within an image.
        """

        response = self.rekognition_client.detect_text(
            Image={
                "S3Object": {
                    "Bucket": target_bucket_name,
                    "Name": target_obj_path,
                }
            }
        )
        self.logger.info("Detected text for image: %s", response)

        image_text = ""
        for txt_detections in response["TextDetections"]:
            if txt_detections["Type"] == "WORD":
                image_text += txt_detections["DetectedText"] + "\n"

        return image_text

    def detect_video_text(
        self, target_bucket_name, target_obj_path, sns_topic_arn, role_arn
    ):
        """
        Starts the processing job to detect the text
        within the video itself
        """

        response = self.rekognition_client.start_text_detection(
            Video={
                "S3Object": {
                    "Bucket": target_bucket_name,
                    "Name": target_obj_path,
                }
            },
            NotificationChannel={"SNSTopicArn": sns_topic_arn, "RoleArn": role_arn},
        )

        self.logger.info("Started text detection: %s", response["JobId"])

        return response["JobId"]

    def get_video_text_job(self, job_id):
        """
        Get the text from the video job that was
        submitted
        """

        response = self.rekognition_client.get_text_detection(
            JobId=job_id,
        )

        self.logger.info("Get text detection response: %s", response)

        video_text = ""
        for txt_detections in response["TextDetections"]:
            if txt_detections["Type"] == "WORD":
                video_text += txt_detections["DetectedText"] + "\n"

        return video_text
