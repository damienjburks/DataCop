import os
import pytest


@pytest.fixture
def aws_credentials():
    os.environ["AWS_ACCESS_KEY_ID"] = "datacop-testing"
    os.environ["AWS_SECRET_ACCESS_ID"] = "datacop-testing"
    os.environ["AWS_SECURITY_TOKEN"] = "datacop-testing"
    os.environ["AWS_SESSION_TOKEN"] = "datacop-testing"
