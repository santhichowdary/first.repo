AWS Secrets Manager Documentation
Overview
AWS Secrets Manager helps you securely store, manage, and retrieve sensitive information such as database credentials, API keys, and other secrets.
This documentation outlines common usage patterns supported through AWS CDK constructs.

Example Usage
1. Create a New Secret
Creates a new secret with a generated or user-provided value.

json
Copy
Edit

{
    "resource_type": "aws_secretsmanager_secret",
    "resource_id": "my-secret",
    "name": "myAppSecret",
    "description": "Secret for application credentials",
    "secret_string": "{\"username\":\"admin\",\"password\":\"P@ssword123\"}"
}


2. Import an Existing Secret
References an already existing secret using its ARN.

json
Copy
Edit
{
    "resource_type": "aws_secretsmanager_secret",
    "resource_id": "existing-secret",
    "secret_arn": "arn:aws:secretsmanager:us-west-2:123456789012:secret:existingSecret-123abc"
}
3. Create a Secret with Key-Value JSON
Creates a secret where multiple key-value pairs are stored inside a single secret.

json
Copy
Edit
{
    "resource_type": "aws_secretsmanager_secret",
    "resource_id": "db-credentials",
    "name": "dbCredentials",
    "secret_object": {
        "username": "dbadmin",
        "password": "dbPassword@2025",
        "engine": "mysql",
        "host": "db.example.com",
        "port": 3306
    }
}
4. Add Resource Policy to Secret (Optional)
Adds permissions for other IAM principals to access the secret.

json
Copy
Edit
{
    "resource_type": "aws_secretsmanager_secret",
    "resource_id": "shared-secret",
    "name": "sharedAppSecret",
    "secret_string": "sharedSecretValue",
    "resource_policy": {
        "statements": [
            {
                "effect": "Allow",
                "principal": {
                    "AWS": "arn:aws:iam::123456789012:role/ExternalAppRole"
                },
                "action": "secretsmanager:GetSecretValue",
                "resource": "*"
            }
        ]
    }
}
Usage Recommendations
Encryption: Secrets are encrypted automatically using AWS KMS. You can specify a custom KMS key if needed.

Rotation: Enable secret rotation if storing credentials (database, API keys) that need periodic updates.

Access Control: Always define minimal access policies using IAM or resource-based policies.

Argument References
Required:

resource_type – (string) Should always be aws_secretsmanager_secret.

resource_id – (string) Unique identifier for the resource.

Optional:

name – (string) Name of the secret.

description – (string) Description of the secret.

secret_string – (string) The plaintext value of the secret.

secret_object – (object) Key-value structure to store multiple fields inside a secret.

secret_arn – (string) ARN for an existing secret.

resource_policy – (object) Policy to attach for access control.

Attribute References
secret_arn – ARN of the created or referenced secret.

secret_name – Name of the secret.

kms_key_id – KMS Key ID used to encrypt the secret (optional).

