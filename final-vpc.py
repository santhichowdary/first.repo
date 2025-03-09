import boto3
import os
import argparse
import mpe_utils
from botocore.exceptions import ClientError

# Initialize EC2 client
AWS_REGION = os.getenv('AWS_REGION', None)
if not AWS_REGION:
    session = boto3.Session()
    AWS_REGION = session.region_name

ec2 = boto3.client('ec2', region_name=AWS_REGION)

def list_all_vpc_endpoints():
    """List all VPC Endpoints in the region."""
    try:
        response = ec2.describe_vpc_endpoints()
        return response.get('VpcEndpoints', [])
    except ClientError as e:
        mpe_utils.log_error(f"Error fetching VPC Endpoints: {e}")
        return []

def check_for_active_vpc_endpoint(endpoint_id):
    """Check if a VPC endpoint has active route tables or subnets."""
    try:
        response = ec2.describe_vpc_endpoints(VpcEndpointIds=[endpoint_id])
        endpoint = response['VpcEndpoints'][0]
        route_tables = endpoint.get('RouteTableIds', [])
        subnets = endpoint.get('SubnetIds', [])
        return bool(route_tables or subnets), route_tables, subnets
    except ClientError as e:
        mpe_utils.log_error(f"Error fetching details for VPC Endpoint {endpoint_id}: {e}")
        return False, [], []

def delete_vpc_endpoint(endpoint_id):
    """Delete a VPC endpoint if no active dependencies exist."""
    active, route_tables, subnets = check_for_active_vpc_endpoint(endpoint_id)
    if active:
        mpe_utils.log_warning(f"Cannot delete VPC Endpoint {endpoint_id}: Active dependencies exist.")
        mpe_utils.log_warning(f"  - Route Tables: {route_tables}")
        mpe_utils.log_warning(f"  - Subnets: {subnets}")
        return
    
    try:
        ec2.delete_vpc_endpoints(VpcEndpointIds=[endpoint_id])
        mpe_utils.log_info(f"Deleted VPC Endpoint: {endpoint_id}")
    except ClientError as e:
        mpe_utils.log_error(f"Failed to delete VPC Endpoint {endpoint_id}: {e}")

def main():
    """Main function to handle input parameters and process VPC Endpoints."""
    parser = argparse.ArgumentParser(description="Manage AWS VPC Endpoints")
    parser.add_argument('-i', '--input', required=True, help="Specify 'ALL' or a file containing VPC Endpoint IDs")
    parser.add_argument('-a', '--action', choices=['DELETE'], help="Specify DELETE to remove VPC Endpoints")
    args = parser.parse_args()
    
    mpe_utils.setup_logging()
    input_param = args.input.lower()
    action = args.action
    deletable_endpoints = []
    
    if input_param == "all":
        all_endpoints = list_all_vpc_endpoints()
        
        if not all_endpoints:
            mpe_utils.log_info("No VPC Endpoints found in the region.")
            return

        for endpoint in all_endpoints:
            endpoint_id = endpoint['VpcEndpointId']
            active, route_tables, subnets = check_for_active_vpc_endpoint(endpoint_id)
            mpe_utils.log_info(f"VPC Endpoint: {endpoint_id} | Active Routes: {route_tables} | Active Subnets: {subnets}")
            deletable_endpoints.append(endpoint_id)

         
              
    
    elif os.path.isfile(input_param):
        with open(input_param, 'r') as file:
            endpoint_ids = [line.strip() for line in file.readlines() if line.strip()]
        
        if not endpoint_ids:
            mpe_utils.log_error("Input file is empty or contains invalid data.")
            return
        
        all_endpoints = list_all_vpc_endpoints()
        all_endpoint_ids = {ep['VpcEndpointId'] for ep in all_endpoints}
        
        for endpoint_id in endpoint_ids:
            if endpoint_id in all_endpoint_ids:
                active, route_tables, subnets = check_for_active_vpc_endpoint(endpoint_id)
                mpe_utils.log_info(f"VPC Endpoint: {endpoint_id} | Active Routes: {route_tables} | Active Subnets: {subnets}")
                deletable_endpoints.append(endpoint_id)
            



            else:
                mpe_utils.log_error(f"Invalid VPC Endpoint: {endpoint_id}")
    else:
        mpe_utils.log_error(f"Invalid input: {input_param} is not a valid file.")
        return
    
    if action == "DELETE":
        for endpoint_id in deletable_endpoints:
            delete_vpc_endpoint(endpoint_id)

if __name__ == "__main__":
    main()
