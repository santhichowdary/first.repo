## Resource: aws_ecr
Provides an **Elastic Container Registry (ECR)** resource. AWS ECR is a managed container image registry service that allows storing, managing, and deploying Docker container images.

For information about AWS ECR and how to use it, see [What is Amazon Elastic Container Registry?](https://docs.aws.amazon.com/AmazonECR/latest/userguide/what-is-ecr.html)


## Example Usage

#### Basic ECR Repository
A simple private ECR repository with default settings.

```json
{
    "stack_id": "enhanced-ecr-stack",
    "resource_prefix": "enhanced-java",
    "aws_region": "us-west-2",
    
    "resources": [
        {
            "resource_type": "aws_ecr",
            "resource_id": "repository1",
            "repository_name": "enhanced-test-repository",
            "tags": {
                "env": "test",
                "project": "my-app"
            }
        }
    ]
}

```

#### ECR Repository with Image Scanning and Encryption
Creates an ECR repository with image scanning on push and encryption enabled using KMS.

```json

{
    "stack_id": "enhanced-ecr-stack",
    "resource_prefix": "enhanced-java",
    "aws_region": "us-west-2",

    "resources": [
        {
            "resource_type": "aws_ecr",
            "resource_id": "repository2",
            "repository_name": "enhanced-test-repository",
            "image_scanning_configuration": {
                "scan_on_push": true
            },
            "encryption_configuration": {
                "encryption_type": "KMS",
                "kms_key": "arn:aws:kms:us-west-2:123456789012:key/my-kms-key"
            },
            "tags": {
                "security": "enabled",
                "env": "production"
            }
        }
    ]
}
```

#### ECR Repository with Lifecycle Policy
Defines an ECR repository with a lifecycle policy to retain only the latest 10 images.
```json

{
    "stack_id": "enhanced-ecr-stack",
    "resource_prefix": "enhanced-java",
    "aws_region": "us-west-2",

    "resources": [
        {
            "resource_type": "aws_ecr",
            "resource_id": "repository3",
            "repository_name": "enhanced-test-repository",
            "lifecycle_policy": {
                "rules": [
                    {
                        "rulePriority": 1,
                        "description": "Retain only the latest 10 images",
                        "selection": {
                            "tagStatus": "any",
                            "countType": "imageCountMoreThan",
                            "countNumber": 10
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
```

#### ECR Repository with Public Access
Creates a public ECR repository allowing anonymous access to pull images.

```json

{
    "stack_id": "enhanced-ecr-stack",
    "resource_prefix": "enhanced-java",
    "aws_region": "us-west-2",

    "resources": [
        {
            "resource_type": "aws_ecr",
            "resource_id": "repository4",
            "repository_name": "enhanced-test-repository",
            "visibility": "public",
            "tags": {
                "env": "public",
                "access": "anonymous"
            }
        }
    ]
}
```

#### Enabling Tag Immutability
Prevents image tags from being overwritten, ensuring version stability.

```json

{
    "stack_id": "enhanced-ecr-stack",
    "resource_prefix": "enhanced-java",
    "aws_region": "us-west-2",

    "resources": [
        {
            "resource_type": "aws_ecr",
            "resource_id": "repository5",
            "repository_name": "immutable-repo",
            "image_tag_mutability": "IMMUTABLE",
            "tags": {
                "env": "production",
                "tag_policy": "immutable"
            }
        }
    ]
}

```

#### Cross-Region Replication
Automatically replicates images from one region to another for high availability.

```json

{
    "stack_id": "enhanced-ecr-stack",
    "resource_prefix": "enhanced-java",
    "aws_region": "us-west-2",

    "resources": [
        {
            "resource_type": "aws_ecr",
            "resource_id": "repository6",
            "repository_name": "multi-region-repo",
            "replication_configuration": {
                "rules": [
                    {
                        "destinations": [
                            {
                                "region": "us-east-1",
                                "registry_id": "123456789012"
                            }
                        ]
                    }
                ]
            },
            "tags": {
                "replication": "enabled",
                "primary_region": "us-west-2"
            }
        }
    ]
}
```


#### Applying Access Policy to Restrict Public Pulls
Allows only a specific AWS account to pull images, preventing unauthorized access.
```json

{
    "stack_id": "enhanced-ecr-stack",
    "resource_prefix": "enhanced-java",
    "aws_region": "us-west-2",

    "resources": [
        {
            "resource_type": "aws_ecr",
            "resource_id": "repository7",
            "repository_name": "restricted-access-repo",
            "repository_policy": {
                "version": "2012-10-17",
                "statement": [
                    {
                        "effect": "Allow",
                        "principal": {
                            "AWS": "arn:aws:iam::987654321098:root"
                        },
                        "action": [
                            "ecr:BatchGetImage",
                            "ecr:GetDownloadUrlForLayer"
                        ]
                    }
                ]
            },
            "tags": {
                "access": "restricted",
                "security": "high"
            }
        }
    ]
}

```

#### Trigger Lambda on Image Push using CloudWatch
Triggers a Lambda function whenever a new image is pushed to the repository.

```json
{
    "stack_id": "enhanced-ecr-stack",
    "resource_prefix": "enhanced-java",
    "aws_region": "us-west-2",

    "resources": [
        {
            "resource_type": "aws_ecr",
            "resource_id": "repository8",
            "repository_name": "event-driven-repo",
            "event_rule": {
                "event_pattern": {
                    "source": ["aws.ecr"],
                    "detail-type": ["ECR Image Action"],
                    "detail": {
                        "action-type": ["PUSH"],
                        "repository-name": ["event-driven-repo"]
                    }
                },
                "targets": [
                    {
                        "arn": "arn:aws:lambda:us-west-2:123456789012:function:processECRPush",
                        "role_arn": "arn:aws:iam::123456789012:role/CloudWatchEventInvokeLambda"
                    }
                ]
            },
            "tags": {
                "automation": "enabled",
                "trigger": "image_push"
            }
        }
    ]
}
```



### Usage Recommendations

* Enable Image Scanning: Use "image_scanning_configuration": { "scan_on_push": true } to detect vulnerabilities when images are pushed.
* Use KMS for Encryption:  AWS ECR does not encrypt repositories by default. You can enable encryption using "encryption_type": "KMS"
* Implement Lifecycle Policies: Configure lifecycle policies to remove unused images and reduce storage costs.
* Secure Access with IAM Policies: Restrict push and pull access using IAM policies for better security.
* Consider Public Repositories for Open-Source Projects: If hosting public images, set visibility to "public" and apply proper access control.

### Argument References

#### Required 
* repository_name - (string, Required) Name of the ECR repository.



#### Optional

* image_scanning_configuration - (object, Optional) Enables image scanning on push.
* encryption_configuration - (object, Optional) Configures encryption settings (AES-256 by default, can be set to KMS).
* encryption_type - (string) Supported values: AES256, KMS.
* kms_key - (string, Optional) The ARN of a KMS key for encryption.
* lifecycle_policy - (object, Optional) Defines rules for image retention and expiration.
* rules - (list) List of lifecycle rules.
* rulePriority - (number, Required) Priority of the rule.
* description - (string, Optional) Description of the rule.
* selection - (object, Required) Criteria for selecting images.
* action - (object, Required) Defines the action to take (e.g., expire images).
* visibility - (string, Optional) Repository visibility: private (default) or public.
* tags - (map, Optional) Key-value pairs to tag the repository.

### Attribute Reference

This resource exports the following attributes:

* repository_arn - The Amazon Resource Name (ARN) of the ECR repository.
* repository_url - The URL of the repository (e.g., 123456789012.dkr.ecr.us-west-2.amazonaws.com/my-repo).
* registry_id - The AWS account ID associated with the repository.












































1️⃣ Basic ECR Repository
📌 What it does:

Creates a private ECR repository with basic settings.
Tags are added for identification (e.g., env: test, project: my-app).
📌 How to explain it:

"This is the most basic way to create an ECR repository. It has just a name and some optional tags for organization."
Point out "repository_name": "enhanced-test-repository" in JSON.
2️⃣ ECR Repository with Image Scanning and Encryption
📌 What it does:

Enables security features like image scanning on push.
Encrypts stored images using AWS KMS.
📌 How to explain it:

"This repository scans images for vulnerabilities when they are pushed."
Highlight "scan_on_push": true
"Encryption is enabled using a KMS key for security."
Highlight "encryption_type": "KMS"
3️⃣ ECR Repository with Lifecycle Policy
📌 What it does:

Automatically deletes old images to save storage costs.
Retains only the latest 10 images.
📌 How to explain it:

"Lifecycle policies help manage storage by automatically removing old images."
Highlight "countNumber": 10 → "This means only the last 10 images will be kept."
4️⃣ ECR Repository with Public Access
📌 What it does:

Makes the repository public so anyone can pull images.
📌 How to explain it:

"This repository is accessible to anyone on the internet, making it useful for open-source projects."
Highlight "visibility": "public"
5️⃣ Enabling Tag Immutability
📌 What it does:

Prevents overwriting of existing image tags (ensures version stability).
📌 How to explain it:

"This prevents accidental overwrites of existing image tags, ensuring that a specific version remains unchanged."
Highlight "image_tag_mutability": "IMMUTABLE"
6️⃣ Cross-Region Replication
📌 What it does:

Copies images to another AWS region for high availability.
📌 How to explain it:

"If one AWS region goes down, the images are still available in another region."
Highlight "region": "us-east-1"
7️⃣ Applying Access Policy to Restrict Public Pulls
📌 What it does:

Restricts image access to a specific AWS account only.
📌 How to explain it:

"This ensures that only authorized accounts can pull images from this repository."
Highlight the IAM policy inside "repository_policy"
8️⃣ CloudWatch Event Rule for Image Push Notification
📌 What it does:

Triggers a Lambda function whenever a new image is pushed.
📌 How to explain it:

"This setup allows automation when new images are pushed. A Lambda function can take further actions, like triggering a deployment."
Highlight "event_pattern": { "source": ["aws.ecr"] }























