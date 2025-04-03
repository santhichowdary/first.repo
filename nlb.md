Resource: aws_nlb
The AWS Network Load Balancer (NLB) is designed to handle millions of requests per second while maintaining ultra-low latency. This documentation covers creating an NLB, attaching target groups, configuring listeners, and logging.

For more details, see AWS NLB Documentation.

Example Usage
1️⃣ Existing NLB Lookup
Retrieves an existing NLB by its ARN.

json
Copy
Edit
{
    "stack_id": "nlb-stack",
    "resource_prefix": "my-app",
    "aws_region": "us-west-2",
    "resources": [
        {
            "resource_type": "aws_nlb",
            "resource_id": "existing_nlb",
            "existing_nlb_arn": "arn:aws:elasticloadbalancing:us-west-2:123456789012:loadbalancer/net/my-nlb/abcdef1234567890"
        }
    ]
}
2️⃣ Create a New NLB
Creates a new NLB with cross-zone load balancing enabled.

json
Copy
Edit
{
    "stack_id": "nlb-stack",
    "resource_prefix": "my-app",
    "aws_region": "us-west-2",
    "resources": [
        {
            "resource_type": "aws_nlb",
            "resource_id": "new_nlb",
            "vpc_subnets": ["subnet-12345678", "subnet-87654321"],
            "internet_facing": true,
            "cross_zone_enabled": true,
            "deletion_protection": false,
            "security_group_id": "sg-12345678",
            "log_bucket_name": "my-nlb-logs"
        }
    ]
}
3️⃣ Attach Listeners
Attaches a listener to the NLB, forwarding traffic to a target group.

json
Copy
Edit
{
    "stack_id": "nlb-stack",
    "resource_prefix": "my-app",
    "aws_region": "us-west-2",
    "resources": [
        {
            "resource_type": "aws_nlb",
            "resource_id": "nlb_with_listener",
            "existing_nlb_arn": "arn:aws:elasticloadbalancing:us-west-2:123456789012:loadbalancer/net/my-nlb/abcdef1234567890",
            "listeners": [
                {
                    "id": "listener-tcp",
                    "port": 80,
                    "protocol": "TCP",
                    "target_groups": [
                        {
                            "id": "tg-instance",
                            "target_type": "INSTANCE",
                            "port": 80,
                            "health_check_port": "80",
                            "targets": ["i-0123456789abcdef0", "i-0fedcba9876543210"]
                        }
                    ]
                }
            ]
        }
    ]
}
4️⃣ Target Groups
Defines target groups for IP-based and instance-based targets.

json
Copy
Edit
{
    "stack_id": "nlb-stack",
    "resource_prefix": "my-app",
    "aws_region": "us-west-2",
    "resources": [
        {
            "resource_type": "aws_nlb",
            "resource_id": "nlb_with_target_groups",
            "existing_nlb_arn": "arn:aws:elasticloadbalancing:us-west-2:123456789012:loadbalancer/net/my-nlb/abcdef1234567890",
            "listeners": [
                {
                    "id": "listener-tls",
                    "port": 443,
                    "protocol": "TLS",
                    "https_certificate": "arn:aws:acm:us-west-2:123456789012:certificate/abcdefg-1234-5678-9012-abcdefg",
                    "target_groups": [
                        {
                            "id": "tg-ip",
                            "target_type": "IP",
                            "port": 443,
                            "health_check_port": "443",
                            "targets": ["10.0.1.10", "10.0.1.11"]
                        }
                    ]
                }
            ]
        }
    ]
}
Usage Recommendations
✅ Use Existing NLB Lookup when integrating with pre-existing infrastructure.
✅ Enable Cross-Zone Load Balancing to improve traffic distribution.
✅ Use TLS Listeners to secure network traffic.
✅ Configure Target Groups based on workload needs (IP-based or instance-based).
✅ Enable Access Logs for monitoring and debugging.

Argument References
Required
resource_id – (string) Unique identifier for the NLB resource.

vpc_subnets – (list) Subnets where the NLB will be deployed.

security_group_id – (string) Security group associated with the NLB.

Optional
existing_nlb_arn – (string) ARN of an existing NLB to reference.

internet_facing – (boolean) Whether the NLB is internet-facing.

cross_zone_enabled – (boolean) Whether cross-zone load balancing is enabled.

deletion_protection – (boolean) Prevents accidental deletion of the NLB.

log_bucket_name – (string) S3 bucket name for storing access logs.

Listeners
port – (integer) The port on which the listener is listening.

protocol – (string) The protocol for the listener (TCP/TLS).

https_certificate – (string) ARN of the SSL/TLS certificate for TLS listeners.

Target Groups
target_type – (string) Type of targets (IP or INSTANCE).

targets – (list) List of IP addresses or instance IDs.

health_check_port – (string) Port for health checks.

target_group_name – (string) Name of the target group.

Attribute References
This resource exports the following attributes:

dns – The DNS name of the Network Load Balancer.

arn – The Amazon Resource Name (ARN) of the NLB.

🚀 Key Takeaways
✅ Existing NLB Lookup allows integration with pre-existing infrastructure.
✅ New NLB Creation supports both internal and internet-facing deployments.
✅ Listeners control traffic forwarding and can be TCP or TLS.
✅ Target Groups support IP-based and instance-based targets.
✅ Access Logging helps with monitoring and debugging.



























 Retrieve an Existing NLB
Finds an existing NLB by ARN and attaches a listener.

json
Copy
Edit
{
    "stack_id": "nlb-stack",
    "resource_prefix": "my-app",
    "aws_region": "us-west-2",
    "resources": [
        {
            "resource_type": "aws_nlb",
            "resource_id": "existing_nlb",
            "load_balancer_arn": "arn:aws:elasticloadbalancing:us-west-2:123456789012:loadbalancer/net/my-nlb/abcdef123456"
        }
    ]
}
2️⃣ Create a New NLB (Internet-facing or Internal)
Defines an NLB with cross-zone load balancing and assigns it to subnets.

json
Copy
Edit
{
    "stack_id": "nlb-stack",
    "resource_prefix": "my-app",
    "aws_region": "us-west-2",
    "resources": [
        {
            "resource_type": "aws_nlb",
            "resource_id": "new_nlb",
            "name": "my-nlb",
            "scheme": "internet-facing",
            "subnets": ["subnet-12345678", "subnet-87654321"],
            "cross_zone_enabled": true
        }
    ]
}
🔹 scheme: "internet-facing" or "internal"
🔹 cross_zone_enabled: Enables load distribution across all AZs

3️⃣ Enable Access Logging
Stores NLB logs in an S3 bucket.

json
Copy
Edit
{
    "stack_id": "nlb-stack",
    "resource_prefix": "my-app",
    "aws_region": "us-west-2",
    "resources": [
        {
            "resource_type": "aws_nlb",
            "resource_id": "nlb_with_logging",
            "name": "my-nlb",
            "access_logs": {
                "s3_bucket_name": "my-nlb-logs",
                "s3_bucket_prefix": "logs/"
            }
        }
    ]
}
4️⃣ Add Listeners (TCP/TLS)
Defines listeners that route traffic to target groups.

json
Copy
Edit
{
    "stack_id": "nlb-stack",
    "resource_prefix": "my-app",
    "aws_region": "us-west-2",
    "resources": [
        {
            "resource_type": "aws_nlb",
            "resource_id": "nlb_listener",
            "listeners": [
                {
                    "protocol": "TCP",
                    "port": 80,
                    "target_group_arn": "arn:aws:elasticloadbalancing:us-west-2:123456789012:targetgroup/my-target-group/abcdef123456"
                },
                {
                    "protocol": "TLS",
                    "port": 443,
                    "certificate_arn": "arn:aws:acm:us-west-2:123456789012:certificate/abcdef-1234"
                }
            ]
        }
    ]
}
🔹 protocol: "TCP" or "TLS"
🔹 certificate_arn (Required for TLS listeners)

5️⃣ Create a Target Group with Health Checks
Registers a target group with IP-based or Instance-based targets.

json
Copy
Edit
{
    "stack_id": "nlb-stack",
    "resource_prefix": "my-app",
    "aws_region": "us-west-2",
    "resources": [
        {
            "resource_type": "aws_nlb",
            "resource_id": "target_group",
            "target_group_name": "my-target-group",
            "protocol": "TCP",
            "port": 80,
            "target_type": "ip",
            "health_check": {
                "path": "/",
                "protocol": "TCP",
                "interval": 30,
                "timeout": 5,
                "healthy_threshold": 3,
                "unhealthy_threshold": 2
            }
        }
    ]
}
🔹 target_type: "ip" or "instance"
🔹 health_check: Configurable health check parameters

6️⃣ Register Targets (IP or Instance)
Adds instances or IP addresses to the target group.

json
Copy
Edit
{
    "stack_id": "nlb-stack",
    "resource_prefix": "my-app",
    "aws_region": "us-west-2",
    "resources": [
        {
            "resource_type": "aws_nlb",
            "resource_id": "target_registration",
            "target_group_arn": "arn:aws:elasticloadbalancing:us-west-2:123456789012:targetgroup/my-target-group/abcdef123456",
            "targets": [
                {
                    "type": "ip",
                    "ip_address": "192.168.1.10"
                },
                {
                    "type": "instance",
                    "instance_id": "i-0123456789abcdef"
                }
            ]
        }
    ]
}
Usage Recommendations
✅ Use Cross-Zone Load Balancing for even traffic distribution.
✅ Enable Access Logging for auditing & debugging.
✅ Choose IP-based targets for containerized workloads (ECS).
✅ Use TLS Listeners for secure traffic routing.

Argument References
Required Arguments
Parameter	Type	Description
name	string	The name of the NLB
scheme	string	"internet-facing" or "internal"
subnets	list	List of subnet IDs for the NLB
protocol	string	"TCP" or "TLS" (for listeners)
port	integer	Listener port (e.g., 80, 443)
target_type	string	"ip" or "instance"
target_group_arn	string	ARN of the target group
Optional Arguments
Parameter	Type	Description
cross_zone_enabled	boolean	Enables cross-zone load balancing
access_logs.s3_bucket_name	string	S3 bucket for access logs
certificate_arn	string	Required for TLS listeners
health_check	object	Defines health check parameters
Attribute References
The following attributes are exported:

Attribute	Description
load_balancer_arn	ARN of the NLB
dns_name	DNS name of the NLB
target_group_arn	ARN of the Target Group
🚀 Summary of Use Cases
Use Case	Description	Example
Retrieve Existing NLB	Use an existing NLB by ARN	"load_balancer_arn": "arn:aws:elasticloadbalancing:..."
Create a New NLB	Define a new NLB with subnets	"scheme": "internet-facing"
Enable Access Logging	Store logs in an S3 bucket	"access_logs": { "s3_bucket_name": "my-logs" }
Add TCP/TLS Listeners	Route traffic to target groups	"protocol": "TLS", "port": 443
Create Target Group	Define health checks for backend targets	"target_type": "ip"
Register Targets	Attach IPs or instances to target groups	"targets": [{ "type": "instance", "instance_id": "i-..." }]