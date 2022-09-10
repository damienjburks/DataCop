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
    result_s3_bucket_name = f"datacop-findings-{account_id}"
    forensics_s3_bucket_name = f"datacop-forensics-{account_id}"

    kms_key_alias = "alias/data-cop-kms-key"

    os.environ["RESULT_S3_BUCKET_NAME"] = result_s3_bucket_name
    os.environ["FORENSICS_S3_BUCKET_NAME"] = forensics_s3_bucket_name
    os.environ["KMS_KEY_ALIAS"] = kms_key_alias


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
def deploy(c, email_address):
    """
    Bootstraps and deploys the CDK templates to AWS
    :param email_address: Necessary for SNS Topic Subscription
    :return:
    """
    c.run(
        f"cd src/cdk-cloudformation && "
        f"cdk bootstrap && "
        f"cdk deploy --require-approval=never "
        f"--parameters bucketName={os.environ['RESULT_S3_BUCKET_NAME']} "
        f"--parameters forensicsBucketName={os.environ['FORENSICS_S3_BUCKET_NAME']} "
        f"--parameters kmsKeyAlias={os.environ['KMS_KEY_ALIAS']} "
        f"--parameters snsEmailAddress={email_address}"
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
