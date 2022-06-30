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
    c.run("pylint src/data_cop")


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
    # Configure environment
    account_id = boto3.client('sts').get_caller_identity().get('Account')
    s3_bucket_name = f"datacop-findings-{account_id}"
    os.environ['S3_BUCKET_NAME'] = s3_bucket_name

@task
def post_setup(c):
    # Configure your S3 buckets
    s3_bucket_name = os.environ['S3_BUCKET_NAME']
    c.run(
        f"python ./src/macie_setup.py {s3_bucket_name}"
    )

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

@task
def destroy(c):
    """
    Destroys the CDK templates within AWS
    :param c:
    :return:
    """
    c.run("cd src/cdk-cloudformation && cdk destroy --force --all")