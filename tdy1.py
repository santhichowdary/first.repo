"""
delete_elb
Author: Santhi Sri
E-mail: santhisri.kankanala@fiserv.com

This script displays details of ELBs (ALL - Fetch all ELBs for given account and region or user-provided list of ELBs).
Once -a as DELETE is passed, it deletes the ELB which is not associated with any Active Listener or Target Groups.

Usage:

1. List all Load Balancers:
   python delete_elb.py -i ALL

2. Check Load Balancers from a File:
   python delete_elb.py -i elbids.txt

   - The file must contain **one Load Balancer ARN or Name (of CLB) per line**.
   - The delete_elb will display the details **only if found in AWS**.
   - If not found, it will print: Invalid Input.

3. Delete Load Balancers from a File:
   python delete_elb.py -i elbids.txt -a DELETE

   - **Deletion is only allowed if the Load Balancer has no active Listeners or Target Groups.**
   - If the Load Balancer is active, deletion is prevented, and a warning is displayed.
   - If deletion is successful, it confirms with a success message.

4. Delete Load Balancers from AWS (without a file):
   python delete_elb.py -i ALL -a DELETE

   **The delete_elb does not delete active/used Load Balancers.**
"""

import boto3
import argparse
import os
import mpe_utils  # Importing mpe_utils for logging
from botocore.exceptions import ClientError

AWS_REGION = os.getenv('AWS_REGION', None)
if not AWS_REGION:
    session = boto3.Session()
    AWS_REGION = session.region_name

def describe_load_balancers():
    """
    Fetches all ALB/NLB and Classic ELBs in the specified region.

    :return: A tuple containing two lists - one for ALB/NLB load balancers and one for Classic load balancers.
    """
    elb_client = boto3.client('elbv2', region_name=AWS_REGION)
    classic_elb_client = boto3.client('elb', region_name=AWS_REGION)
    
    try:
        alb_nlb_response = elb_client.describe_load_balancers()
        alb_nlb_load_balancers = alb_nlb_response.get('LoadBalancers', [])
    except ClientError as e:
        mpe_utils.log_error(f"Failed to fetch ALB/NLBs: {e}")
        alb_nlb_load_balancers = []
    
    try:
        classic_response = classic_elb_client.describe_load_balancers()
        classic_load_balancers = classic_response.get('LoadBalancerDescriptions', [])
    except ClientError as e:
        mpe_utils.log_error(f"Failed to fetch Classic ELBs: {e}")
        classic_load_balancers = []
    
    return alb_nlb_load_balancers, classic_load_balancers

def check_for_active_elb(load_balancer_arn):
    """
    Checks if a Load Balancer has active target groups or listeners.

    :param load_balancer_arn: The ARN of the Load Balancer to check.

    :return: A tuple containing three elements:
             - A boolean indicating if the Load Balancer has active target groups or listeners.
             - A list of active target group details.
             - A list of active listener details.
    """
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
    except ClientError:
        pass
    
    try:
        listener_response = elb_client.describe_listeners(LoadBalancerArn=load_balancer_arn)
        for listener in listener_response['Listeners']:
            listener_details.append(f"Port {listener['Port']} - Protocol {listener['Protocol']}")
        if listener_details:
            active_elb = True
    except ClientError:
        pass

    return active_elb, target_group_details, listener_details

def delete_load_balancer(load_balancer_arn_or_name, is_classic=False):
    """
    Deletes the specified Load Balancer.

    :param load_balancer_arn_or_name: The ARN (for ALB/NLB) or Name (for Classic ELB) of the Load Balancer to delete.
    :param is_classic: A boolean indicating if the Load Balancer is a Classic ELB.

    This function attempts to delete the specified Load Balancer.
    If the deletion is successful, it prints a success message.
    If an error occurs during deletion, it catches the ClientError exception and prints an error message.
    """
    if is_classic:
        elb_client = boto3.client('elb', region_name=AWS_REGION)
        try:
            elb_client.delete_load_balancer(LoadBalancerName=load_balancer_arn_or_name)
            mpe_utils.log_info(f"Deleted Classic Load Balancer: {load_balancer_arn_or_name}")
        except ClientError as e:
            mpe_utils.log_error(f"Failed to delete Classic Load Balancer {load_balancer_arn_or_name}: {e}")
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
    """
    Main function to handle input parameters and process Load Balancers.

    This function parses command-line arguments to determine the input method and action to perform.
    It lists all Load Balancers or reads Load Balancer IDs from a file, and optionally deletes unused Load Balancers.
    """
    parser = argparse.ArgumentParser(description="Manage AWS Load Balancers")
    parser.add_argument('-i', '--input', required=True, help="Specify 'ALL' or a filename containing Load Balancer ARNs")
    parser.add_argument('-a', '--action', choices=['DELETE'], help="Specify DELETE to remove Load Balancers")
    args = parser.parse_args()
    
    mpe_utils.setup_logging()
    
    param = args.input.lower()
    action = args.action
    deletable_lbs = []
    
    if param == "all":
        mpe_utils.log_info("Listing all Load Balancers...")
        alb_nlb_load_balancers, classic_load_balancers = describe_load_balancers()
        
        if not alb_nlb_load_balancers and not classic_load_balancers:
            mpe_utils.log_info("No Load Balancers found in the region.")
            return
        
        for lb in alb_nlb_load_balancers:
            lb_arn = lb['LoadBalancerArn']
            state = lb['State']['Code']
            elb_type = lb['Type']
            mpe_utils.log_info(f"Load Balancer: {lb_arn} | Type: {elb_type} | State: {state}")
            deletable_lbs.append(lb_arn)
        
        for lb in classic_load_balancers:
            mpe_utils.log_info(f"Classic Load Balancer: {lb['LoadBalancerName']}, State: Available")
            deletable_lbs.append(lb['LoadBalancerName'])
    
    elif os.path.isfile(param):
        with open(param, 'r') as file:
            lb_ids = [line.strip() for line in file.readlines()]
        
        alb_nlb_load_balancers, classic_load_balancers = describe_load_balancers()
        
        for lb_arn in lb_ids:
            found = False
            for lb in alb_nlb_load_balancers:
                if lb_arn == lb['LoadBalancerArn']:
                    active, tg_details, listener_details = check_for_active_elb(lb_arn)
                    mpe_utils.log_info(f"Load Balancer: {lb_arn}, Type: ALB/NLB")
                    if active:
                        mpe_utils.log_error("  - Cannot delete due to active services:")
                        if tg_details:
                            mpe_utils.log_info(f"    - Active Target Groups: {tg_details}")
                        if listener_details:
                            mpe_utils.log_info(f"    - Active Listeners: {listener_details}")
                    else:
                        deletable_lbs.append(lb_arn)
    
                    found = True
            if not found:
                mpe_utils.log_error(f"Invalid given Load Balancer Detail: {lb_arn}")
    
    if action == "DELETE":
        for lb_arn in deletable_lbs:
            delete_load_balancer(lb_arn, is_classic=not lb_arn.startswith("arn:"))

if __name__ == "__main__":
    main()