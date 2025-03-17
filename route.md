Provides an Amazon Route 53 resource. Route 53 is a scalable and highly available domain name system (DNS) web service that provides domain registration, DNS routing, and health checking.

For more details, see What is Amazon Route 53?

Example Usage
🔹 Basic Hosted Zone
Creates a simple hosted zone in Route 53.

json
Copy
Edit
{
    "stack_id": "route53-stack",
    "resource_prefix": "example",
    "aws_region": "us-east-1",
    
    "resources": [
        {
            "resource_type": "aws_route53_zone",
            "resource_id": "example-zone",
            "name": "example.com",
            "comment": "Hosted zone for example.com",
            "tags": {
                "env": "production"
            }
        }
    ]
}
🔹 Public Hosted Zone with Records
Creates a public hosted zone and an A record pointing to an IP.

json
Copy
Edit
{
    "stack_id": "route53-stack",
    "resource_prefix": "example",
    "aws_region": "us-east-1",
    
    "resources": [
        {
            "resource_type": "aws_route53_zone",
            "resource_id": "public-zone",
            "name": "mywebsite.com",
            "visibility": "public",
            "tags": {
                "env": "production"
            }
        },
        {
            "resource_type": "aws_route53_record",
            "resource_id": "a-record",
            "zone_id": "${public-zone.id}",
            "name": "www.mywebsite.com",
            "type": "A",
            "ttl": 300,
            "records": ["192.0.2.1"]
        }
    ]
}
📌 Explanation:

Defines a public hosted zone for mywebsite.com.

Creates an A record (www.mywebsite.com → 192.0.2.1).

🔹 Private Hosted Zone for VPC
Creates a private hosted zone linked to a VPC for internal DNS resolution.

json
Copy
Edit
{
    "stack_id": "route53-stack",
    "resource_prefix": "example",
    "aws_region": "us-east-1",

    "resources": [
        {
            "resource_type": "aws_route53_zone",
            "resource_id": "private-zone",
            "name": "internal.mycompany.com",
            "visibility": "private",
            "vpc": {
                "vpc_id": "vpc-12345678"
            },
            "tags": {
                "env": "staging"
            }
        }
    ]
}
📌 Explanation:

A private hosted zone only accessible within the specified VPC.

Useful for internal service discovery within AWS.

🔹 Weighted Routing
Directs traffic based on assigned weights (e.g., A record with 70% and 30% split).

json
Copy
Edit
{
    "stack_id": "route53-stack",
    "resource_prefix": "example",
    "aws_region": "us-east-1",

    "resources": [
        {
            "resource_type": "aws_route53_record",
            "resource_id": "weighted-record1",
            "zone_id": "Z123456789",
            "name": "www.mywebsite.com",
            "type": "A",
            "ttl": 300,
            "records": ["192.0.2.1"],
            "set_identifier": "primary",
            "weight": 70
        },
        {
            "resource_type": "aws_route53_record",
            "resource_id": "weighted-record2",
            "zone_id": "Z123456789",
            "name": "www.mywebsite.com",
            "type": "A",
            "ttl": 300,
            "records": ["192.0.2.2"],
            "set_identifier": "secondary",
            "weight": 30
        }
    ]
}
📌 Explanation:

Weighted routing splits traffic between two IPs (70% and 30%).

Useful for gradual rollouts or A/B testing.

🔹 Failover Routing
Routes traffic to a primary instance, and switches to secondary when the primary fails.

json
Copy
Edit
{
    "stack_id": "route53-stack",
    "resource_prefix": "example",
    "aws_region": "us-east-1",

    "resources": [
        {
            "resource_type": "aws_route53_record",
            "resource_id": "primary-record",
            "zone_id": "Z123456789",
            "name": "www.mywebsite.com",
            "type": "A",
            "ttl": 300,
            "records": ["192.0.2.1"],
            "set_identifier": "primary",
            "failover_routing_policy": "PRIMARY",
            "health_check_id": "hc-12345"
        },
        {
            "resource_type": "aws_route53_record",
            "resource_id": "secondary-record",
            "zone_id": "Z123456789",
            "name": "www.mywebsite.com",
            "type": "A",
            "ttl": 300,
            "records": ["192.0.2.2"],
            "set_identifier": "secondary",
            "failover_routing_policy": "SECONDARY"
        }
    ]
}
📌 Explanation:

Primary traffic goes to 192.0.2.1.

If it fails the health check, traffic shifts to 192.0.2.2.

🔹 Latency-Based Routing
Routes users to the nearest AWS region for lower latency.

json
Copy
Edit
{
    "stack_id": "route53-stack",
    "resource_prefix": "example",
    "aws_region": "us-east-1",

    "resources": [
        {
            "resource_type": "aws_route53_record",
            "resource_id": "us-east",
            "zone_id": "Z123456789",
            "name": "www.mywebsite.com",
            "type": "A",
            "ttl": 300,
            "records": ["192.0.2.1"],
            "set_identifier": "us-east",
            "latency_routing_policy": "us-east-1"
        },
        {
            "resource_type": "aws_route53_record",
            "resource_id": "us-west",
            "zone_id": "Z123456789",
            "name": "www.mywebsite.com",
            "type": "A",
            "ttl": 300,
            "records": ["192.0.2.2"],
            "set_identifier": "us-west",
            "latency_routing_policy": "us-west-2"
        }
    ]
}
📌 Explanation:

Directs users to the nearest AWS region.

Users from the East Coast → 192.0.2.1 (us-east-1).

Users from the West Coast → 192.0.2.2 (us-west-2).

Argument References
Required
name - (string) Name of the hosted zone.

Optional
comment - (string) Description of the hosted zone.

visibility - (string) Either public or private.

vpc - (object) Required for private zones (includes vpc_id).

record_type - (string) Type of DNS record (A, CNAME, MX, etc.).

ttl - (number) Time in seconds before record expiration.

records - (list) List of IP addresses or values.

routing_policy - (string) Defines routing type (failover, latency, weighted).

tags - (map) Key-value tags.

This documentation follows the same structured format as your ECR one and includes detailed explanations for each function. Let me know if you need any modifications! 