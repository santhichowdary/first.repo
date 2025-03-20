our CDK script.

Resource: aws_ecr
Provides an Elastic Container Registry (ECR) resource. AWS ECR is a managed container image registry service that allows storing, managing, and deploying Docker container images.

For information about AWS ECR and how to use it, see What is Amazon Elastic Container Registry?

Example Usage
Basic ECR Repository
A simple private ECR repository with default settings.

json
Copy
Edit
{
    "stack_id": "ecr-stack",
    "resource_prefix": "my-app",
    "aws_region": "us-west-2",
    "resources": [
        {
            "resource_type": "aws_ecr",
            "resource_id": "repository1",
            "repository_name": "my-basic-repo",
            "tags": {
                "env": "dev",
                "project": "my-app"
            }
        }
    ]
}
ECR Repository with Image Scanning
Enables image scanning on push for security vulnerability detection.

json
Copy
Edit
{
    "stack_id": "ecr-stack",
    "resource_prefix": "my-app",
    "aws_region": "us-west-2",
    "resources": [
        {
            "resource_type": "aws_ecr",
            "resource_id": "repository2",
            "repository_name": "secure-repo",
            "image_scanning_configuration": {
                "scan_on_push": true
            },
            "tags": {
                "security": "enabled"
            }
        }
    ]
}
ECR Repository with Encryption
Creates an ECR repository with KMS encryption enabled.

json
Copy
Edit
{
    "stack_id": "ecr-stack",
    "resource_prefix": "my-app",
    "aws_region": "us-west-2",
    "resources": [
        {
            "resource_type": "aws_ecr",
            "resource_id": "repository3",
            "repository_name": "encrypted-repo",
            "encryption_configuration": {
                "encryption_type": "KMS",
                "kms_key": "arn:aws:kms:us-west-2:123456789012:key/my-kms-key"
            },
            "tags": {
                "security": "high"
            }
        }
    ]
}
ECR Repository with Lifecycle Policy
Defines an ECR repository with a lifecycle policy to retain only the last 15 images.

json
Copy
Edit
{
    "stack_id": "ecr-stack",
    "resource_prefix": "my-app",
    "aws_region": "us-west-2",
    "resources": [
        {
            "resource_type": "aws_ecr",
            "resource_id": "repository4",
            "repository_name": "lifecycle-repo",
            "lifecycle_policy": {
                "rules": [
                    {
                        "rulePriority": 1,
                        "description": "Retain only the last 15 images",
                        "selection": {
                            "tagStatus": "any",
                            "countType": "imageCountMoreThan",
                            "countNumber": 15
                        },
                        "action": {
                            "type": "expire"
                        }
                    }
                ]
            },
            "tags": {
                "env": "staging"
            }
        }
    ]
}
Applying Tags to ECR Repository
Assigns metadata tags to an ECR repository.

json
Copy
Edit
{
    "stack_id": "ecr-stack",
    "resource_prefix": "my-app",
    "aws_region": "us-west-2",
    "resources": [
        {
            "resource_type": "aws_ecr",
            "resource_id": "repository5",
            "repository_name": "tagged-repo",
            "tags": {
                "env": "production",
                "owner": "dev-team"
            }
        }
    ]
}
Usage Recommendations
Enable Image Scanning: Use "image_scanning_configuration": { "scan_on_push": true } to detect vulnerabilities when images are pushed.

Use KMS for Encryption: AWS ECR does not encrypt repositories by default. Enable encryption using "encryption_type": "KMS".

Implement Lifecycle Policies: Configure lifecycle policies to remove unused images and reduce storage costs.

Secure Access with IAM Policies: Restrict push and pull access using IAM policies for better security.

Tag Your Resources: Use "tags": { "key": "value" } to assign metadata to repositories.

Argument References
Required
repository_name – (string, Required) The name of the ECR repository.

Optional
image_scanning_configuration – (object, Optional) Enables image scanning on push.

encryption_configuration – (object, Optional) Configures encryption settings.

encryption_type – (string) Supported values: AES256, KMS.

kms_key – (string) The ARN of a KMS key for encryption.

lifecycle_policy – (object, Optional) Defines rules for image retention and expiration.

rules – (list) List of lifecycle rules.

rulePriority – (number, Required) Priority of the rule.

description – (string, Optional) Description of the rule.

selection – (object, Required) Criteria for selecting images.

action – (object, Required) Defines the action to take (e.g., expire images).

tags – (map, Optional) Key-value pairs to tag the repository.

Attribute References
This resource exports the following attributes:

repository_arn – The Amazon Resource Name (ARN) of the ECR repository.

repository_url – The URL of the repository (e.g., 123456789012.dkr.ecr.us-west-2.amazonaws.com/my-repo).

registry_id – The AWS account ID associated with the repository