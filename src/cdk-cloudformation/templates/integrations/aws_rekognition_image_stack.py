"""
Module for deploying necessary infrastructure to fully leverage AWS Rekognition
to parse image text.
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
    aws_events as events,
    aws_events_targets as event_targets,
    aws_s3 as s3,
)

STEP_FUNCTION_NAME = "DCRekognitionImageFunction"


class RekognitionImageStack(Stack):
    """
    This class contains the logic for deploying the following resources: (WIP)
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

        # Create SNS Topic and subscribe it to the lambda function
        sns_topic = sns.Topic(
            self, "DCRekognitionImageTopic", display_name="DCRekognitionImageTopic"
        )
        sns_topic.add_subscription(sns_subs.LambdaSubscription(dc_lambda))

        # Create Step Function w/ states
        sfn_log_group = logs.LogGroup(
            self,
            "DCRekognitionImageSfnLogGroup",
            log_group_name="DCRekognitionImageSfnLogGroup",
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

        detect_text_in_image = sfn_tasks.LambdaInvoke(
            self,
            "detect_text_in_image",
            lambda_function=dc_lambda,
            payload=sfn.TaskInput.from_object(
                {
                    "state_name": "detect_text_in_image",
                    "report.$": "$",
                },
            ),
            result_path="$.detect_text_in_image",
            output_path="$.detect_text_in_image",
        ).add_catch(handler=send_error_report, result_path="$.exception")

        has_sensitive_text = sfn.Choice(self, "Has Sensitive Text?")
        sensitive_text_found = sfn.Pass(self, "Sensitive Text Found")
        no_sensitive_text_found = sfn.Pass(self, "No Sensitive Text Found")

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

        definition = detect_text_in_image.next(
            has_sensitive_text.when(
                sfn.Condition.boolean_equals("$.Payload.has_sensitive_text", False),
                no_sensitive_text_found,
            ).otherwise(
                sensitive_text_found.next(copy_object_to_quarantine_bucket)
                .next(remove_object_from_parent_bucket)
                .next(send_report)
            )
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
        rekognition_event_pattern = events.EventPattern(
            source=["aws.s3"],
            detail={
                "eventSource": ["s3.amazonaws.com"],
                "eventName": ["PutObject"],
                "requestParameters": {
                    "key": [  # Filter on these file types
                        {"suffix": ".png"},
                        {"suffix": ".jpg"},
                        {"suffix": ".jpeg"},
                    ],
                },
            },
        )
        sfn_target = event_targets.SfnStateMachine(dc_state_machine)
        events.Rule(
            self,
            "DCRekognitionImageEventRule",
            rule_name="DCRekognitionImageEventRule",
            enabled=True,
            event_pattern=rekognition_event_pattern,
            targets=[sfn_target],
        )
