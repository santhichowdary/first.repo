import boto3
import sys
import time
from botocore.exceptions import ClientError

# Specify your AWS region
AWS_REGION = 'us-east-1'  # Change this to your AWS region if needed

def describe_nat_gateways():
    """Fetches all NAT Gateways from AWS."""
    ec2_client = boto3.client('ec2', region_name=AWS_REGION)
    response = ec2_client.describe_nat_gateways()
    return response['NatGateways']

def check_route_tables(nat_gateway_id):
    """Checks if a NAT Gateway is associated with any route tables."""
    ec2_client = boto3.client('ec2', region_name=AWS_REGION)
    response = ec2_client.describe_route_tables(
        Filters=[{'Name': 'route.nat-gateway-id', 'Values': [nat_gateway_id]}]
    )
    return response['RouteTables']

def delete_nat_gateway(nat_gateway_id):
    """Deletes the specified NAT Gateway."""
    ec2_client = boto3.client('ec2', region_name=AWS_REGION)
    try:
        ec2_client.delete_nat_gateway(NatGatewayId=nat_gateway_id)
        print(f"Deleted NAT Gateway with ID: {nat_gateway_id}")
    except ClientError as e:
        print(f"Error deleting NAT Gateway {nat_gateway_id}: {e}")

def wait_for_nat_deletion(nat_gateway_id):
    """Waits for NAT Gateway to be fully deleted before releasing the Elastic IP."""
    ec2_client = boto3.client('ec2', region_name=AWS_REGION)
    print(f"Waiting for NAT Gateway {nat_gateway_id} to be deleted...")

    while True:
        try:
            response = ec2_client.describe_nat_gateways(
                Filters=[{'Name': 'nat-gateway-id', 'Values': [nat_gateway_id]}]
            )
            if not response['NatGateways'] or response['NatGateways'][0]['State'] == 'deleted':
                print(f"NAT Gateway {nat_gateway_id} is fully deleted.")
                break
        except ClientError as e:
            print(f"Error checking NAT Gateway status: {e}")
            break
        time.sleep(10)  # Check every 10 seconds

def release_elastic_ip(allocation_id):
    """Releases the specified Elastic IP."""
    ec2_client = boto3.client('ec2', region_name=AWS_REGION)
    try:
        ec2_client.release_address(AllocationId=allocation_id)
        print(f"Released Elastic IP with Allocation ID: {allocation_id}")
    except ClientError as e:
        print(f"Error releasing Elastic IP {allocation_id}: {e}")

def get_nat_details_from_file(filename):
    """Reads NAT Gateway IDs from a file and fetches details if they exist."""
    try:
        with open(filename, 'r') as file:
            nat_ids = [line.strip() for line in file.readlines()]
    except FileNotFoundError:
        print(f"Error: The file '{filename}' was not found.")
        return None

    if not nat_ids:
        print("Error: The input file is empty.")
        return None

    all_nat_gateways = describe_nat_gateways()
    found_nat_gateways = []
    unmatched_nats = []

        
    print("\n")

    for nat_id in nat_ids:
        found = False
        for nat_gateway in all_nat_gateways:
            if nat_id == nat_gateway['NatGatewayId']:
                state = nat_gateway['State']
                allocation_id = nat_gateway.get('NatGatewayAddresses', [{}])[0].get('AllocationId')
                route_tables = check_route_tables(nat_id)
                print(f"NAT Gateway ID: {nat_id}, State: {state}, Elastic IP: {allocation_id}, "
                      f"{'No associated Route Tables' if not route_tables else 'In use'}")
                
                if not route_tables and state != 'deleted':
                    found_nat_gateways.append((nat_id, allocation_id))
                
                found = True
                break

        if not found:
            unmatched_nats.append(nat_id)

    if unmatched_nats:
        print("\n------------------------------------------------------------")
        print("           INVALID NAT GATEWAY IDS FROM FILE                ")
        print("------------------------------------------------------------\n")
        for nat_id in unmatched_nats:
            print(f"Provide a correct NAT Gateway ID: {nat_id}")

    return found_nat_gateways

def main():
    """Main function to execute the script."""
    
    if len(sys.argv) < 2:
        print("\n------------------------------------------------------------")
        print("                SCRIPT USAGE INSTRUCTIONS                   ")
        print("------------------------------------------------------------\n")
        print("Usage: python script.py <ALL|filename> [delete]\n")
        
        print("Examples:")
        print("  1. List all NAT Gateways:         python script.py ALL")
        print("  2. List NAT Gateways from file:   python script.py <filename>.txt")
        print("  3. Delete NAT Gateways from file: python script.py <filename>.txt delete")
        print("\n------------------------------------------------------------\n")
        return

    param = sys.argv[1].upper()  # ALL or filename
    action = sys.argv[2].lower() if len(sys.argv) > 2 else None  # Optional delete argument

    if param == "ALL":
        print("\n------------------------------------------------------------")
        print("               LISTING ALL NAT GATEWAYS                     ")
        print("------------------------------------------------------------\n")
        all_nat_gateways = describe_nat_gateways()
        for nat_gateway in all_nat_gateways:
            nat_gateway_id = nat_gateway['NatGatewayId']
            state = nat_gateway['State']
            allocation_id = nat_gateway.get('NatGatewayAddresses', [{}])[0].get('AllocationId')
            print(f"NAT Gateway ID: {nat_gateway_id}, State: {state}, Elastic IP: {allocation_id if allocation_id else 'None'}")
        if action == "delete":
            print("\n Deleting all Nat_ids are not allowed! Specify a file instead.")    

    else:
        deletable_gateways = get_nat_details_from_file(param)

        if not deletable_gateways:
            print("\nNo NAT Gateways available for deletion.")
            return

        if action == 'delete':
            for nat_gateway_id, allocation_id in deletable_gateways:
                delete_nat_gateway(nat_gateway_id)
                wait_for_nat_deletion(nat_gateway_id)
                if allocation_id:
                    release_elastic_ip(allocation_id)
        else:
            print("\nNo deletion action specified.")

if __name__ == "__main__":
    main()





# AWS NAT Gateway Management Script

This Python script allows you to manage AWS NAT Gateways by listing, checking for associated route tables, and optionally deleting them if they are not in use.

## Features
- List all NAT Gateways in your AWS account.
- Check if a NAT Gateway is associated with any route tables.
- Delete NAT Gateways only if they have no associated route tables.
- Release associated Elastic IPs after NAT Gateway deletion.
- Read NAT Gateway IDs from a file for batch processing.
- Improved error handling with detailed messages, including associated route tables preventing deletion.

## Prerequisites
- Python 3.x installed.
- AWS CLI configured with appropriate permissions (`ec2:DescribeNatGateways`, `ec2:DescribeRouteTables`, `ec2:DeleteNatGateway`, `ec2:ReleaseAddress`).
- `boto3` library installed.

## Installation
1. Clone or download the script.
2. Install the required dependencies:
   ```sh
   pip install boto3
   ```
3. Ensure your AWS CLI is configured with:
   ```sh
   aws configure
   ```

## Usage

### List All NAT Gateways
```sh
python script.py ALL
```

### List NAT Gateways from a File
```sh
python script.py <filename>.txt
```

### Delete NAT Gateways from a File
```sh
python script.py <filename>.txt delete
```

### Example
File `nat_gateways.txt` contains:
```
nat-1234567890abcdef0
nat-0987654321abcdef1
```
Command:
```sh
python script.py nat_gateways.txt delete
```

### Important Notes
- NAT Gateways **will not be deleted** if they have associated route tables. The script will print the specific route table IDs preventing deletion.
- Deleting all NAT Gateways at once (using `ALL delete`) is **not allowed** to prevent accidental removal.
- Ensure AWS credentials have the necessary permissions before running the script.

## Error Handling
- If a NAT Gateway is still associated with route tables, the script prints:
  ```sh
  Skipping deletion of NAT Gateway nat-1234567890abcdef0: It is still associated with the following route tables: rtb-abcdef1234567890. Please remove these associations before attempting deletion.
  ```
- If the input file does not exist, an error message is displayed.
- If an invalid NAT Gateway ID is provided, the script identifies and notifies the user.

## License
This script is open-source and can be modified as needed. Use at your own risk.

## Author
Your Name (Modify as needed)


