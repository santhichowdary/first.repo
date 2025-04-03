Overview
Amazon Elastic Container Service (ECS) is a fully managed container orchestration service that helps you deploy, manage, and scale containerized applications. ECS supports Fargate and EC2 launch types for running containers.

For more information, see Amazon ECS.

Example Usage
1. ECS Cluster with Fargate Service
Creates an ECS cluster with a Fargate service, including a task definition, auto-scaling, and logging.

json
Copy
Edit
{
    "stack_id": "9000-hw",
    "resource_prefix": "9000-hw",
    "aws_region": "us-west-2",
    "vpc": {
        "name": "vpc",
        "id": "vpc-0fe0ccb4f6f842818"
    },
    "resources": [
        {
            "resource_type": "aws_ecs_fargate",
            "resource_id": "cluster",
            "services": [
                {
                    "resource_id": "9000-svc",
                    "security_group_id": "${stack_id:resource_id:attribute}",
                    "desired_count": 1,
                    "vpc_subnets": [
                        {
                            "id": "subnet-0c784156beb8d2c0e",
                            "zone": "us-west-2a"
                        },
                        {
                            "id": "subnet-0e6c8fbcf8f60d7da",
                            "zone": "us-west-2b"
                        }
                    ],
                    "task_definition": {
                        "task_role": "${stack_id:resource_id:attribute}",
                        "execution_role": "${9000-hw:task-execution-role:arn}",
                        "memory_limit": 8192,
                        "cpu": 2048,
                        "containers": [
                            {
                                "resource_id": "ctr-9000",
                                "name_override": "dev-test-9000",
                                "ecr_repo": "java17_template_port9000",
                                "ports": [3000, 9000],
                                "memory": 512,
                                "cpu": 1024,
                                "log_group": "${9000-hw:log-group:aws_resource}",
                                "environment_variables": [
                                    { "ENV_NAME": "dev" },
                                    { "fdc:uaid": "UAID-10302" },
                                    { "application_name": "test-9000-helloworld" },
                                    { "created_by": "gurminder.sidhu@fiserv.com" }
                                ]
                            }
                        ]
                    }
                }
            ]
        }
    ]
}
2. ECS Task Definition with Container and vault secret integration
Defines an ECS task definition with a container, specifying CPU, memory, logging, and environment variables.

json
{
    "resource_type": "aws_ecs_task_definition",
    "resource_id": "task-definition",
    "task_role": "${stack_id:task-role:arn}",
    "execution_role": "${stack_id:task-execution-role:arn}",
    "memory_limit": 8192,
    "cpu": 2048,
    "containers": [
        {
            "resource_id": "ctr-9000",
            "name_override": "dev-test-9000",
            "ecr_repo": "java17_template_port9000",
            "ports": [3000, 9000],
            "memory": 512,
            "cpu": 1024,
            "log_group": "${stack_id:log-group:aws_resource}",
            "environment_variables": [
                { "ENV_NAME": "dev" },
                { "fdc:uaid": "UAID-10302" },
                { "application_name": "test-9000-helloworld" },
                { "created_by": "gurminder.sidhu@fiserv.com" }
            ],
            "secrets": [
                {
                    "name": "DATABASE_PASSWORD",
                    "valueFrom": "vault:secret/data/db#password"
                },
                {
                    "name": "API_KEY",
                    "valueFrom": "vault:secret/data/api#key"
                }
            ]
        }
    ]
}

3. ECS Service Auto Scaling
Configures auto-scaling for an ECS service based on CPU and memory utilization.

json
Copy
Edit
{
    "resource_type": "aws_ecs_auto_scaling",
    "resource_id": "ecs-auto-scaling",
    "min_capacity": 1,
    "max_capacity": 4,
    "cpu_target_utilization": 70,
    "cpu_scale_in_cooldown": 300,
    "cpu_scale_out_cooldown": 300,
    "mem_target_utilization": 70,
    "mem_scale_in_cooldown": 300,
    "mem_scale_out_cooldown": 300
}
4. Security Group for Fargate Service
Creates a security group allowing inbound traffic on port 3000.

json
Copy
Edit
{
    "resource_type": "aws_ec2",
    "resource_id": "sg-for-fargate-svc",
    "allow_all_outbound": true,
    "ingress": [
        {
            "type": "construct",
            "peer": "sg-0ed05ea439ab3c74b",
            "port": 3000
        }
    ]
}
5. CloudWatch Log Group for ECS
Creates a log group for storing ECS container logs.

json
Copy
Edit
{
    "resource_type": "aws_logs",
    "resource_id": "log-group",
    "subscription_filter_arn": "arn:aws:logs:us-west-2:871681779858:destination:3467d164-8930-4845-81d1-f509ef4e57a3"
}
6. IAM Roles for ECS Tasks
Execution Role for ECS Task
Defines an execution role that allows ECS tasks to interact with AWS services.

json
Copy
Edit
{
    "resource_type": "aws_iam",
    "resource_id": "task-execution-role",
    "assume_role_principal": "ecs-tasks.amazonaws.com",
    "policies": [
        {
            "inline_policies": [
                {
                    "name": "fargate-tsk-exec-policy",
                    "path": "policies/fargate-task-execution-policy.json"
                }
            ]
        },
        {
            "managed_policy_arns": [
                "arn:aws:iam::aws:policy/AmazonS3FullAccess"
            ]
        }
    ]
}
Task Role for ECS Task
Defines a task role that grants permissions to the running ECS task.

json
Copy
Edit
{
    "resource_type": "aws_iam",
    "resource_id": "task-role",
    "assume_role_principal": "ecs-tasks.amazonaws.com",
    "policies": [
        {
            "inline_policies": [
                {
                    "name": "fargate-tsk-policy",
                    "path": "policies/fargate-task-policy.json"
                }
            ]
        }
    ]
}
Usage Recommendations
Use Fargate for Serverless Deployments: Eliminates the need to manage EC2 instances.

Enable Auto Scaling: Adjusts service capacity based on CPU/memory usage.

Utilize CloudWatch Logging: Stores and analyzes logs.

Restrict Security Groups: Control inbound traffic using security group rules.

Apply IAM Policies: Ensure least privilege for task execution and access.

Argument References
Required
resource_type – (string) The type of ECS resource (aws_ecs_fargate, aws_ecs_task_definition, etc.).

resource_id – (string) Unique identifier for the resource.

services – (list) List of ECS services within the cluster.

Optional
security_group_id – (string) Security group attached to the service.

desired_count – (integer) Number of desired tasks for the service.

vpc_subnets – (list) List of subnets where the service runs.

task_definition – (object) Task definition configuration.

auto_scaling – (object) Auto-scaling settings.

log_group – (string) CloudWatch log group for ECS logs.

Attribute References
cluster_arn – The ARN of the ECS cluster.

service_arn – The ARN of the ECS service.

task_definition_arn – The ARN of the ECS task definition.

log_group_arn – The ARN of the CloudWatch Log Group.

