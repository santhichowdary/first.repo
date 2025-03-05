import boto3
import argparse
import os
import time
import mpe_utils  # Importing mpe_utils for logging
from botocore.exceptions import ClientError

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
        mpe_utils.log_error(f"Unable to fetch NAT Gateways: {e}")
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
    ec2_client = boto3.client('ec2', region_name=AWS_REGION)
    mpe_utils.log_info(f"Waiting for NAT Gateway {nat_gateway_id} to be deleted...")
    while True:
        try:
            response = ec2_client.describe_nat_gateways(
                Filters=[{'Name': 'nat-gateway-id', 'Values': [nat_gateway_id]}]
            )
            if not response['NatGateways'] or response['NatGateways'][0]['State'] == 'deleted':
                mpe_utils.log_info(f"NAT Gateway {nat_gateway_id} is fully deleted.")
                break
        except ClientError as e:
            mpe_utils.log_error(f"Error checking NAT Gateway status: {e}")
            break
        time.sleep(10)

def release_elastic_ip(allocation_id):
    ec2_client = boto3.client('ec2', region_name=AWS_REGION)
    try:
        ec2_client.release_address(AllocationId=allocation_id)
        mpe_utils.log_info(f"Released Elastic IP: {allocation_id}")
    except ClientError as e:
        mpe_utils.log_error(f"Failed to release Elastic IP {allocation_id}: {e}")

def delete_nat_gateway(nat_gateway_id):
    ec2_client = boto3.client('ec2', region_name=AWS_REGION)
    route_tables = check_route_tables(nat_gateway_id)
    
    if route_tables:
        mpe_utils.log_error(f"Cannot delete NAT Gateway {nat_gateway_id} as it has associated route tables.")
        for rt in route_tables:
            mpe_utils.log_info(f"  - Route Table: {rt['RouteTableId']}")
        return
    
    try:
        nat_details = ec2_client.describe_nat_gateways(
            Filters=[{'Name': 'nat-gateway-id', 'Values': [nat_gateway_id]}]
        )['NatGateways'][0]

        allocation_id = nat_details.get('NatGatewayAddresses', [{}])[0].get('AllocationId') if nat_details.get('NatGatewayAddresses') else None

        ec2_client.delete_nat_gateway(NatGatewayId=nat_gateway_id)
        mpe_utils.log_info(f"Deleting NAT Gateway: {nat_gateway_id}")

        wait_for_nat_deletion(nat_gateway_id)

        if allocation_id:
            release_elastic_ip(allocation_id)
    except ClientError as e:
        mpe_utils.log_error(f"Failed to delete NAT Gateway {nat_gateway_id}: {e}")

def main():
    parser = argparse.ArgumentParser(description="Manage AWS NAT Gateways")
    parser.add_argument('-i', '--input', required=True, help="Specify 'all' or a filename containing NAT Gateway IDs")
    parser.add_argument('-a', '--action', choices=['DELETE'], help="Specify DELETE to remove NAT Gateways")
    args = parser.parse_args()
    
    mpe_utils.setup_logging()
    
    param = args.input.lower()
    action = args.action
    deletable_nats = []
    
    if param == "all":
        mpe_utils.log_info("Listing all NAT Gateways...")
        all_nat_gateways = describe_nat_gateways()
        if not all_nat_gateways:
            mpe_utils.log_info("No NAT Gateways found in the region.")
            return
        
        for nat in all_nat_gateways:
            nat_id = nat['NatGatewayId']
            state = nat['State']
            allocation_id = nat.get('NatGatewayAddresses', [{}])[0].get('AllocationId') if nat.get('NatGatewayAddresses') else None
            route_tables = check_route_tables(nat_id)
            route_info = ', '.join([rt['RouteTableId'] for rt in route_tables]) if route_tables else "No associated Route Tables"
            
            mpe_utils.log_info(f"NAT Gateway: {nat_id} | State: {state} | Elastic IP: {allocation_id if allocation_id else 'None'} | Routes: {route_info}")
            
            if not route_tables and state != 'deleted':
                deletable_nats.append(nat_id)
    elif os.path.isfile(param):
        with open(param, 'r') as file:
            nat_ids = [line.strip() for line in file.readlines()]
        
        all_nat_gateways = describe_nat_gateways()
        found_nat_ids = {nat['NatGatewayId']: nat for nat in all_nat_gateways}
        
        for nat_id in nat_ids:
            if nat_id in found_nat_ids:
                nat = found_nat_ids[nat_id]
                state = nat['State']
                allocation_id = nat.get('NatGatewayAddresses', [{}])[0].get('AllocationId') if nat.get('NatGatewayAddresses') else None
                route_tables = check_route_tables(nat_id)
                route_info = ', '.join([rt['RouteTableId'] for rt in route_tables]) if route_tables else "No associated Route Tables"

                mpe_utils.log_info(f"NAT Gateway ID: {nat_id} | Status: {state} | Elastic IP: {allocation_id} | Route Tables: {route_info}")

                if not route_tables and state != 'deleted':
                    deletable_nats.append(nat_id)
            else:
                mpe_utils.log_error(f"Invalid NAT Gateway ID: {nat_id}")
    else:
        mpe_utils.log_error(f"The file '{param}' does not exist. Please provide a valid file name.")
        return

    if action == "DELETE":
        for nat_id in deletable_nats:
            delete_nat_gateway(nat_id)

if __name__ == "__main__":
    main()
