# Data Cop

<p align="center"><img src="./documentation/images/logo.png" alt="DataCop Logo" width="200px" height="200px" /></p>

---

Data Cop is an custom AWS framework that mitigates the 
potential of vulnerable S3 buckets. Reliant on AWS Macie results, Data Cop enables professionals that leverage AWS Macie
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

Data Cop is broken up into two parts and requires the following technologies
to be installed:

1. Python 3.8+

Please install these before proceeding.

### Install

The installation process for Data Cop is fairly straightforward. Please follow the steps
outlined below:

1. Create and activate your virtual environment:

    ![Create/Activate Virtual Environment](./documentation/images/create_activate_venv.gif)

2. Install the dependencies:

    ![Installing Dependencies](./documentation/images/install_deps.gif)

Once you've installed those requirements, you're good to go.

## Deployment
---

WIP

## Want to contribute?
---

If you want to contribute, please take a 
look at the [Contributing Documentation](./documentation/contributing.md).