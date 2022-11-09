"""
Module for DataCop and Macie Stack :)
"""
from aws_cdk import RemovalPolicy, Fn
from aws_cdk import (
    Stack,
    App,
    Duration,
    aws_lambda as _lambda,
    aws_logs as logs,
    aws_events as events,
    aws_events_targets as event_targets,
    aws_stepfunctions as sfn,
    aws_stepfunctions_tasks as sfn_tasks,
    aws_s3 as s3,
)
from aws_cdk.aws_logs import RetentionDays

STEP_FUNCTION_NAME = "DCMacieStepFunction"


class MacieStack(Stack):
    # pylint: disable=too-many-locals
    """
    This class contains the logic for deploying the following resources:
    - S3 Buckets
    - KMS Key
    - SNS Topic
    """

    def __init__(self, scope: App, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        # Import S3 Bucket
        s3_bucket_arn = Fn.import_value("S3BucketArn")
        s3_bucket = s3.Bucket.from_bucket_arn(
            self, id="DataCopS3Bucket", bucket_arn=s3_bucket_arn
        )

        # Import Lambda Function
        dc_lambda_function_arn = Fn.import_value("LambdaFunctionArn")
        dc_lambda = _lambda.Function.from_function_arn(
            self, id="DataCopLambda", function_arn=dc_lambda_function_arn
        )

        # Create Step Function w/ states
        sfn_log_group = logs.LogGroup(
            self,
            "DataCopMacieSfnLogGroup",
            log_group_name="DataCopMacieSfnLogGroup",
            removal_policy=RemovalPolicy.DESTROY,
            retention=RetentionDays.INFINITE,
        )
        send_error_report = sfn_tasks.LambdaInvoke(
            self,
            "send_error_report",
            lambda_function=dc_lambda,
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
            lambda_function=dc_lambda,
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
            lambda_function=dc_lambda,
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
            lambda_function=dc_lambda,
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
            lambda_function=dc_lambda,
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
            STEP_FUNCTION_NAME,
            state_machine_name=STEP_FUNCTION_NAME,
            definition=definition,
            logs=sfn.LogOptions(
                destination=sfn_log_group,
                include_execution_data=True,
                level=sfn.LogLevel.ALL,
            ),
            timeout=Duration.minutes(5),
        )

        # Creating EventBridge Resources
        macie_event_pattern = events.EventPattern(
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
            "DataCopMacieEventRule",
            enabled=True,
            event_pattern=macie_event_pattern,
            targets=[sfn_target],
        )
