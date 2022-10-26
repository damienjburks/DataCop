"""
Module for deploying core CDK resources with Trend Micro's Cloud One
File Storage.
"""
from aws_cdk import RemovalPolicy, Fn
from aws_cdk.aws_logs import RetentionDays
from aws_cdk import (
    Stack,
    App,
    Duration,
    aws_lambda as _lambda,
    aws_logs as logs,
    aws_stepfunctions as sfn,
    aws_stepfunctions_tasks as sfn_tasks,
    aws_sns as sns,
    aws_sns_subscriptions as sns_subs,
)

STEP_FUNCTION_NAME = "DCFssStepFunction"


class FileStorageStack(Stack):
    # pylint: disable=too-many-locals

    def __init__(self, scope: App, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        # Import Lambda Function
        dc_lambda_function_arn = Fn.import_value("LambdaFunctionArn")
        dc_lambda = _lambda.Function.from_function_arn(
            self, id="DataCopLambda", function_arn=dc_lambda_function_arn
        )

        # Subscribe lambda to SNS topic
        fss_topic_arn = Fn.import_value("FssSnsTopicArn")
        sns_topic = sns.Topic.from_topic_arn(
            self, id="FssTopicArn", topic_arn=fss_topic_arn
        )
        sns_topic.add_subscription(sns_subs.LambdaSubscription(dc_lambda))

        # Create Step Function w/ states
        sfn_log_group = logs.LogGroup(
            self,
            "DataCopFssSfnLogGroup",
            log_group_name="DataCopFssSfnLogGroup",
            removal_policy=RemovalPolicy.DESTROY,
            retention=RetentionDays.INFINITE,
        )

        # Step Function States
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

        copy_object_to_quarantine_bucket = sfn_tasks.LambdaInvoke(
            self,
            "copy_object_to_quarantine_bucket",
            lambda_function=dc_lambda,
            payload=sfn.TaskInput.from_object(
                {
                    "state_name": "copy_object_to_quarantine_bucket",
                    "report.$": "$.Payload",
                }
            ),
            result_path="$.copy_object_to_quarantine_bucket",
            output_path="$.copy_object_to_quarantine_bucket",
        ).add_catch(handler=send_error_report, result_path="$.exception")

        remove_object_from_parent_bucket = sfn_tasks.LambdaInvoke(
            self,
            "remove_object_from_parent_bucket",
            lambda_function=dc_lambda,
            payload=sfn.TaskInput.from_object(
                {
                    "state_name": "remove_object_from_parent_bucket",
                    "report.$": "$.Payload",
                }
            ),
            result_path="$.remove_object_from_parent_bucket",
            output_path="$.remove_object_from_parent_bucket",
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

        definition = check_bucket_status.next(
            previously_blocked.when(
                sfn.Condition.string_equals("$.Payload.is_blocked", "true"),
                block_s3_bucket,
            )
            .afterwards(include_error_handlers=True)
            .next(
                copy_object_to_quarantine_bucket.next(
                    remove_object_from_parent_bucket.next(send_report)
                )
            )
        )

        sfn.StateMachine(
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
