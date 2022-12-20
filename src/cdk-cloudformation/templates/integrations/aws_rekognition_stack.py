"""
Module for deploying necessary infrastructure to fully leverage AWS Rekognition.
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

STEP_FUNCTION_NAME = "DCRekognitionFunction"


class RekognitionStack(Stack):
    """
    This class contains the logic for deploying the following resources: (WIP)
    """

    def __init__(self, scope: App, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        # Import Lambda Function
        dc_lambda_function_arn = Fn.import_value("LambdaFunctionArn")
        dc_lambda = _lambda.Function.from_function_arn(
            self, id="DataCopLambda", function_arn=dc_lambda_function_arn
        )

        # Create SNS Topic and subscribe it to the lambda function
        sns_topic = sns.Topic(
            self, "DCRekognitionTopic", display_name="DCRekognitionTopic"
        )
        sns_topic.add_subscription(sns_subs.LambdaSubscription(dc_lambda))

        # Create Step Function w/ states
        sfn_log_group = logs.LogGroup(
            self,
            "DCRekognitionSfnLogGroup",
            log_group_name="DCRekognitionSfnLogGroup",
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

        check_event = sfn_tasks.LambdaInvoke(
            self,
            "check_event",
            lambda_function=dc_lambda,
            payload=sfn.TaskInput.from_object(
                {
                    "state_name": "check_event",
                    "report.$": "$.Payload",
                }
            ),
            result_path="$.check_event",
            output_path="$.check_event",
        ).add_catch(handler=send_error_report, result_path="$.exception")

        completed_job = sfn.Choice(self, "Completed Job?")

        submit_job = sfn_tasks.LambdaInvoke(
            self,
            "submit_job",
            lambda_function=dc_lambda,
            payload=sfn.TaskInput.from_object(
                {
                    "state_name": "submit_job",
                    "report.$": "$.Payload",
                }
            ),
            result_path="$.submit_job",
            output_path="$.submit_job",
        ).add_catch(handler=send_error_report, result_path="$.exception")

        block_object = sfn_tasks.LambdaInvoke(
            self,
            "block_object",
            lambda_function=dc_lambda,
            payload=sfn.TaskInput.from_object(
                {
                    "state_name": "block_object",
                    "report.$": "$.Payload",
                }
            ),
            result_path="$.block_object",
            output_path="$.block_object",
        ).add_catch(handler=send_error_report, result_path="$.exception")

        parse_and_classify_text = sfn_tasks.LambdaInvoke(
            self,
            "parse_and_classify_text",
            lambda_function=dc_lambda,
            payload=sfn.TaskInput.from_object(
                {
                    "state_name": "parse_and_classify_text",
                    "report.$": "$.Payload",
                }
            ),
            result_path="$.parse_and_classify_text",
            output_path="$.parse_and_classify_text",
        ).add_catch(handler=send_error_report, result_path="$.exception")

        quarantine_object = sfn.Choice(self, "Quarantine Object?")

        quarantine_and_delete_object = sfn_tasks.LambdaInvoke(
            self,
            "quarantine_and_delete_object",
            lambda_function=dc_lambda,
            payload=sfn.TaskInput.from_object(
                {
                    "state_name": "quarantine_and_delete_object",
                    "report.$": "$.Payload",
                }
            ),
            result_path="$.quarantine_and_delete_object",
            output_path="$.quarantine_and_delete_object",
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

        definition = check_event.next(
            completed_job.when(
                sfn.Condition.boolean_equals("$.Payload.job_status", True),
                parse_and_classify_text.next(
                    quarantine_object.when(
                        sfn.Condition.boolean_equals(
                            "$.Payload.has_prohibited_info", True
                        ),
                        quarantine_and_delete_object,
                    )
                    .afterwards()
                ),
            )
            .otherwise(submit_job.next(block_object))
            .afterwards()
        ).next(send_report)

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
