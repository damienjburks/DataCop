import json
import os
import boto3

from invoke import task


@task
def lint(c):
    """
    Executes pylint to check for any linting issues/errors
    :param c:
    :return:
    """
    c.run("python -m pylint src")


@task
def format_check(c):
    """
    Checks the formatting of the code within the project
    :param c:
    :return:
    """
    c.run("python -m black --check .")


@task
def format(c):
    """
    Formats all of the python files within the project
    :param c:
    :return:
    """
    c.run("python -m black .")


@task
def pre_setup(c):
    """
    Configures environment deploying infrastructure
    :param c:
    :return:
    """
    account_id = boto3.client("sts").get_caller_identity().get("Account")
    s3_bucket_name = f"datacop-findings-{account_id}"
    kms_key_alias = "alias/data-cop-kms-key"
    ses_email = "dburksgtr@gmail.com"

    os.environ["S3_BUCKET_NAME"] = s3_bucket_name
    os.environ["KMS_KEY_ALIAS"] = kms_key_alias
    os.environ["SES_EMAIL"] = ses_email


@task
def post_setup(c):
    """
    Executes post setup configuration steps for Macie
    :param c:
    :return:
    """
    c.run(f"python ./src/datacop_setup.py")


@task
def disable_macie(c):
    """
    Disables macie for the account.
    :param c:
    :return:
    """
    c.run(f"python ./src/datacop_setup.py true")


@task(pre=[pre_setup], post=[post_setup])
def deploy(c):
    """
    Bootstraps and deploys the CDK templates to AWS
    :param c:
    :return:
    """
    c.run(
        "cd src/cdk-cloudformation && cdk bootstrap && cdk deploy --require-approval=never"
    )


@task(pre=[pre_setup])
def destroy(c):
    """
    Destroys the CDK templates within AWS
    :param c:
    :return:
    """
    c.run("cd src/cdk-cloudformation && cdk destroy --force --all")


@task(pre=[pre_setup], post=[disable_macie])
def destroy_and_disable(c):
    """
    Destroys the CDK templates and disables Macie
    for the AWS Account.
    :param c:
    :return:
    """
    c.run("cd src/cdk-cloudformation && cdk destroy --force --all")


@task
def test(c):
    """
    Executes unit test cases
    :param c:
    :return:
    """
    c.run("pytest tests/")
