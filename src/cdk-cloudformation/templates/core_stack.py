"""
Module for deploying all CDK core resources.
"""
import os
from aws_cdk import RemovalPolicy, CfnParameter
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
    aws_stepfunctions as sfn,
    aws_stepfunctions_tasks as sfn_tasks,
    aws_sns as sns,
)
from aws_cdk.aws_iam import Effect
from aws_cdk.aws_logs import RetentionDays
from aws_cdk.aws_sns_subscriptions import EmailSubscription

from .constructs.lambda_packager import LambdaPackager


class DataCopCoreStack(Stack):
    """
    This class contains the logic for deploying the following resources:
    - S3 Buckets
    - Lambda Function for DataCop
    - Step Function & corresponding Log Group
    - KMS Key
    """

    def __init__(self, scope: App, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        # Export Environment Variables to the CFT
        BUCKET_NAME = CfnParameter(
            self,
            "bucketName",
            type="String",
            description="The name of the Amazon S3 bucket where uploaded files will be stored.",
        ).value_as_string
        KMS_KEY_ALIAS = CfnParameter(
            self,
            "kmsKeyAlias",
            type="String",
            description="The name of the Amazon KMS key alias.",
        ).value_as_string
        SUB_EMAIL_ADDRESS = CfnParameter(
            self,
            "snsEmailAddress",
            type="String",
            description="The email address that is subscription to the SNS topic.",
        ).value_as_string

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
            alias=KMS_KEY_ALIAS,
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
                    ]
                ),
            )
        )

        # Create S3 Bucket w/ S3 Managed Encryption
        s3_bucket = s3.Bucket(
            self,
            "DataCopS3Bucket",
            bucket_name=BUCKET_NAME,
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

        # Create Step Function w/ states
        sfn_log_group = logs.LogGroup(
            self,
            "DataCopSfnLogGroup",
            log_group_name="DataCopSfnLogGroup",
            removal_policy=RemovalPolicy.DESTROY,
            retention=RetentionDays.INFINITE,
        )
        send_error_report = sfn_tasks.LambdaInvoke(
            self, "send_error_report", lambda_function=dk_lambda
        )

        determine_severity = sfn_tasks.LambdaInvoke(
            self, "determine_severity", lambda_function=dk_lambda
        )
        block_bucket_boolean = sfn.Choice(self, "Block Bucket?")

        block_s3_bucket = sfn_tasks.LambdaInvoke(
            self, "block_s3_bucket", lambda_function=dk_lambda
        ).add_catch(handler=send_error_report, result_path="$.exception")

        send_report = sfn_tasks.LambdaInvoke(
            self,
            "send_report",
            lambda_function=dk_lambda,
        )
        definition = determine_severity.next(
            block_bucket_boolean.when(
                sfn.Condition.string_equals("$.block_bucket", "true"),
                block_s3_bucket.next(send_report),
            )
        )
        sfn.StateMachine(
            self,
            "DataCopStepFunction",
            state_machine_name="DataCop",
            definition=definition,
            logs=sfn.LogOptions(
                destination=sfn_log_group,
                include_execution_data=True,
                level=sfn.LogLevel.ALL,
            ),
            timeout=Duration.minutes(5),
        )

        # SNS Topic Creation
        datacop_topic = sns.Topic(self, "DataCopTopic")
        datacop_topic.add_subscription(
            EmailSubscription(SUB_EMAIL_ADDRESS)
        )