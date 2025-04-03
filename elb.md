Overview
Amazon Application Load Balancer (ALB) is a fully managed service that automatically distributes incoming application traffic across multiple targets, such as EC2 instances, containers, and IP addresses. ALB supports path-based routing, host-based routing, and dynamic host scaling.

For more information, see Amazon ALB.

Example Usage
1. Creating an ALB with Target Groups and Listeners
This example sets up an Application Load Balancer with multiple listeners and target groups.

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
            "resource_type": "aws_alb",
            "resource_id": "application-load-balancer",
            "security_group_id": "${stack_id:alb-sg:attribute}",
            "subnets": [
                "subnet-0c784156beb8d2c0e",
                "subnet-0e6c8fbcf8f60d7da"
            ],
            "target_groups": [
                {
                    "resource_id": "tg-9000",
                    "protocol": "HTTP",
                    "port": 80,
                    "target_type": "ip",
                    "health_check": {
                        "enabled": true,
                        "path": "/health",
                        "interval": 30,
                        "timeout": 5
                    }
                }
            ],
            "listeners": [
                {
                    "protocol": "HTTP",
                    "port": 80,
                    "default_target_group": "${stack_id:tg-9000:attribute}"
                }
            ]
        }
    ]
}
2. Listener Rules for Path-Based Routing
Defines an ALB listener rule to route traffic based on request paths.

json
Copy
Edit
{
    "resource_type": "aws_alb_listener_rule",
    "resource_id": "listener-rule-1",
    "listener_arn": "${stack_id:alb-listener:arn}",
    "priority": 100,
    "conditions": [
        {
            "field": "path-pattern",
            "values": ["/api/*"]
        }
    ],
    "actions": [
        {
            "type": "forward",
            "target_group_arn": "${stack_id:tg-9000:arn}"
        }
    ]
}
3. Security Group for ALB
Creates a security group allowing inbound traffic on ports 80 and 443.

json
Copy
Edit
{
    "resource_type": "aws_ec2",
    "resource_id": "alb-sg",
    "allow_all_outbound": true,
    "ingress": [
        {
            "type": "cidr",
            "cidr": "0.0.0.0/0",
            "port": 80
        },
        {
            "type": "cidr",
            "cidr": "0.0.0.0/0",
            "port": 443
        }
    ]
}
4. ALB Access Logging
Enables access logging for ALB to store logs in an S3 bucket.

json
Copy
Edit
{
    "resource_type": "aws_alb_logging",
    "resource_id": "alb-logging",
    "alb_arn": "${stack_id:application-load-balancer:arn}",
    "s3_bucket": "my-alb-logs",
    "log_prefix": "alb-access-logs/"
}
Usage Recommendations
✔ Use HTTPS Listeners – Ensure all HTTP traffic is redirected to HTTPS for security.
✔ Enable Access Logs – Store logs in S3 for troubleshooting and security analysis.
✔ Optimize Target Groups – Use multiple target groups to balance application traffic.
✔ Implement Path-Based Routing – Direct traffic efficiently using listener rules.
✔ Restrict Security Groups – Limit inbound traffic to only necessary sources.

Argument References
Required
resource_type – (string) Type of resource (aws_alb, aws_alb_listener, etc.).

resource_id – (string) Unique identifier for the resource.

security_group_id – (string) Security group attached to the ALB.

subnets – (list) List of subnet IDs where the ALB is deployed.

target_groups – (list) Target groups linked to the ALB.

listeners – (list) Listeners that define how requests are routed.

Optional
health_check – (object) Configuration for ALB health checks.

logging – (object) Configuration for access logging.

listener_rules – (list) List of rules for request routing.

tags – (list) Key-value pairs for resource tagging.

Attribute References
alb_arn – The ARN of the Application Load Balancer.

listener_arn – The ARN of an ALB listener.

target_group_arn – The ARN of an ALB target group.

security_group_arn – The ARN of the security group attached to the ALB.






























Let me generate the structured documentation accordingly.

AWS Application Load Balancer (ALB) Documentation
Overview
Amazon Elastic Load Balancing (ALB) automatically distributes incoming application traffic across multiple targets, such as EC2 instances, containers, and Lambda functions. This documentation outlines the supported use cases based on the provided CDK script.

Example Usage
1. ALB Setup
Creates an Application Load Balancer in a specified VPC with an optional access logging configuration.

json
Copy
Edit
{
    "resource_type": "aws_alb",
    "resource_id": "my-alb",
    "vpc_subnets": [
        {
            "id": "subnet-0abc123456789",
            "zone": "us-west-2a"
        },
        {
            "id": "subnet-0def987654321",
            "zone": "us-west-2b"
        }
    ],
    "security_group_id": "sg-0ed05ea439ab3c74b",
    "internet_facing": true,
    "log_bucket_name": "alb-logs-bucket"
}
2. Target Group Configuration
Creates target groups and attaches them to an ALB, supporting IP-based, EC2 instance-based, and Lambda targets.

IP-Based Target Group
json
Copy
Edit
{
    "resource_type": "aws_alb_target_group",
    "resource_id": "ip-target-group",
    "vpc_id": "vpc-0abc123456789",
    "target_type": "IP",
    "protocol": "HTTP",
    "port": 80,
    "targets": ["192.168.1.100", "192.168.1.101"]
}
Instance-Based Target Group
json
Copy
Edit
{
    "resource_type": "aws_alb_target_group",
    "resource_id": "instance-target-group",
    "vpc_id": "vpc-0abc123456789",
    "target_type": "INSTANCE",
    "protocol": "HTTP",
    "port": 80,
    "targets": ["i-0a1b2c3d4e5f6g7h8", "i-0h8g7f6e5d4c3b2a1"]
}
Lambda Target Group
json
Copy
Edit
{
    "resource_type": "aws_alb_target_group",
    "resource_id": "lambda-target-group",
    "target_type": "LAMBDA",
    "targets": ["arn:aws:lambda:us-west-2:123456789012:function:myLambdaFunction"]
}
3. Listener Rules
Attaches listener rules to an ALB listener, defining priority and rule conditions.

json
Copy
Edit
{
    "resource_type": "aws_alb_listener_rule",
    "resource_id": "listener-rule-1",
    "listener_arn": "arn:aws:elasticloadbalancing:us-west-2:123456789012:listener/app/my-alb/abcdef1234567890",
    "priority": 10,
    "rule_conditions": [
        {
            "host_headers": ["example.com"],
            "path_patterns": ["/api/*"],
            "source_ips": ["192.168.1.1/32"]
        }
    ],
    "target_group_arns": [
        "arn:aws:elasticloadbalancing:us-west-2:123456789012:targetgroup/my-target-group/abcdef1234567890"
    ]
}
Usage Recommendations
Enable Access Logs: Store logs in an S3 bucket for monitoring.

Define Listener Rules: Use host headers, paths, and source IP conditions to control traffic flow.

Select the Right Target Type: Choose between IP, Instance, or Lambda targets based on deployment needs.

Argument References
Required
resource_type – (string) Type of resource (aws_alb, aws_alb_target_group, etc.).

resource_id – (string) Unique identifier for the resource.

vpc_subnets – (list) Subnets for the ALB deployment.

target_type – (string) The type of target (IP, INSTANCE, LAMBDA).

port – (integer) The port on which the target group listens.

Optional
log_bucket_name – (string) Name of the S3 bucket for ALB logs.

security_group_id – (string) Security group ID attached to the ALB.

rule_conditions – (list) Conditions for listener rules (host headers, path patterns, etc.).

Attribute References
alb_arn – ARN of the Application Load Balancer.

target_group_arn – ARN of the created Target Group.

listener_arn – ARN of the listener associated with the ALB.

