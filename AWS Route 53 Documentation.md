AWS Route 53 Documentation
Resource: aws_route53
Provides an AWS Route 53 resource for managing DNS records within a hosted zone. This documentation covers creating A records, CNAME records, Weighted Routing, and Geo-Proximity Routing.

For more details, see AWS Route 53 Documentation.

Example Usage
1️⃣ Private Hosted Zone
Creates a private hosted zone for internal domain resolution.

json
Copy
Edit
{
    "stack_id": "route53-stack",
    "resource_prefix": "my-app",
    "aws_region": "us-west-2",
    "resources": [
        {
            "resource_type": "aws_route53",
            "resource_id": "private_zone",
            "zone_name": "example.internal",
            "vpc_id": "vpc-12345678"
        }
    ]
}
2️⃣ A Record (Alias to ALB/NLB)
Creates an A record pointing to an Application Load Balancer (ALB) or Network Load Balancer (NLB).

json
Copy
Edit
{
    "stack_id": "route53-stack",
    "resource_prefix": "my-app",
    "aws_region": "us-west-2",
    "resources": [
        {
            "resource_type": "aws_route53",
            "resource_id": "a_record",
            "zone_id": "Z123456789ABCDEFG",
            "records": [
                {
                    "record_name": "app.example.com",
                    "record_type": "A",
                    "is_alias": true,
                    "load_balancer_arn": "arn:aws:elasticloadbalancing:us-west-2:123456789012:loadbalancer/app/my-alb/1234567890abcdef"
                }
            ]
        }
    ]
}
3️⃣ CNAME Record
Creates a CNAME record that maps one domain to another.

json
Copy
Edit
{
    "stack_id": "route53-stack",
    "resource_prefix": "my-app",
    "aws_region": "us-west-2",
    "resources": [
        {
            "resource_type": "aws_route53",
            "resource_id": "cname_record",
            "zone_id": "Z123456789ABCDEFG",
            "records": [
                {
                    "record_name": "www.example.com",
                    "record_type": "CNAME",
                    "target_dns_name": "example.com"
                }
            ]
        }
    ]
}
4️⃣ Weighted Routing
Creates weighted routing to distribute traffic across multiple endpoints.

json
Copy
Edit
{
    "stack_id": "route53-stack",
    "resource_prefix": "my-app",
    "aws_region": "us-west-2",
    "resources": [
        {
            "resource_type": "aws_route53",
            "resource_id": "weighted_record",
            "zone_id": "Z123456789ABCDEFG",
            "records": [
                {
                    "record_name": "api.example.com",
                    "record_type": "A",
                    "load_balancer_dns": "alb-1234567890.us-west-2.elb.amazonaws.com",
                    "lb_hosted_zone_id": "Z3AADJGX6KTTL2",
                    "weight": 50
                },
                {
                    "record_name": "api.example.com",
                    "record_type": "A",
                    "load_balancer_dns": "alb-0987654321.us-west-2.elb.amazonaws.com",
                    "lb_hosted_zone_id": "Z3AADJGX6KTTL2",
                    "weight": 50
                }
            ]
        }
    ]
}
5️⃣ Geo-Proximity Routing
Routes traffic based on the geographical proximity of users.

json
Copy
Edit
{
    "stack_id": "route53-stack",
    "resource_prefix": "my-app",
    "aws_region": "us-west-2",
    "resources": [
        {
            "resource_type": "aws_route53",
            "resource_id": "geo_proximity_record",
            "zone_id": "Z123456789ABCDEFG",
            "records": [
                {
                    "record_name": "geo.example.com",
                    "record_type": "A",
                    "load_balancer_dns": "alb-1234567890.us-west-2.elb.amazonaws.com",
                    "lb_hosted_zone_id": "Z3AADJGX6KTTL2",
                    "geo_proximity_aws_region": "us-west-2",
                    "bias": 10
                }
            ]
        }
    ]
}
Usage Recommendations
Use Private Hosted Zones for internal applications.

Enable Weighted Routing to distribute traffic between multiple endpoints.

Utilize Geo-Proximity Routing for regional load balancing.

Create CNAME Records to simplify domain management.

Argument References
Required
zone_id - (string) The ID of the Route 53 hosted zone.

record_name – (string) The domain name for the record.

record_type – (string) The type of DNS record (A, CNAME, etc.).

Optional
is_alias – (boolean) If true, the record is an alias to another AWS resource.

load_balancer_arn – (string) The ARN of an ALB/NLB.

load_balancer_dns – (string) The DNS name of the ALB/NLB.

lb_hosted_zone_id – (string) Hosted Zone ID of the ALB/NLB.

target_dns_name – (string) The DNS name for CNAME records.

weight – (integer) Weight for weighted routing.

geo_proximity_aws_region – (string) AWS region for geo-proximity routing.

bias – (integer) Bias for geo-proximity routing.

Attribute References
This resource exports the following attributes:

hosted_zone_id – The ID of the hosted zone.

record_set_id – The ID of the created record set.

record_fqdn – The fully qualified domain name (FQDN) of the record.


















1️⃣ Private Hosted Zone
📌 What is it?
A private hosted zone is a DNS zone that is only accessible within a specific Amazon VPC. This is useful for internal applications where you don’t want the DNS records to be publicly accessible.

🛠 When to use it?
When you need internal DNS resolution for applications inside a VPC.

When you want to keep domain records private (not exposed to the public internet).

📄 Example
This creates a private hosted zone for the domain example.internal, only accessible inside the specified VPC.

json
Copy
Edit
{
    "resource_type": "aws_route53",
    "resource_id": "private_zone",
    "zone_name": "example.internal",
    "vpc_id": "vpc-12345678"
}
2️⃣ A Record (Alias to ALB/NLB)
📌 What is it?
An A record maps a domain name to an IPv4 address.
AWS Route 53 allows alias records, which means an A record can directly point to an AWS resource (like an ALB or NLB) without needing an explicit IP address.

🛠 When to use it?
When you need to point a domain name (e.g., app.example.com) to an Application Load Balancer (ALB) or Network Load Balancer (NLB).

When you don’t want to manually update IP addresses (since ALBs and NLBs can change IPs dynamically).

📄 Example
This creates an A record pointing to an ALB.

json
Copy
Edit
{
    "resource_type": "aws_route53",
    "resource_id": "a_record",
    "zone_id": "Z123456789ABCDEFG",
    "records": [
        {
            "record_name": "app.example.com",
            "record_type": "A",
            "is_alias": true,
            "load_balancer_arn": "arn:aws:elasticloadbalancing:us-west-2:123456789012:loadbalancer/app/my-alb/1234567890abcdef"
        }
    ]
}
3️⃣ CNAME Record
📌 What is it?
A CNAME (Canonical Name) record maps a domain name to another domain name instead of an IP address.

🛠 When to use it?
When you want to redirect a subdomain (e.g., www.example.com) to another domain (e.g., example.com).

When you need to point a domain to a third-party service (e.g., CloudFront, S3 Static Website, or an external hosting provider).

📄 Example
This creates a CNAME record that makes www.example.com point to example.com.

json
Copy
Edit
{
    "resource_type": "aws_route53",
    "resource_id": "cname_record",
    "zone_id": "Z123456789ABCDEFG",
    "records": [
        {
            "record_name": "www.example.com",
            "record_type": "CNAME",
            "target_dns_name": "example.com"
        }
    ]
}
4️⃣ Weighted Routing
📌 What is it?
Weighted Routing allows you to distribute traffic between multiple endpoints based on assigned weights.

🛠 When to use it?
When you want to gradually shift traffic between two versions of an application.

When you need load distribution across different AWS regions or instances.

When implementing blue-green deployments or A/B testing.

📄 Example
This splits traffic 50-50 between two ALBs.

json
Copy
Edit
{
    "resource_type": "aws_route53",
    "resource_id": "weighted_record",
    "zone_id": "Z123456789ABCDEFG",
    "records": [
        {
            "record_name": "api.example.com",
            "record_type": "A",
            "load_balancer_dns": "alb-1234567890.us-west-2.elb.amazonaws.com",
            "lb_hosted_zone_id": "Z3AADJGX6KTTL2",
            "weight": 50
        },
        {
            "record_name": "api.example.com",
            "record_type": "A",
            "load_balancer_dns": "alb-0987654321.us-west-2.elb.amazonaws.com",
            "lb_hosted_zone_id": "Z3AADJGX6KTTL2",
            "weight": 50
        }
    ]
}
5️⃣ Geo-Proximity Routing
📌 What is it?
Geo-Proximity Routing sends users to the closest AWS region based on their location.
It allows bias adjustments, meaning you can increase or decrease the likelihood of sending users to a specific region.

🛠 When to use it?
When running multi-region applications and want users to be directed to the nearest AWS region.

When needing low-latency access for global users.

When controlling traffic to balance the load across regions.

📄 Example
This directs traffic to an AWS region closest to the user with a bias of +10.

json
Copy
Edit
{
    "resource_type": "aws_route53",
    "resource_id": "geo_proximity_record",
    "zone_id": "Z123456789ABCDEFG",
    "records": [
        {
            "record_name": "geo.example.com",
            "record_type": "A",
            "load_balancer_dns": "alb-1234567890.us-west-2.elb.amazonaws.com",
            "lb_hosted_zone_id": "Z3AADJGX6KTTL2",
            "geo_proximity_aws_region": "us-west-2",
            "bias": 10
        }
    ]
}
🌟 Summary of Use Cases
Use Case	Description	Example
Private Hosted Zone	Internal DNS resolution inside a VPC	example.internal
A Record (Alias)	Points a domain to an ALB/NLB	app.example.com → ALB
CNAME Record	Maps one domain to another	www.example.com → example.com
Weighted Routing	Distributes traffic across multiple resources	50% to ALB-1, 50% to ALB-2
Geo-Proximity Routing	Routes users based on their location	Users in US → us-west-2
🚀 Key Takeaways
Private Hosted Zones are for internal applications inside a VPC.

A Records (Alias) are for pointing domains to ALBs/NLBs.

CNAME Records allow domain redirection.

Weighted Routing is for traffic distribution across endpoints.

Geo-Proximity Routing directs users to the nearest AWS region.



modofications-----------------


{
    "stack_id": "route53-stack",
    "resource_prefix": "my-app",
    "aws_region": "us-west-2",
    "resources": [
        {
            "resource_type": "aws_route53",
            "resource_id": "weighted_record",
            "zone_id": "Z123456789ABCDEFG",
            "records": [
                {
                    "record_name": "api.example.com",
                    "record_type": "A",
                    "load_balancer_dns": "${aws_lb.dns_name}",
                    "lb_hosted_zone_id": "${aws_lb.zone_id}",
                    "weight": 50
                },
                {
                    "record_name": "api.example.com",
                    "record_type": "A",
                    "load_balancer_dns": "alb-0987654321.us-west-2.elb.amazonaws.com",
                    "lb_hosted_zone_id": "Z3AADJGX6KTTL2",
                    "weight": 50
                }
            ]
        }
    ]
}


Optional Arguments
is_alias (boolean) – If true, the record is an alias to another AWS resource.

load_balancer_arn (string) – The ARN of an ALB/NLB.

load_balancer_dns (string) – The DNS name of the ALB/NLB.
✅ New: Supports dynamic placeholder ${aws_lb.dns_name} to fetch ALB DNS automatically.

lb_hosted_zone_id (string) – The hosted zone ID of the ALB/NLB.
✅ New: Supports dynamic placeholder ${aws_lb.zone_id} to fetch ALB Hosted Zone ID automatically.

target_dns_name (string) – The DNS name for CNAME records.

weight (integer) – Weight for weighted routing.

geo_proximity_aws_region (string) – AWS region for geo-proximity routing.

bias (integer) – Bias for geo-proximity routing.

✅ New Additions in Attribute References
Since ${aws_lb.dns_name} and ${aws_lb.zone_id} dynamically fetch values, I added them under Attribute References too.

Updated Attribute References
This resource exports the following attributes:

hosted_zone_id – The ID of the hosted zone.

record_set_id – The ID of the created record set.

record_fqdn – The fully qualified domain name (FQDN) of the record.

✅ New: load_balancer_dns – Fetches the ALB DNS Name when ${aws_lb.dns_name} is used.

✅ New: lb_hosted_zone_id – Fetches the ALB Hosted Zone ID when ${aws_lb.zone_id} is used.

🔥 Summary of Enhancements
✅ Added ${aws_lb.dns_name} and ${aws_lb.zone_id} as optional arguments.

✅ Updated explanations in the Argument References section.

✅ Included new attributes in the Attribute References section.
