"""
Module for deploying all CDK core resources.
"""
import os
from aws_cdk import RemovalPolicy
from aws_cdk import (
    Stack,
    App,
    Duration,
    aws_lambda as _lambda,
    aws_logs as logs,
    aws_s3 as s3,
    aws_iam as iam,
    aws_kms as kms,
    aws_s3_notifications as s3_notifications,
)
from aws_cdk.aws_iam import Effect

from .constructs.lambda_packager import LambdaPackager


class DataCopCoreStack(Stack):
    """
    This class contains the logic for deploying the following resources:
    - S3 Buckets
    - Lambda Function for DataCop
    """

    def __init__(self, scope: App, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        # Package & create Lambda Function
        lambda_package_dir = LambdaPackager("../lambda_func").package()
        dk_lambda = _lambda.Function(
            self,
            "DataCopLambda",
            function_name="DataCopLambda",
            runtime=_lambda.Runtime.PYTHON_3_9,
            timeout=Duration.minutes(10),
            handler="handler.lambda_handler",
            log_retention=logs.RetentionDays.INFINITE,
            code=_lambda.Code.from_asset(path=lambda_package_dir),
        )

        # Create KMS key and add policy for macie
        kms_key = kms.Key(
            self,
            "DataCopKMSKey",
            alias=os.environ["KMS_KEY_ALIAS"],
            enable_key_rotation=True,
            removal_policy=RemovalPolicy.DESTROY,
            pending_window=Duration.days(7),
        )
        kms_key.add_to_resource_policy(
            iam.PolicyStatement(
                principals=[iam.ServicePrincipal("macie.amazonaws.com")],
                actions=["kms:GenerateDataKey*", "kms:Encrypt"],
                resources=["*"],
            )
        )
        kms_key.add_to_resource_policy(
            iam.PolicyStatement(
                principals=[iam.ServicePrincipal("lambda.amazonaws.com")],
                actions=["kms:GenerateDataKey*", "kms:Encrypt", "kms:Decrypt"],
                resources=["*"],
            )
        )

        dk_lambda.role.add_managed_policy(
            iam.ManagedPolicy(
                self,
                "DataCopS3PolicyInline",
                document=iam.PolicyDocument(
                    statements=[
                        iam.PolicyStatement(
                            sid="AllowPutActions",
                            effect=Effect.ALLOW,
                            actions=[
                                "s3:PutBucketPolicy",
                                "s3:PutBucketAcl",
                                "s3:PutPublicAccessBlock",
                                "s3:PutBucketPublicAccessBlock",
                            ],
                            resources=["arn:aws:s3:::*"],
                        ),
                        iam.PolicyStatement(
                            sid="AllowDecryptionOfS3Objects",
                            effect=Effect.ALLOW,
                            actions=["kms:Decrypt"],
                            resources=[kms_key.key_arn],
                        ),
                        iam.PolicyStatement(
                            sid="SendEmailsUsingSES",
                            effect=Effect.ALLOW,
                            actions=["ses:SendEmail"],
                            resources=["*"],
                        )
                    ]
                ),
            )
        )

        # Create S3 Bucket w/ S3 Managed Encryption
        s3_bucket = s3.Bucket(
            self,
            "DataCopS3Bucket",
            bucket_name=os.environ["S3_BUCKET_NAME"],
            auto_delete_objects=True,
            removal_policy=RemovalPolicy.DESTROY,
            encryption=s3.BucketEncryption.S3_MANAGED,
        )
        s3_bucket.policy.document.creation_stack.clear()  # Clearing bucket policy

        # Adding event notifications to bucket
        s3_bucket.add_event_notification(
            s3.EventType.OBJECT_CREATED, s3_notifications.LambdaDestination(dk_lambda)
        )

        # Creating bucket policy & attaching it to s3 bucket
        default_bucket_policy = iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=["s3:*"],
            principals=[iam.AnyPrincipal()],  # Clean this up in the future
            resources=[s3_bucket.bucket_arn, f"{s3_bucket.bucket_arn}/*"],
        )
        s3_bucket.add_to_resource_policy(default_bucket_policy)
