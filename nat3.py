import boto3
import argparse
import os
import time
from botocore.exceptions import ClientError

# Set AWS region from environment variable or session
AWS_REGION = os.getenv('AWS_REGION', None)
if not AWS_REGION:
    session = boto3.Session()
    AWS_REGION = session.region_name

def describe_nat_gateways():
    ec2_client = boto3.client('ec2', region_name=AWS_REGION)
    try:
        response = ec2_client.describe_nat_gateways()
        return response['NatGateways']
    except ClientError as e:
        print(f"ERROR: Unable to fetch NAT Gateways: {e}")
        return []

def check_route_tables(nat_gateway_id):
    ec2_client = boto3.client('ec2', region_name=AWS_REGION)
    try:
        response = ec2_client.describe_route_tables(
            Filters=[{'Name': 'route.nat-gateway-id', 'Values': [nat_gateway_id]}]
        )
        return response['RouteTables']
    except ClientError:
        return []

def wait_for_nat_deletion(nat_gateway_id):
    """
    Waits for NAT Gateway to be fully deleted before releasing the Elastic IP.
    """
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
        time.sleep(10)

def release_elastic_ip(allocation_id):
    """
    Releases the specified Elastic IP.
    """
    ec2_client = boto3.client('ec2', region_name=AWS_REGION)
    try:
        ec2_client.release_address(AllocationId=allocation_id)
        print(f"SUCCESS: Released Elastic IP: {allocation_id}")
    except ClientError as e:
        print(f"ERROR: Failed to release Elastic IP {allocation_id}: {e}")

def delete_nat_gateway(nat_gateway_id):
    ec2_client = boto3.client('ec2', region_name=AWS_REGION)
    route_tables = check_route_tables(nat_gateway_id)
    
    if route_tables:
        print(f"ERROR: Cannot delete NAT Gateway {nat_gateway_id} as it has associated route tables.")
        for rt in route_tables:
            print(f"  - Route Table: {rt['RouteTableId']}")
        return
    
    try:
        # Fetch NAT details before deletion (to get Elastic IP)
        nat_details = ec2_client.describe_nat_gateways(
            Filters=[{'Name': 'nat-gateway-id', 'Values': [nat_gateway_id]}]
        )['NatGateways'][0]

        allocation_id = nat_details.get('NatGatewayAddresses', [{}])[0].get('AllocationId')

        # Delete NAT Gateway
        ec2_client.delete_nat_gateway(NatGatewayId=nat_gateway_id)
        print(f"SUCCESS: Deleting NAT Gateway: {nat_gateway_id}")

        # Wait for NAT Gateway to be fully deleted
        wait_for_nat_deletion(nat_gateway_id)

        # Release Elastic IP if available
        if allocation_id:
            release_elastic_ip(allocation_id)

    except ClientError as e:
        print(f"ERROR: Failed to delete NAT Gateway {nat_gateway_id}: {e}")

def main():
    parser = argparse.ArgumentParser(description="Manage AWS NAT Gateways")
    parser.add_argument('-i', '--input', required=True, help="Specify 'all' or a filename containing NAT Gateway IDs")
    parser.add_argument('-a', '--action', choices=['DELETE'], help="Specify DELETE to remove NAT Gateways")
    args = parser.parse_args()
    
    param = args.input.lower()
    action = args.action
    deletable_nats = []
    
    if param == "all":
        print("\n------------------------------------------------------------")
        print("               LISTING ALL NAT GATEWAYS                     ")
        print("------------------------------------------------------------\n")
        
        all_nat_gateways = describe_nat_gateways()
        if not all_nat_gateways:
            print("No NAT Gateways found in the region.")
            return
        
        for nat in all_nat_gateways:
            nat_id = nat['NatGatewayId']
            state = nat['State']
            allocation_id = nat.get('NatGatewayAddresses', [{}])[0].get('AllocationId')
            route_tables = check_route_tables(nat_id)
            route_info = ', '.join([rt['RouteTableId'] for rt in route_tables]) if route_tables else "No associated Route Tables"
            
            print(f"NAT Gateway: {nat_id} | State: {state} | Elastic IP: {allocation_id if allocation_id else 'None'} | Routes: {route_info}")
            
            if not route_tables and state != 'deleted':
                deletable_nats.append(nat_id)
                if action != "DELETE":
                    print(f"INFO: {nat_id} can be deleted safely.")
                    print("To DELETE, Please pass -a DELETE as 2nd argument.")

    elif os.path.isfile(param):  # Handling input file
        with open(param, 'r') as file:
            nat_ids = [line.strip() for line in file.readlines()]
        
        all_nat_gateways = describe_nat_gateways()
        found_nat_ids = {nat['NatGatewayId']: nat for nat in all_nat_gateways}  # Store all NATs for quick lookup

        for nat_id in nat_ids:
            if nat_id in found_nat_ids:
                nat = found_nat_ids[nat_id]
                state = nat['State']
                allocation_id = nat.get('NatGatewayAddresses', [{}])[0].get('AllocationId', 'None')
                route_tables = check_route_tables(nat_id)
                route_info = ', '.join([rt['RouteTableId'] for rt in route_tables]) if route_tables else "No associated Route Tables"

                print("\n------------------------------------------------------------")
                print(f" NAT Gateway ID  : {nat_id}")
                print(f" Status          : {state}")
                print(f" Elastic IP      : {allocation_id}")
                print(f" Route Tables    : {route_info}")
                print("------------------------------------------------------------")

                if not route_tables and state != 'deleted':
                    deletable_nats.append(nat_id)
                    if action != "DELETE":
                        print(f"INFO: {nat_id} can be deleted safely.")
                        print("To DELETE, Please pass -a DELETE as 2nd argument.")
            else:
                print(f"ERROR: Invalid NAT Gateway ID: {nat_id}")

    else:
        print(f"ERROR: The file '{param}' does not exist. Please provide a valid file name.")
        return

    if action == "DELETE":
        for nat_id in deletable_nats:
            delete_nat_gateway(nat_id)

if __name__ == "__main__":
    main()
