import os
import boto3
import configparser

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

    config = configparser.ConfigParser()
    config.read("config.ini")

    os.environ[
        "S3_BUCKET_NAME"
    ] = f"{config['configuration']['s3_bucket_name']}-{account_id}"
    os.environ["KMS_KEY_ALIAS"] = config["configuration"]["kms_key_alias"]
    os.environ["EMAIL_ADDRESS"] = config["configuration"]["email_address"]
    os.environ["FSS_SNS_TOPIC_ARN"] = config["configuration"][
        "file_storage_sns_topic_arn"
    ]
    os.environ["QUARANTINE_S3_BUCKET_NAME"] = config["configuration"][
        "quarantine_s3_bucket_name"
    ]


@task
def post_setup(c):
    """
    Executes post setup configuration steps for Macie
    :param c:
    :return:
    """
    c.run(f"python ./src/macie_setup.py")


@task
def disable_macie(c):
    """
    Disables macie for the account.
    :param c:
    :return:
    """
    c.run(f"python ./src/macie_setup.py true")


@task(pre=[pre_setup], post=[post_setup])
def deploy(c):
    """
    Bootstraps and deploys the CDK templates to AWS
    :return:
    """
    c.run(
        f"cd src/cdk-cloudformation && "
        f"cdk bootstrap && "
        f"cdk deploy --all --require-approval=never "
        f"--parameters DataCopCore:bucketName={os.environ['S3_BUCKET_NAME']} "
        f"--parameters DataCopCore:kmsKeyAlias={os.environ['KMS_KEY_ALIAS']} "
        f"--parameters DataCopCore:snsEmailAddress={os.environ['EMAIL_ADDRESS']}"
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
