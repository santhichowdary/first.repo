import boto3
import argparse
import os
import mpe_utils  # Importing mpe_utils for logging
from botocore.exceptions import ClientError

AWS_REGION = os.getenv('AWS_REGION')
if not AWS_REGION:
    session = boto3.Session()
    AWS_REGION = session.region_name

def describe_load_balancers():
    """Fetches ALB/NLB and Classic ELBs in the region."""
    elb_client = boto3.client('elbv2', region_name=AWS_REGION)
    classic_elb_client = boto3.client('elb', region_name=AWS_REGION)
    
    alb_nlb_load_balancers = []
    classic_load_balancers = []

    try:
        alb_nlb_response = elb_client.describe_load_balancers()
        alb_nlb_load_balancers = alb_nlb_response.get('LoadBalancers', [])
    except ClientError as e:
        mpe_utils.log_error(f"Failed to fetch ALB/NLBs: {e}")

    try:
        classic_response = classic_elb_client.describe_load_balancers()
        classic_load_balancers = classic_response.get('LoadBalancerDescriptions', [])
    except ClientError as e:
        mpe_utils.log_error(f"Failed to fetch Classic ELBs: {e}")

    return alb_nlb_load_balancers, classic_load_balancers

def check_for_active_elb(load_balancer_arn):
    """Checks if a Load Balancer has active target groups or listeners."""
    elb_client = boto3.client('elbv2', region_name=AWS_REGION)
    active_elb = False
    target_group_details = []
    listener_details = []

    try:
        tg_response = elb_client.describe_target_groups(LoadBalancerArn=load_balancer_arn)
        for tg in tg_response['TargetGroups']:
            target_group_details.append(f"{tg['TargetGroupName']} (ARN: {tg['TargetGroupArn']})")
        if target_group_details:
            active_elb = True
    except ClientError as e:
        mpe_utils.log_error(f"Error fetching Target Groups: {e}")

    try:
        listener_response = elb_client.describe_listeners(LoadBalancerArn=load_balancer_arn)
        for listener in listener_response['Listeners']:
            listener_details.append(f"Port {listener['Port']} - Protocol {listener['Protocol']}")
        if listener_details:
            active_elb = True
    except ClientError as e:
        mpe_utils.log_error(f"Error fetching Listeners: {e}")

    return active_elb, target_group_details, listener_details

def delete_load_balancer(load_balancer_arn_or_name, is_classic=False):
    """Deletes the specified Load Balancer."""
    if is_classic:
        elb_client = boto3.client('elb', region_name=AWS_REGION)
        try:
            elb_client.delete_load_balancer(LoadBalancerName=load_balancer_arn_or_name)
            mpe_utils.log_info(f"Deleted Classic Load Balancer: {load_balancer_arn_or_name}")
        except ClientError as e:
            mpe_utils.log_error(f"Failed to delete Classic ELB {load_balancer_arn_or_name}: {e}")
    else:
        elb_client = boto3.client('elbv2', region_name=AWS_REGION)
        active_elb, tg_details, listener_details = check_for_active_elb(load_balancer_arn_or_name)
        
        if active_elb:
            mpe_utils.log_error(f"Cannot delete Load Balancer {load_balancer_arn_or_name} due to active services.")
            if tg_details:
                mpe_utils.log_info(f"  - Active Target Groups: {tg_details}")
            if listener_details:
                mpe_utils.log_info(f"  - Active Listeners: {listener_details}")
        else:
            try:
                elb_client.delete_load_balancer(LoadBalancerArn=load_balancer_arn_or_name)
                mpe_utils.log_info(f"Deleted ELB: {load_balancer_arn_or_name}")
            except ClientError as e:
                mpe_utils.log_error(f"Failed to delete Load Balancer {load_balancer_arn_or_name}: {e}")

def main():
    """Handles input parameters, lists Load Balancers, and optionally deletes unused ones."""
    parser = argparse.ArgumentParser(description="Manage AWS Load Balancers")
    parser.add_argument('-i', '--input', required=True, help="Specify 'ALL' or a file containing Load Balancer ARNs")
    parser.add_argument('-a', '--action', choices=['DELETE'], help="Specify DELETE to remove Load Balancers")
    args = parser.parse_args()
    
    mpe_utils.setup_logging()

    input_param = args.input.lower()
    action = args.action
    deletable_lbs = []

    # If "ALL" is provided, fetch all Load Balancers
    if input_param == "all":
        mpe_utils.log_info("Fetching all Load Balancers...")
        alb_nlb_load_balancers, classic_load_balancers = describe_load_balancers()

        if not alb_nlb_load_balancers and not classic_load_balancers:
            mpe_utils.log_info("No Load Balancers found in the region.")
            return

        for lb in alb_nlb_load_balancers:
            mpe_utils.log_info(f"ALB/NLB: {lb['LoadBalancerArn']} | Type: {lb['Type']} | State: {lb['State']['Code']}")
            deletable_lbs.append(lb['LoadBalancerArn'])

        for lb in classic_load_balancers:
            mpe_utils.log_info(f"Classic ELB: {lb['LoadBalancerName']} | State: Available")
            deletable_lbs.append(lb['LoadBalancerName'])

    # If a file is provided, read Load Balancers from file
    elif os.path.isfile(input_param):
        with open(input_param, 'r') as file:
            lb_ids = [line.strip() for line in file.readlines() if line.strip()]

        if not lb_ids:
            mpe_utils.log_error("Input file is empty or contains invalid data.")
            return

        alb_nlb_load_balancers, classic_load_balancers = describe_load_balancers()
        all_lbs = {lb['LoadBalancerArn']: lb for lb in alb_nlb_load_balancers}
        all_lbs.update({lb['LoadBalancerName']: lb for lb in classic_load_balancers})

        for lb_id in lb_ids:
            if lb_id in all_lbs:
                lb = all_lbs[lb_id]
                lb_type = lb.get('Type', 'Classic')  # Classic ELB doesn't have a 'Type' key
                lb_state = lb.get('State', {}).get('Code', 'Available')  # Default to Available
                mpe_utils.log_info(f"Processing Load Balancer: {lb_id} | Type: {lb_type} | State: {lb_state}")
                deletable_lbs.append(lb_id)
            else:
                mpe_utils.log_error(f"Invalid Load Balancer: {lb_id}")

    # If action is DELETE, attempt to delete Load Balancers
    if action == "DELETE":
        for lb in deletable_lbs:
            delete_load_balancer(lb, is_classic=not lb.startswith("arn:"))
    else:
        mpe_utils.log_info("No action specified. Logging Load Balancer details only.")

if __name__ == "__main__":
    main()
