# DataCop

<p align="center"><img src="./documentation/images/logo.png" alt="DataCop Logo" width="200px" height="200px" /></p>

---
DataCop is a custom AWS framework that mitigates S3 bucket attack 
vectors based on customer configuration. By default, this framework relies on AWS Macie results to automatically 
block S3 buckets that contain PII or any classified information. However, this framework supports the following 
third party services:
- Trend Micro CloudOne File Storage Security (FSS)
>**NOTE:** All other integrations from third party vendors is completely optional.

Features
---

* Automatically provisioned infrastructure with AWS CDK
* Configurable settings for bucket blocking for Macie and FSS
* Event-driven S3 bucket blocking
* Highly scalable and extensible

Architecture
---
If you would like to view the architecture of the project, please refer
to the [Architecture Documentation](/documentation/architecture.md).

Setup & Installation
---

### Requirements

In order to install and deploy DataCop, you need
to ensure that you have the following installed:

- Python 3.8+

### Install

The installation process for DataCop is fairly straightforward. Please follow the steps
outlined below:

0. Configure your `config.ini` file. This file is **EXTREMELY IMPORTANT**, and it must be 
filled out properly before you deploy DataCop. An example of the file with an explanation
of the key/value pairs are highlighted below:
  
    #### Figure 0: Modify config.ini file
    ```ini
    [configuration]
    s3_bucket_name = your_bucket_name # MANDATORY
    kms_key_alias = alias/datacop-kms-key # MANDATORY
    email_address = sample_email_address@gmail.com # MANDATORY
    severity = LOW|MEDIUM|HIGH # MANDATORY
    file_storage_sns_topic_arn = arnforFSS # OPTIONAL
    quarantine_s3_bucket_name = your-quarantine-items # OPTIONAL
    ```

    >**NOTE**: The _optional_ parameters are in-fact, optional.
    >You do not have to specify these if you do not have CloudOne FSS deployed
    >into your environment.

1. Create and activate your virtual environment:
    
    #### Figure 1. Create/Activate Virtual Environment
    ```bash
    $ python -m venv .datacop-venv
    (datacop-venv) $ # You've activated your VENV
    ```

2. Install the dependencies:

    #### Figure 2: Install Python Dependencies
    ```text
    (datacop-venv) $ pip install -r requirements.txt
    ```
    
Once you've installed those requirements, you're good to deploy the application.

Commands
---

This project uses `invoke` to execute commands for both development and deployment.
If you would like to learn more about invoke, please refer to this document: [Invoke Docs](https://www.pyinvoke.org).

#### Figure 3. List of commands
```text
(datacop-venv) $ inv --list

Available tasks:
  deploy                Bootstraps and deploys the CDK templates to AWS
  destroy               Destroys the CDK templates within AWS
  destroy-and-disable   Destroys the CDK templates and disables Macie
  disable-macie         Disables macie for the account.
  format                Formats all of the python files within the project
  format-check          Checks the formatting of the code within the project
  lint                  Executes pylint to check for any linting issues/errors
  post-setup            Executes post setup configuration steps for Macie
  pre-setup             Configures environment deploying infrastructure
  test                  Executes unit test cases
```

Deployment
---

Assuming you have activated your virtual environment, 
run the following command to deploy the CDK stack:
    
#### Figure 4. Deploying DataCop
```text
(.env) $ invoke deploy
```
**Please ensure that you have configured the config.ini file prior to executing this command.
If you have not, please refer to Step 0.**

>**NOTE:** This command will bootstrap the default AWS account & profile.
Afterward, it will deploy everything with `cdk deploy`. 

---
To review the results, please log into your AWS account and verify
that the following CloudFormation Template exists: `DataCopCoreStack`.

Want to contribute?
---

If you want to contribute, please take a 
look at the [Contributing Documentation](./documentation/contributing.md).

Presentations
---
- [Automated S3 Blocking with AWS Macie and DataCop @ DevOpsDays Dallas - 5th Anniversary 2022](documentation/talks/devopsdays_dallas_2022/README.md)
- [Minimizing AWS S3 attack vectors at scale @ BSidesDFW - 2022](documentation/talks/bsides_dfw_2022/README.md)
- [A 10,000-foot view on how to create automated data and malware mitigation controls](documentation/talks/aws_user_group_chicago_2023/README.md)