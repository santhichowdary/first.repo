AWS EventBridge Documentation
Overview
Amazon EventBridge is a serverless event bus that enables applications to communicate using events.
This documentation covers the creation of EventBridge event buses, rules, targets, and EventBridge Connections.

Example Usage
1. EventBridge Event Bus
Creates a custom event bus to manage events for your application.

json
Copy
Edit
{
    "resource_type": "aws_eventbridge_bus",
    "resource_id": "my-custom-bus",
    "name": "my-app-event-bus"
}
2. EventBridge Rule
Defines an EventBridge rule to match incoming events based on a pattern and route them to targets.

json
Copy
Edit
{
    "resource_type": "aws_eventbridge_rule",
    "resource_id": "my-event-rule",
    "event_bus_name": "my-app-event-bus",
    "event_pattern": {
        "source": ["my.application"],
        "detail-type": ["order_placed"]
    },
    "targets": [
        {
            "arn": "arn:aws:lambda:us-west-2:123456789012:function:myLambdaFunction",
            "id": "TargetLambda"
        }
    ]
}
3. EventBridge Connection
Creates a connection resource for API destinations, with authentication.

json
Copy
Edit
{
    "resource_type": "aws_eventbridge_connection",
    "resource_id": "my-connection",
    "authorization_type": "API_KEY",
    "auth_parameters": {
        "api_key_name": "x-api-key",
        "api_key_value": "your-api-key-value"
    },
    "description": "Connection for external API"
}
Usage Recommendations
Use Custom Buses: Helps separate domain-specific events.

Secure Connections: Use appropriate authentication (API Key, OAuth, Basic Auth) when creating EventBridge connections.

Target Lambda or SQS: Depending on event handling needs.

Use Dead Letter Queues: In case of delivery failures.

Argument References
Required

Argument	Type	Description
resource_type	string	Type of resource (aws_eventbridge_bus, aws_eventbridge_rule, aws_eventbridge_connection).
resource_id	string	Unique identifier for the resource.
name	string	Name of the EventBridge bus (for bus).
event_pattern	map	Pattern to match events (for rule).
targets	list	List of targets for the rule (for rule).
authorization_type	string	Authorization type for connection (for connection).
Optional

Argument	Type	Description
event_bus_name	string	Name of the event bus associated with the rule.
auth_parameters	map	Authentication parameters for connections.
description	string	Description for the EventBridge connection.
Attribute References

Attribute	Description
event_bus_arn	ARN of the created Event Bus.
rule_arn	ARN of the created EventBridge Rule.
connection_arn	ARN of the created EventBridge Connection.
🔥 Notes
EventBridge Connection is only used when sending events to external APIs.

You don't need a connection for Lambda, Step Functions, SNS, or SQS targets.

For more complex event filtering, use content-based filtering inside the event pattern.