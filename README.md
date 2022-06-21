# DataCop

<p align="center"><img src="./documentation/images/logo.png" alt="DataCop Logo" width="200px" height="200px" /></p>

---

DataCop is an custom AWS framework that mitigates the 
potential of vulnerable S3 buckets. Reliant on AWS Macie results, DataCop enables professionals that leverage AWS Macie
to automatically block S3 buckets that contain PII or any classified information.

## Features
---

* Automatically provisioned infrastructure to bridge the 
cap between Macie and S3 with AWS CDK
* Configurable settings for bucket blocking (containment)
* Event-driven S3 bucket blocking (containment)

## Setup & Installation
---
### Requirements

DataCop is broken up into two parts and requires the following technologies
to be installed:

1. Python 3.8+

Please install these before proceeding.

### Install

The installation process for DataCop is fairly straightforward. Please follow the steps
outlined below:

1. Create and activate your virtual environment:
    
    #### Figure 1. Create/Activate Virtual Environment
    ![Create/Activate Virtual Environment](./documentation/images/create_activate_venv.gif)

2. Install the dependencies:

    #### Figure 2: Install Python Dependencies
    ![Installing Dependencies](./documentation/images/install_deps.gif)

Once you've installed those requirements, you're good to deploy the application.

## Deployment
---

For deployment, DataCop utilizes the `invoke` command. If you would
like to learn more about invoke, please refer to this document: [Invoke Docs](https://www.pyinvoke.org).

Assuming you have activated your virtual environment, 
run the following command to deploy the CDK stack:
    
#### Figure 3. Deploying DataCop
```bash
(.env) $ invoke cdk-deploy
```

>**NOTE:** This command will bootstrap the default AWS account & profile.
Afterward, it will deploy everything with `cdk deploy`.

To review the results, please log into your AWS account and verify
that the following CloudFormation Template exists: `DataCopCoreStack`.

## Want to contribute?
---

If you want to contribute, please take a 
look at the [Contributing Documentation](./documentation/contributing.md).