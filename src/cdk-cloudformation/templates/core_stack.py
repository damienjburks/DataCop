"""
Module for deploying CDK core resources for DataCop.
"""
from os import environ
from aws_cdk import RemovalPolicy, CfnParameter, CfnOutput
from aws_cdk import (
    Stack,
    App,
    Duration,
    aws_lambda as _lambda,
    aws_logs as logs,
    aws_s3 as s3,
    aws_iam as iam,
    aws_kms as kms,
    aws_cloudtrail as cloudtrail,
    aws_sns as sns,
    aws_ssm as ssm,
)
from aws_cdk.aws_iam import Effect
from aws_cdk.aws_sns_subscriptions import EmailSubscription

from .constructs.lambda_packager import LambdaPackager


class CoreStack(Stack):
    # pylint: disable=too-many-locals
    """
    This class contains the logic for deploying the following resources:
    - S3 Buckets
    - KMS Key
    - SNS Topic
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

        # SNS Topic Creation
        datacop_topic = sns.Topic(self, "DataCopTopic", display_name="AWS DataCop")
        datacop_topic.add_subscription(EmailSubscription(SUB_EMAIL_ADDRESS))

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

        # Create KMS key
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

        # Create S3 Bucket w/ S3 Managed Encryption
        s3_bucket = s3.Bucket(
            self,
            "DataCopBucket",
            bucket_name=BUCKET_NAME,
            auto_delete_objects=True,
            removal_policy=RemovalPolicy.DESTROY,
            encryption=s3.BucketEncryption.S3_MANAGED,
        )
        s3_bucket.policy.document.creation_stack.clear()  # Clearing bucket policy

        if environ.get("QUARANTINE_S3_BUCKET_NAME") is not None:
            # Create Quarantine S3 Bucket w/ S3 Managed Encryption
            quarantine_s3_bucket = s3.Bucket(
                self,
                "DataCopQuarantineBucket",
                bucket_name=environ.get("QUARANTINE_S3_BUCKET_NAME"),
                auto_delete_objects=True,
                removal_policy=RemovalPolicy.DESTROY,
                encryption=s3.BucketEncryption.S3_MANAGED,
            )
            quarantine_s3_bucket.policy.document.creation_stack.clear()  # Clearing bucket policy

        # Lambda Function Permissions
        dk_lambda.role.add_managed_policy(
            iam.ManagedPolicy(
                self,
                "DataCopLambdaPolicyInline",
                document=iam.PolicyDocument(
                    statements=[
                        iam.PolicyStatement(
                            sid="AllowPutAndGetActions",
                            effect=Effect.ALLOW,
                            actions=["s3:Put*", "s3:Get*", "s3:List*", "s3:Delete*"],
                            resources=["arn:aws:s3:::*"],
                        ),
                        iam.PolicyStatement(
                            sid="AllowReadSSMParams",
                            effect=Effect.ALLOW,
                            actions=[
                                "ssm:DescribeParameter",
                                "ssm:GetParameter",
                                "ssm:GetParameterHistory",
                            ],
                            resources=["*"],
                        ),
                        iam.PolicyStatement(
                            sid="AllowDecryptionOfS3Objects",
                            effect=Effect.ALLOW,
                            actions=["kms:Decrypt"],
                            resources=[kms_key.key_arn],
                        ),
                        iam.PolicyStatement(
                            sid="AllowSnsPolicy",
                            effect=Effect.ALLOW,
                            actions=["sns:Publish", "sns:ListTopics"],
                            resources=["*"],
                        ),
                        iam.PolicyStatement(
                            sid="AllowSfnInteractions",
                            effect=Effect.ALLOW,
                            actions=[
                                "states:ListStateMachines",
                                "states:StartExecution",
                            ],
                            resources=["*"],
                        ),
                        iam.PolicyStatement(
                            sid="AllowRekognitionInteractions",
                            effect=Effect.ALLOW,
                            actions=[
                                "rekognition:DetectText",
                                "rekognition:StartTextDetection",
                                "rekognition:GetTextDetection",
                            ],
                            resources=["*"],
                        ),
                        iam.PolicyStatement(
                            sid="AllowComprehendInteractions",
                            effect=Effect.ALLOW,
                            actions=["comprehend:DetectPiiEntities"],
                            resources=["*"],
                        ),
                    ]
                ),
            )
        )
        dk_lambda.add_permission(
            "AllowInvokeViaSns",
            principal=iam.ServicePrincipal("sns.amazonaws.com"),
            action="lambda:InvokeFunction",
        )

        # Creating bucket policy & attaching it to s3 bucket
        default_bucket_policy = iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=["s3:*"],
            principals=[iam.AnyPrincipal()],  # Clean this up in the future
            resources=[s3_bucket.bucket_arn, f"{s3_bucket.bucket_arn}/*"],
        )
        s3_bucket.add_to_resource_policy(default_bucket_policy)

        # Creating CloudTrail w/ event selector
        # These CT events will trigger upon write commits only
        dc_trail = cloudtrail.Trail(
            self,
            "DataCopCloudTrail",
            include_global_service_events=False,
            is_multi_region_trail=False,
        )
        s3_event_selector = cloudtrail.S3EventSelector(bucket=s3_bucket)
        dc_trail.add_s3_event_selector(
            [s3_event_selector],
            include_management_events=False,
            read_write_type=cloudtrail.ReadWriteType.WRITE_ONLY,
        )

        # SNS Topic Service Role
        datacop_sns_topic_role = iam.Role(
            self,
            "DataCopSnsSvcRole",
            role_name="DCSnsServiceRole",
            assumed_by=iam.ServicePrincipal("rekognition.amazonaws.com"),
        )
        datacop_sns_topic_role.add_managed_policy(
            iam.ManagedPolicy(
                self,
                "DCSnsTopicAllowPolicy",
                document=iam.PolicyDocument(
                    statements=[
                        iam.PolicyStatement(
                            sid="AllowSnsPolicy",
                            effect=Effect.ALLOW,
                            actions=["sns:Publish", "sns:ListTopics"],
                            resources=["*"],
                        )
                    ],
                ),
            )
        )

        # Configure Parameter store for certain attributes
        ssm.StringParameter(
            self,
            "DataCopSeverity",
            parameter_name="DataCopSeverity",
            description="This value will be used to block S3 buckets.",
            string_value=environ.get("DATACOP_SEVERITY"),
        )
        ssm.StringParameter(
            self,
            "DCSnsServiceRole",
            parameter_name="DCSnsServiceRole",
            description="This value will store the DC SNS service role ARN.",
            string_value=datacop_sns_topic_role.role_arn,
        )
        if environ.get("QUARANTINE_S3_BUCKET_NAME") is not None:
            ssm.StringParameter(
                self,
                "DataCopQuarantineBucketSSM",
                parameter_name="DataCopQuarantineBucket",
                description="This is the s3 bucket necessary for the Quarantine Bucket.",
                string_value=environ.get("QUARANTINE_S3_BUCKET_NAME"),
            )

        # Create Outputs for this CFT
        CfnOutput(
            self,
            "DataCopLambdaFunctionArn",
            value=dk_lambda.function_arn,
            export_name="LambdaFunctionArn",
        )
        CfnOutput(
            self,
            "DataCopS3BucketArn",
            value=s3_bucket.bucket_arn,
            export_name="S3BucketArn",
        )
        if environ.get("FSS_SNS_TOPIC_ARN") is not None:
            CfnOutput(
                self,
                "DataCopFssSnsTopicArn",
                value=environ.get("FSS_SNS_TOPIC_ARN"),
                export_name="FssSnsTopicArn",
            )
