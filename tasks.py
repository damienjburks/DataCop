from invoke import task


@task
def lint(c):
    """
    Executes pylint to check for any linting issues/errors
    :param c:
    :return:
    """
    c.run("pylint src/lambda")


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
def cdk_deploy(c):
    """
    Bootstraps and deploys the CDK templates to AWS
    :param c:
    :return:
    """
    c.run(
        "cd src/cdk-cloudformation && cdk bootstrap && cdk deploy --require-approval=never"
    )


@task
def cdk_destroy(c):
    """
    Destroys the CDK templates within AWS
    :param c:
    :return:
    """
    c.run("cd src/cdk-cloudformation && cdk destroy --force --all")
