"""
Module for deploying all CDK core resources.
"""
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
    aws_cloudtrail as cloudtrail,
    aws_events as events,
    aws_events_targets as event_targets,
    aws_stepfunctions as sfn,
    aws_stepfunctions_tasks as sfn_tasks,
    aws_sns as sns,
    aws_ssm as ssm,
)
from aws_cdk.aws_iam import Effect
from aws_cdk.aws_logs import RetentionDays
from aws_cdk.aws_sns_subscriptions import EmailSubscription

from .constructs.lambda_packager import LambdaPackager


class DataCopCoreStack(Stack):
    # pylint: disable=too-many-locals
    """
    This class contains the logic for deploying the following resources:
    - S3 Buckets
    - Lambda Function for DataCop
    - Step Function & corresponding Log Group
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

        # Configure Parameter store for
        # DataCop Lambda Attributes
        ssm.StringParameter(
            self,
            "DataCopSeverity",
            parameter_name="DataCopSeverity",
            description="This value will be used to block S3 buckets.",
            string_value="HIGH",
        )

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

        dk_lambda.role.add_managed_policy(
            iam.ManagedPolicy(
                self,
                "DataCopS3PolicyInline",
                document=iam.PolicyDocument(
                    statements=[
                        iam.PolicyStatement(
                            sid="AllowPutAndGetActions",
                            effect=Effect.ALLOW,
                            actions=["s3:Put*", "s3:Get*", "s3:List*"],
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
                    ]
                ),
            )
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

        # Create Step Function w/ states
        sfn_log_group = logs.LogGroup(
            self,
            "DataCopSfnLogGroup",
            log_group_name="DataCopSfnLogGroup",
            removal_policy=RemovalPolicy.DESTROY,
            retention=RetentionDays.INFINITE,
        )
        send_error_report = sfn_tasks.LambdaInvoke(
            self,
            "send_error_report",
            lambda_function=dk_lambda,
            payload=sfn.TaskInput.from_object(
                {
                    "state_name": "send_error_report",
                    "report.$": "$.exception",
                    "execution_id.$": "$$.Execution.Id",
                }
            ),
        )

        determine_severity = sfn_tasks.LambdaInvoke(
            self,
            "determine_severity",
            lambda_function=dk_lambda,
            payload=sfn.TaskInput.from_object(
                {
                    "state_name": "determine_severity",
                    "Payload.$": "$",
                }
            ),
            result_path="$.determine_severity",
            output_path="$.determine_severity",
        ).add_catch(handler=send_error_report, result_path="$.exception")

        block_bucket_boolean = sfn.Choice(self, "Block Bucket?")

        check_bucket_status = sfn_tasks.LambdaInvoke(
            self,
            "check_bucket_status",
            lambda_function=dk_lambda,
            payload=sfn.TaskInput.from_object(
                {
                    "state_name": "check_bucket_status",
                    "report.$": "$.Payload",
                }
            ),
            result_path="$.check_bucket_status",
            output_path="$.check_bucket_status",
        )

        previously_blocked = sfn.Choice(self, "Previously Blocked?")

        block_s3_bucket = sfn_tasks.LambdaInvoke(
            self,
            "block_s3_bucket",
            lambda_function=dk_lambda,
            payload=sfn.TaskInput.from_object(
                {
                    "state_name": "block_s3_bucket",
                    "report.$": "$.Payload",
                }
            ),
            result_path="$.block_s3_bucket",
            output_path="$.block_s3_bucket",
        ).add_catch(handler=send_error_report, result_path="$.exception")

        send_report = sfn_tasks.LambdaInvoke(
            self,
            "send_report",
            lambda_function=dk_lambda,
            payload=sfn.TaskInput.from_object(
                {
                    "state_name": "send_report",
                    "report.$": "$.Payload",
                    "execution_id.$": "$$.Execution.Id",
                }
            ),
        )
        ignore_bucket_state = sfn.Pass(self, "Ignore Bucket")
        definition = determine_severity.next(
            block_bucket_boolean.when(
                sfn.Condition.is_not_null("$.Payload"),
                check_bucket_status.next(
                    previously_blocked.when(
                        sfn.Condition.string_equals("$.Payload.is_blocked", "true"),
                        ignore_bucket_state,
                    ).otherwise(block_s3_bucket.next(send_report))
                ),
            ).otherwise(ignore_bucket_state)
        )
        dc_state_machine = sfn.StateMachine(
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

        # Creating EventBridge Resources
        dc_event_pattern = events.EventPattern(
            source=["aws.s3"],
            detail={
                "eventSource": ["s3.amazonaws.com"],
                "eventName": ["PutObject"],
                "requestParameters": {"bucketName": [s3_bucket.bucket_name]},
            },
        )
        sfn_target = event_targets.SfnStateMachine(dc_state_machine)
        events.Rule(
            self,
            "DataCopEventRule",
            enabled=True,
            event_pattern=dc_event_pattern,
            targets=[sfn_target],
        )
