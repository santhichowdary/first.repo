
import argparse
import boto3, requests
import mpe_utils as mu
from botocore.exceptions import ClientError

# Initialize a session using Amazon RDS
rds_client = boto3.client('rds')
session = boto3.Session()
compute_optimizer_client = boto3.client('compute-optimizer')
account_no, AWS_REGION = mu.get_aws_account_id_and_region()
msg_key = account_no + "_" + AWS_REGION + "_" + mu.get_current_month() + "_RDS_TERMINATION_R"
msg_value = "Region:" + AWS_REGION 
def get_rds_instances_for_current_account(input = "ALL",action="READ"):
    """
    Get the list of RDS instances for the current AWS account.
    
    :param option: Option to filter instances (e.g., 'ALL', 'RUNNING', 'STOPPED').
    :param connections_count: Number of connections to check.
    :return: List of RDS instance identifiers.
    """
    try:
        response = rds_client.describe_db_instances()
        db_instances = response['DBInstances']

        if action == "COUNT":
            # Count the number of RDS instances
            instance_count = len(db_instances)
            
            return instance_count
        
        header_data = ["DBInstanceIdentifier", "DBInstanceClass", "DBInstanceEngine" "DBInstanceStatus", "Average_Connections"]
        instance_details = []
        for db_instance in db_instances:
            instance_id = db_instance['DBInstanceIdentifier']
            instance_state = db_instance['DBInstanceStatus']
            instance_class = db_instance['DBInstanceClass']
            DBInstanceArn = db_instance['DBInstanceArn']
            # Get the average connections for the RDS instance
            instance_arn = db_instance['DBInstanceArn']
            Idle =get_rds_instance_recommendations
            Avergae_Connections = mu.get_active_db_connections(rds_instance_id=instance_id, days=30)
            instance_engine = db_instance['Engine']
            if input == "ALL":
                instance_details.append([instance_id, instance_class,instance_engine, instance_state, Avergae_Connections])
        
        print(f"RDS Instances for current account: {instance_details}")
        return True
    except ClientError as e:
        mu.log_error(f"Error fetching RDS instances: {e}")
        return False

def get_idle_rds_instances_detail(option="ALL",test="Y"):
    """
    Get the list of idle RDS instances and their details.
    :param option: Option to filter instances (e.g., 'ALL', 'RUNNING', 'STOPPED').
    :return: List of idle RDS instance identifiers.
    """
    global msg_key, msg_value
    header_data = ["DBInstanceIdentifier", "DBInstanceClass", "DBInstanceEngine", "DBInstanceStatus", "AverageConnections","MaxConnections", "Finding", "SavingsOpportunityAfterDiscounts"]
    instance_details = []
    # Create a Boto3 client for Compute Optimizer
    client = boto3.client('compute-optimizer')
    # Initialize a list to hold the ARNs
    rds_instance_arns = []

    # Describe RDS instances
    response = rds_client.describe_db_instances()
    DBInstances = response['DBInstances']
    # Iterate through the instances and collect their ARNs
    for db_instance in DBInstances:
        rds_instance_arns.append(db_instance['DBInstanceArn'])
    # Get recommendations for RDS instances
    response = client.get_idle_recommendations(
        resourceArns=rds_instance_arns
    )
    total_savingsOpportunityAfterDiscounts = 0
    # Iterate through the recommendations
    for recommendation in response['idleRecommendations']:
        # Check the utilization metrics for idle instances
        resourceId = recommendation['resourceId']
        finding = recommendation['finding']
        savingsOpportunityAfterDiscounts = "$" + str(recommendation['savingsOpportunityAfterDiscounts']["estimatedMonthlySavings"]["value"])
        total_savingsOpportunityAfterDiscounts += recommendation['savingsOpportunityAfterDiscounts']["estimatedMonthlySavings"]["value"]
        maxDatabaseConnections = round(recommendation['utilizationMetrics'][1]["value"],2)

        for db_instance in DBInstances:
            instance_id = db_instance['DBInstanceIdentifier']
            if instance_id == resourceId:
                instance_state = db_instance['DBInstanceStatus']
                instance_class = db_instance['DBInstanceClass']
                AverageConnections = mu.get_active_db_connections(rds_instance_id=instance_id, days=30)
                instance_engine = db_instance['Engine']
                instance_details.append([instance_id, instance_class,instance_engine, instance_state, AverageConnections, maxDatabaseConnections, finding, savingsOpportunityAfterDiscounts])
        
    last_6_month_cost = mu.get_monthly_cost(service_name="Amazon Relational Database Service")
    last_month_cost = "Error"
    prev_month = mu.get_previous_month()
    for mandc in last_6_month_cost:
        if mandc[0] == prev_month:
            last_month_cost = mandc[1].split("$")[1]
        else:
            continue
    if len(last_6_month_cost) > 0 and last_6_month_cost[0][1] != "$0.0":
        email_body = "<b>Last 6 months RDS Cost:</b>" 

        email_body = email_body + mu.get_table_html(["Month", "Cost"], last_6_month_cost)  + "<br>"
    else:
        email_body = "<b>Last 6 months RDS Cost:</b> This information is currently not available due to some technical issue." + "<br>"
    
    recommended_resources_count = str(len(instance_details)) + "/" + str(get_rds_instances_for_current_account(input="ALL",action="COUNT"))
    email_body += "Count of Recommended RDS Instances for Termination/Total RDS Count: " + "<b>" + recommended_resources_count + "</b>\n\n"
    
    msg_value += ",OptimizationName:RDS_TERMINATION,OptimizableResourcesCount:" + recommended_resources_count + ",FinOpsSavingOpportunityIn$:" + str(total_savingsOpportunityAfterDiscounts) + ",FinOpsSavingRecommendationDate:" + mu.get_current_date() + ",LastMonthCostIn$:" + last_month_cost
    print("msg_key: " + msg_key)
    print("msg_value: " + msg_value)
    
    if len(response['idleRecommendations']) > 0:
       # mu.write_data_to_confluent_topic(key=msg_key, value=msg_value)
        table_html = mu.get_table_html(header_data, instance_details)
        exec_table_html = mu.get_table_html(['Serial Number','DBInstanceIdentifier','No Action(NA))/Termination with Backup Snapshot(TWB)/Just Stop(JS)'], [['1', ' ', ' '],['2', ' ', ' '],['3', ' ', ' ']])
        
        email_body += '<br><b>Recommended Action:</b> Idle RDS Instances should be terminated to optimize RDS costs without any backup snapshot created before Termination.'
        email_body += '<br><b>Recommended Action Execution Plan:</b> Below list of DB Instances will be terminated as per above Recommended Action  excluding received exceptions from you using automation script present at <a href="https://gitlab.onefiserv.net/mstechpe/utils/finopsautomations/-/tree/main">finopsautomations gitlab repo</a>'
        email_body += table_html
        email_body += '<p style="color: blue;"><br><b>Exceptions:</b>If you want to exclude any DB Instances from above recommended action, please copy the DBInstanceIdentifier into the table below and select only one action against it.</p>'
        email_body += exec_table_html



        if test.upper() == "Y":
            mu.log_info("Test mode is ON. Sending email to santhisri.kankanala@fiserv.com")  
            sender_list = "santhisri.kankanala@fiserv.com"
            cc_list = "@Fiserv.com" 
        else:
            acct_no,region = mu.get_aws_account_id_and_region()
            sender_list,cc_list = mu.get_account_conatct_details(acct_no)
            mu.log_info("Test mode is OFF. Sending email to " + sender_list)   
            
        mu.send_email(email_type="FinOps Recommended Action Report: RDS Termination", sender_list=sender_list, cc_list=cc_list,email_body=email_body,test=test)
    else:
        mu.log_info("No RDS Found for Termination")
 


def get_rds_instance_recommendations():
    try:
        # Call the get_rds_instance_recommendations API
        response = compute_optimizer_client.get_recommendation_summaries()
        
        print(f"Response: {response}")
        # Check if the response contains recommendations
        
       
    
    except Exception as e:
        print(f"Error fetching recommendations: {e}")



def get_instance_details(db_instance_identifier):
    """
    Fetch the details of an RDS instance, such as its size, state, Multi-AZ status,
    and read replica details.
    
    :param db_instance_identifier: The identifier of the RDS instance.
    :return: A tuple with the instance's size, state, Multi-AZ status, read replica status, and source instance identifier if a read replica.
    """
    try:
        response = rds_client.describe_db_instances(DBInstanceIdentifier=db_instance_identifier)
        db_instance = response['DBInstances'][0]
        
        instance_size = db_instance['DBInstanceClass']
        instance_state = db_instance['DBInstanceStatus']
        
        # Debug log all attributes that might indicate the status of Multi-AZ or read replica
        mu.log_debug(f"Instance attributes: {db_instance}")

        # MultiAZ will be True if the instance is part of a Multi-AZ deployment
        multi_az = db_instance.get('MultiAZ', False)
        
        # If it's a read replica, the 'ReadReplicaSourceDBInstanceIdentifier' field is populated
        read_replica = db_instance.get('ReadReplicaSourceDBInstanceIdentifier')
        source_identifier = db_instance.get('ReadReplicaSourceDBInstanceIdentifier', None)
        
        # Log additional details for clarity
        mu.log_debug(f"Multi-AZ: {multi_az}, Read Replica: {read_replica}, Source Identifier: {source_identifier}")
        
        return instance_size, instance_state, multi_az, bool(read_replica), source_identifier
    
    except ClientError as e:
        mu.log_error(f"Error fetching details for instance {db_instance_identifier}: {e}")
        return None, None, None, None, None

def resize_rds_instance(db_instance_identifier, new_instance_type):
    """
    Resize the RDS instance to a new instance type.
    
    :param db_instance_identifier: The identifier of the RDS instance to resize.
    :param new_instance_type: The new instance type (e.g., 'db.m5.large', 'db.t3.medium').
    """
    instance_size, instance_state, multi_az, is_read_replica, source_identifier = get_instance_details(db_instance_identifier)
    
    if instance_size is None:
        return

    mu.log_info(f"Instance {db_instance_identifier} - Current size: {instance_size}, State: {instance_state}, Multi-AZ: {multi_az}.")
    
    # Check if the instance is a Multi-AZ instance or a read replica
    if multi_az or is_read_replica:
        mu.log_warning(f"Cannot resize Multi-AZ or Read Replica instances directly. Resizing the source instance for read replicas.")
        if is_read_replica:
            mu.log_info(f"Attempting to resize the source instance for read replica: {source_identifier}")
            db_instance_identifier = source_identifier  # Resize the source instance for read replicas
        
        # Proceed with resizing the instance (note: it may not apply to Multi-AZ or read replica directly)
    
    # Ensure the instance is in a resizable state
    if instance_state != 'available':
        mu.log_warning(f"Instance {db_instance_identifier} is not in a resizable state (current state: {instance_state}).")
        return

    try:
        # Modify the RDS instance
        response = rds_client.modify_db_instance(
            DBInstanceIdentifier=db_instance_identifier,
            DBInstanceClass=new_instance_type,
            ApplyImmediately=True  # Apply changes immediately, may cause downtime
        )
        mu.log_info(f"Successfully initiated resize of RDS instance {db_instance_identifier} to {new_instance_type}.")
        mu.log_debug(f"Response: {response}")
    
    except ClientError as e:
        mu.log_error(f"Error resizing RDS instance {db_instance_identifier}: {e}")

def delete_rds_instance(db_instance_identifier,SkipFinalSnapshot=False):
    """
    Delete an RDS instance.
    
    :param db_instance_identifier: The identifier of the RDS instance to delete.
    """
    instance_size, instance_state, multi_az, is_read_replica, source_identifier = get_instance_details(db_instance_identifier)
    
    if instance_size is None:
        return

    mu.log_info(f"Instance {db_instance_identifier} - Current size: {instance_size}, State: {instance_state}, Multi-AZ: {multi_az}.")
    
    # Check if the instance is in a deletable state
    if instance_state != 'available':
        mu.log_warning(f"Instance {db_instance_identifier} is not in a deletable state (current state: {instance_state}).")
        return

    try:
        # Delete the RDS instance
        response = rds_client.delete_db_instance(
            DBInstanceIdentifier=db_instance_identifier,
            SkipFinalSnapshot=SkipFinalSnapshot  # Skip final snapshot before deletion
        )
        mu.log_info(f"Successfully initiated deletion of RDS instance {db_instance_identifier}.")
        mu.log_debug(f"Response: {response}")
    
    except ClientError as e:
        mu.log_error(f"Error deleting RDS instance {db_instance_identifier}: {e}")

def read_rds_instance(db_instance_identifier):
    """
    READ an RDS instance.
    
    :param db_instance_identifier: The identifier of the RDS instance to get the detail.
    """
    instance_size, instance_state, multi_az, is_read_replica, source_identifier = get_instance_details(db_instance_identifier)
    
    if instance_size is None:
        return

    mu.log_info(f"Instance {db_instance_identifier} - Current size: {instance_size}, State: {instance_state}, Multi-AZ: {multi_az}.")

def process_input_file(file_path, action):
    """
    Process the input file containing RDS instance IDs and their target instance types or deletion requests.
    
    :param file_path: Path to the input file containing instance ID and target size or deletion request.
    :param action: Action to perform ('RESIZE' or 'DELETE').
    """
    try:
        with open(file_path, 'r') as file:
            lines = file.readlines()
        
        for line in lines:
            parts = line.strip().split(',')
            if action == 'RESIZE' and len(parts) == 2:
                db_instance_id, target_size = parts
                mu.log_info(f"Processing instance {db_instance_id} with target size {target_size}...")
                resize_rds_instance(db_instance_id, target_size)
            elif action == 'DELETE' and len(parts) == 1:
                db_instance_id = parts[0]
                mu.log_info(f"Processing instance {db_instance_id} for deletion...")
                delete_rds_instance(db_instance_id)
            elif action == 'READ' and len(parts) == 1:
                db_instance_id = parts[0]
                mu.log_info(f"Getting instance {db_instance_id} Detail...")
                read_rds_instance(db_instance_id)

            else:
                mu.log_warning(f"Skipping invalid line: {line.strip()}")
    except FileNotFoundError as e:
        mu.log_error(f"Input file {file_path} not found: {e}")
    except Exception as e:
        mu.log_error(f"Error reading input file {file_path}: {e}")


def get_stopped_rds_instances():
    client = boto3.client('rds')
    response = client.describe_db_instances()
    stopped_rds = []
    for db in response['DBInstances']:
        if db['DBInstanceStatus'] == 'stopped':
            stopped_rds.append({
                'name': db['DBInstanceIdentifier'],
                'databaseEngine': db['Engine'],
                'lastSeen': None,
                'idle': 100,
                'savings': 0,
                'savingsPct': 0,
                'action': 'Terminate',
                'vendorAccountId': None,
                'accountName': None
            })
    return stopped_rds


def get_rds_recommendation_from_cloudability(input="ALL", action="READ", test="Y"):
    FD_API_PUBLIC_KEY, FD_API_SECRET_KEY = mu.get_cloudability_secrets_by_view(view_name="GBS_ALL")
    DOMAIN = "firstdata.com"
    ENV_ID = "8207c224-4499-4cbf-b63d-537d61bb2582"
    
    aws_account_number, region = mu.get_aws_account_id_and_region()
    vendor_account_ids = aws_account_number

    RIGHTSIZING_API_URL = "https://api.cloudability.com/v3/rightsizing/aws/recommendations/rds"
    params = {'keyAccess': FD_API_PUBLIC_KEY, 'keySecret': FD_API_SECRET_KEY}
    auth_response = requests.post('https://frontdoor.apptio.com/service/apikeylogin', json=params)

    if auth_response.status_code != 200:
        print(f'❌ Auth failed: {auth_response.status_code}\n{auth_response.text}')
        exit()
    
    token = auth_response.headers.get('apptio-opentoken')
    if not token:
        print("❌ Token not found!")
        exit()

    headers = {
        'apptio-opentoken': token,
        'Content-Type': 'application/json',
        'apptio-current-environment': ENV_ID
    }

    api_params = {
        'vendorAccountIds': vendor_account_ids,
        'basis': 'effective',
        'limit': 100000,
        'maxRecsPerResource': 1,
        'offset': 0,
        'product': 'rds',
        'duration': 'thirty-day',
        'viewId': 1467480,
        'Accept': 'text/csv'
    }

    rightsizing_response = requests.get(RIGHTSIZING_API_URL, headers=headers, params=api_params)

    if rightsizing_response.status_code != 200:
        print(f'❌ API failed: {rightsizing_response.status_code}\n{rightsizing_response.text}')
        exit()

    rightsizing_response_json = rightsizing_response.json()
    accounts_rds = rightsizing_response_json.get('result', [])

    terminate_data, resize_data = [], []

    cloudability_terminated_ids = set()

    for account_rds in accounts_rds:
        name = account_rds.get('name')
        lastSeen = account_rds.get('lastSeen')
        idle = account_rds.get('idle')
        databaseEngine = account_rds.get('databaseEngine')
        recommendations = account_rds.get('recommendations', [])
        storageRecommendations = account_rds.get('storageRecommendations', [])

        for recommendation in recommendations:
            rec_action = recommendation.get('action')
            if rec_action in ["Terminate", "Resize"]:
                if len(storageRecommendations) > 0:
                    savings = round(recommendation.get('savings', 0) + storageRecommendations[0].get('savings', 0), 2)
                    savingsPct = recommendation.get('savingsPct', 0) + storageRecommendations[0].get('savingsPct', 0)
                else:
                    savings = recommendation.get('savings', 0)
                    savingsPct = recommendation.get('savingsPct', 0)

                record = [name, databaseEngine, lastSeen, idle, savings, savingsPct, rec_action]
                
                if rec_action == "Terminate":
                    terminate_data.append(record)
                    cloudability_terminated_ids.add(name)
                elif rec_action == "Resize":
                    resize_data.append(record)

    # Add stopped RDS not in Cloudability terminate list
    for rds in get_stopped_rds_instances():
        if rds['name'] not in cloudability_terminated_ids:
            terminate_data.append([
                rds['name'], rds['databaseEngine'], rds['lastSeen'],
                rds['idle'], rds['savings'], rds['savingsPct'], rds['action']
            ])

    # Prepare Email
    email_body = ""
    last_6_month_cost = mu.get_monthly_cost("Amazon Relational Database Service")
    if last_6_month_cost and last_6_month_cost[0][1] != "$0.0":
        email_body += "<b>Last 6 months RDS Cost:</b>" + mu.get_table_html(["Month", "Cost"], last_6_month_cost) + "<br>"
    else:
        email_body += "<b>Last 6 months RDS Cost:</b> Not available due to technical issues.<br>"

    total_rds_count = get_rds_instances_for_current_account(input="ALL", action="COUNT")
    email_body += f"Total Recommended Termination: <b>{len(terminate_data)}</b> / {total_rds_count}<br>"
    email_body += f"Total Recommended Resize: <b>{len(resize_data)}</b> / {total_rds_count}<br><br>"

    if terminate_data:
        email_body += "<br><b>Termination Recommendations:</b>"
        email_body += mu.get_table_html(["Resource Name", "Engine", "Last Seen", "Idle(%)", "Savings($)", "Savings(%)", "Action"], terminate_data)

    if resize_data:
        email_body += "<br><b>Resize Recommendations:</b>"
        email_body += mu.get_table_html(["Resource Name", "Engine", "Last Seen", "Idle(%)", "Savings($)", "Savings(%)", "Action"], resize_data)

    email_body += '''
        <p><b>Note:</b> Please review and respond with any exclusions before the automated execution date.</p>
        <p><b>Execution Plan:</b> Approved actions will be automated from <a href="https://gitlab.onefiserv.net/mstechpe/utils/finopsautomations/-/tree/main">finopsautomations GitLab repo</a>.</p>
    '''

    if test.upper() == "Y":
        sender_list = "santhisri.kankanala@fiserv.com"
        cc_list = "@Fiserv.com"
        mu.log_info("Test mode ON: Email to test recipient.")
    else:
        acct_no, _ = mu.get_aws_account_id_and_region()
        sender_list, cc_list = mu.get_account_conatct_details(acct_no)
        mu.log_info("Test mode OFF: Email to actual recipients.")

    mu.send_email(
        email_type="FinOps Recommended Action Report: RDS Resize & Terminate",
        sender_list=sender_list,
        cc_list=cc_list,
        email_body=email_body,
        test=test
    )



ddef main():
    import argparse

    log_file = mu.setup_logging(True)

    parser = argparse.ArgumentParser(
        description="This script processes AWS RDS instance resize/delete or recommendation actions.",
        epilog="Example: python script.py -i input.txt -a RESIZE --verbose"
    )

    parser.add_argument("-i", "--input", required=True, help="Input file with RDS instance info.")
    parser.add_argument("-a", "--action", choices=["RESIZE", "DELETE"], required=False, help="Action type.")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging.")
    parser.add_argument("-t", "--test", help="Set to 'Y' for test mode email.", type=str, default='N')

    args = parser.parse_args()

    if args.action:
        mu.log_info(f"Starting RDS instance action: {args.action} from file: {args.input}")
        # process_input_file(args.input, args.action)
    else:
        mu.log_info(f"Getting RDS recommendations from Cloudability for input: {args.input}")
        get_rds_recommendation_from_cloudability(input=args.input, action="READ", test=args.test)







--------------------------------------------------------------------------------

sent chnages -

def get_rds_recommendation_from_cloudability(input="ALL", action="READ", test="Y"):
    FD_API_PUBLIC_KEY, FD_API_SECRET_KEY = mu.get_cloudability_secrets_by_view(view_name="GBS_ALL")
    ENV_ID = "8207c224-4499-4cbf-b63d-537d61bb2582"

    aws_account_number, region = mu.get_aws_account_id_and_region()
    vendor_account_ids = aws_account_number
    product = "rds"
    RIGHTSIZING_API_URL = f"https://api.cloudability.com/v3/rightsizing/aws/recommendations/{product}"

    params = {'keyAccess': FD_API_PUBLIC_KEY, 'keySecret': FD_API_SECRET_KEY}
    auth_response = requests.post('https://frontdoor.apptio.com/service/apikeylogin', json=params)
    if auth_response.status_code != 200:
        print(f'❌ Authentication failed: {auth_response.status_code}')
        exit()

    token = auth_response.headers.get('apptio-opentoken')
    if not token:
        print("❌ Authentication token not found!")
        exit()

    headers = {
        'apptio-opentoken': token,
        'Content-Type': 'application/json',
        'apptio-current-environment': ENV_ID
    }

    api_params = {
        'vendorAccountIds': vendor_account_ids,
        'basis': "effective",
        'limit': 100000,
        'maxRecsPerResource': 1,
        'offset': 0,
        'product': product,
        'duration': "thirty-day",
        'viewId': 1467480,
        'Accept': "text/csv"
    }

    rightsizing_response = requests.get(RIGHTSIZING_API_URL, headers=headers, params=api_params)
    if rightsizing_response.status_code != 200:
        print(f'❌ API call failed: {rightsizing_response.status_code}')
        exit()

    print("✅ API call successful")

    header = ["Resource Name", "Last Seen", "Engine", "Instance Type - Current", "Instance Type - Recommended", "Savings ($)", "Savings (%)"]
    data = []

    for account_rds in rightsizing_response.json().get('result', []):
        name = account_rds.get('name')
        last_seen = account_rds.get('lastSeen')
        engine = account_rds.get('databaseEngine')

        for recommendation in account_rds.get('recommendations', []):
            if recommendation.get('action') == "Resize":
                current_type = recommendation.get('currentType')
                target_type = recommendation.get('targetType')
                savings = round(recommendation.get('savings', 0.0), 2)
                savings_pct = recommendation.get('savingsPct', 0.0)
                data.append([name, last_seen, engine, current_type, target_type, f"${savings}", f"{savings_pct}%"])

    last_6_month_cost = mu.get_monthly_cost(service_name="Amazon Relational Database Service")
    email_body = "<b>Last 6 months RDS Cost:</b><br>"
    if last_6_month_cost and last_6_month_cost[0][1] != "$0.0":
        email_body += mu.get_table_html(["Month", "Cost"], last_6_month_cost) + "<br>"
    else:
        email_body += "This information is currently not available due to a technical issue.<br>"

    email_body += "Total Recommended RDS Instances for Resize: <b>{}/{}</b><br><br>".format(
        len(data), get_rds_instances_for_current_account(input="ALL", action="COUNT")
    )

    if data:
        table_html = mu.get_table_html(header, data)
        email_body += "<b>Recommended Action:</b> Below RDS Instances are eligible for resizing to optimize cost.<br>"
        email_body += "<p style='color: blue;'><b>Note:</b> Please review the below recommendations. If any instance needs to be excluded from resizing, reply to this email with justification.</p>"
        email_body += table_html

        if test.upper() == "Y":
            mu.log_info("Test mode is ON. Sending email to santhisri.kankanala@fiserv.com")
            sender_list = "santhisri.kankanala@fiserv.com"
            cc_list = "@Fiserv.com"
        else:
            acct_no, region = mu.get_aws_account_id_and_region()
            sender_list, cc_list = mu.get_account_conatct_details(acct_no)
            mu.log_info("Test mode is OFF. Sending email to " + sender_list)

        mu.send_email(
            email_type="FinOps Recommended Action Report: RDS Resize",
            sender_list=sender_list,
            cc_list=cc_list,
            email_body=email_body,
            test=test
        )
    else:
        mu.log_info("No RDS Found for Resize Recommendation")




















-----------------------------------data-----------

----incoming RDS: {
  "service": "rds-recs",
  "name": "bts-prod-merchant-db-west-global-instance-1",
  "resourceIdentifier": "arn:aws:rds:us-west-2:675440017561:db:bts-prod-merchant-db-west-global-instance-1",
  "accountName": "FDAWS BusinessTrack Prod",
  "clusterI.dentifier": "bts-prod-merchant-db-west-global-cluster-1",
  "vendorAccountId": "675440017561",
  "tagMappings": [
    {
      "tag": "tag14",
      "tagName": "ACC:FDC:DEPARTMENT",
      "vendorTagValue": "gbs - rocco"
    },
    {
      "tag": "tag15",
      "tagName": "ACC-FDC-UAID",
      "vendorTagValue": "uaid-02135"
    },
    {
      "tag": "tag16",
      "tagName": "ACC-FDC-ENV",
      "vendorTagValue": "prod"
    },
    {
      "tag": "tag17",
      "tagName": "ACC-FDC-MONTHLY-BUDGET",
      "vendorTagValue": "500"
    },
    {
      "tag": "tag19",
      "tagName": "ACC-FDC-ENV2",
      "vendorTagValue": "prod"
    },
    {
      "tag": "tag20",
      "tagName": "ACC-FDC-UAID2",
      "vendorTagValue": "uaid-02135"
    },
    {
      "tag": "tag22",
      "tagName": "DIVISION",
      "vendorTagValue": "gbs - rocco"
    }
  ],
  "provider": "NATIVE",
  "currencyCode": "USD",
  "region": "us-west-2",
  "nodeType": "db.r5.xlarge",
  "instanceFamily": "r5",
  "clusterRole": "Reader",
  "failoverOrder": "1",
  "databaseEngine": "Aurora MySQL",
  "storageType": "aurora",
  "totalStorage": 0,
  "unitPrice": 0.3,
  "totalSpend": 208.94,
  "idle": 0,
  "lastSeen": "2025-06-06T23:00:00Z",
  "daysInactive": 0,
  "cpuCapacity": 4,
  "memoryCapacity": 32,
  "iopsCapacity": 0,
  "storageThroughputCapacity": 3500,
  "hoursRunning": 696,
  "cpuMax": 24,
  "memoryMax": 74,
  "storageThroughputMax": 70,
  "iopsMax": 533,
  "databaseConnectionsMax": 80,
  "topSavings": 1.65,
  "topAction": "Rightsize",
  "recommendations": [
    {
      "action": "Rightsize",
      "preferenceOrder": 1,
      "nodeType": "db.x2g.large",
      "instanceFamily": "x2g",
      "cpuCapacity": 2,
      "memoryCapacity": 32,
      "currentGen": true,
      "sameFamily": false,
      "unitPrice": 0.3,
      "storageThroughputCapacity": 4750,
      "instanceType": "aurora",
      "cpuRatio": 0.5,
      "memoryRatio": 1,
      "cpuRisk": 0,
      "memoryRisk": 0,
      "risk": 0,
      "storageThroughputRisk": 0,
      "savingsPct": 1,
      "savings": 1.65,
      "inDefaults": false,
      "memoryFit": true
    }
  ],
  "storageRecommendations": [],
  "defaultSameFamily": false,
  "defaultCurrentGen": true,
  "defaultMemoryFit": false,
  "snoozed": false,
  "snoozeExpiresOn": ""
}



----------------------------------------------------snapshot logic


def delete_rds_instance(db_instance_identifier, SkipFinalSnapshot=False):
    """
    Delete an RDS instance after optionally taking a final snapshot.
    
    :param db_instance_identifier: The identifier of the RDS instance to delete.
    :param SkipFinalSnapshot: If True, skips snapshot creation before deletion.
    """
    instance_size, instance_state, multi_az, is_read_replica, source_identifier = get_instance_details(db_instance_identifier)

    if instance_size is None:
        return

    mu.log_info(f"Instance {db_instance_identifier} - Current size: {instance_size}, State: {instance_state}, Multi-AZ: {multi_az}.")

    if instance_state != 'available':
        mu.log_warning(f"Instance {db_instance_identifier} is not in a deletable state (current state: {instance_state}).")
        return

    try:
        # Describe instance to check for cluster membership
        response = rds_client.describe_db_instances(DBInstanceIdentifier=db_instance_identifier)
        db_instance = response['DBInstances'][0]
        db_cluster_id = db_instance.get('DBClusterIdentifier')
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')

        # Step 1: Create snapshot if not skipped
        if not SkipFinalSnapshot:
            if db_cluster_id:
                snapshot_id = f"final-cluster-snapshot-{db_cluster_id}-{timestamp}"
                mu.log_info(f"Creating cluster snapshot {snapshot_id} for cluster {db_cluster_id}...")
                rds_client.create_db_cluster_snapshot(
                    DBClusterSnapshotIdentifier=snapshot_id,
                    DBClusterIdentifier=db_cluster_id
                )
                waiter = rds_client.get_waiter('db_cluster_snapshot_available')
                waiter.wait(DBClusterSnapshotIdentifier=snapshot_id)
                mu.log_info(f"Cluster snapshot {snapshot_id} created successfully.")
            else:
                snapshot_id = f"final-snapshot-{db_instance_identifier}-{timestamp}"
                mu.log_info(f"Creating DB snapshot {snapshot_id} for instance {db_instance_identifier}...")
                rds_client.create_db_snapshot(
                    DBInstanceIdentifier=db_instance_identifier,
                    DBSnapshotIdentifier=snapshot_id
                )
                waiter = rds_client.get_waiter('db_snapshot_available')
                waiter.wait(DBSnapshotIdentifier=snapshot_id)
                mu.log_info(f"Snapshot {snapshot_id} created successfully.")

        # Step 2: Delete the instance
        response = rds_client.delete_db_instance(
            DBInstanceIdentifier=db_instance_identifier,
            SkipFinalSnapshot=True  # Already handled manually
        )
        mu.log_info(f"Successfully initiated deletion of RDS instance {db_instance_identifier}.")
        mu.log_debug(f"Response: {response}")

    except ClientError as e:
        mu.log_error(f"Error deleting RDS instance {db_instance_identifier}: {e}")



------------------------------------------------------------new snapshot individually, delete, new action items 


snapshot--


from datetime import datetime
from botocore.exceptions import ClientError

def create_final_snapshot(db_instance_identifier):
    """
    Creates a final snapshot for a given RDS instance or cluster, and tags it with a FinOps name.
    """
    try:
        response = rds_client.describe_db_instances(DBInstanceIdentifier=db_instance_identifier)
        db_instance = response['DBInstances'][0]
        db_cluster_id = db_instance.get('DBClusterIdentifier')
        date_tag = datetime.now().strftime('%Y-%m-%d')
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')

        if db_cluster_id:
            snapshot_id = f"final-cluster-snapshot-{db_cluster_id}-{timestamp}"
            tag_value = f"finops-automation-{db_cluster_id}-snapshot-{date_tag}"

            mu.log_info(f"Creating cluster snapshot {snapshot_id} for cluster {db_cluster_id}...")
            rds_client.create_db_cluster_snapshot(
                DBClusterSnapshotIdentifier=snapshot_id,
                DBClusterIdentifier=db_cluster_id,
                Tags=[
                    {
                        'Key': 'Name',
                        'Value': tag_value
                    }
                ]
            )
            waiter = rds_client.get_waiter('db_cluster_snapshot_available')
            waiter.wait(DBClusterSnapshotIdentifier=snapshot_id)

        else:
            snapshot_id = f"final-snapshot-{db_instance_identifier}-{timestamp}"
            tag_value = f"finops-automation-{db_instance_identifier}-snapshot-{date_tag}"

            mu.log_info(f"Creating DB snapshot {snapshot_id} for instance {db_instance_identifier}...")
            rds_client.create_db_snapshot(
                DBInstanceIdentifier=db_instance_identifier,
                DBSnapshotIdentifier=snapshot_id,
                Tags=[
                    {
                        'Key': 'Name',
                        'Value': tag_value
                    }
                ]
            )
            waiter = rds_client.get_waiter('db_snapshot_available')
            waiter.wait(DBSnapshotIdentifier=snapshot_id)

        mu.log_info(f"Snapshot {snapshot_id} created and tagged successfully.")
        return True

    except ClientError as e:
        mu.log_error(f"Snapshot creation failed for {db_instance_identifier}: {e}")
        return False



----------------------------------------------main action


def main():
    global log_file

    log_file = mu.setup_logging(True)

    parser = argparse.ArgumentParser(
        description="RDS automation for RESIZE, DELETE, and DELETE-WITH-COMMENTS.",
        epilog="Example: python rds1.py -i input.csv -a DELETE-WITH-COMMENTS"
    )

    parser.add_argument(
        "-i", "--input",
        required=True,
        help="Path to input file (format depends on action)"
    )

    parser.add_argument(
        "-a", "--action",
        choices=["RESIZE", "DELETE", "DELETE-WITH-COMMENTS"],
        required=True,
        help="Action to perform"
    )

    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )

    args = parser.parse_args()
    log_file = mu.setup_logging(args.verbose)

    mu.log_info(f"Running action: {args.action}, using input file: {args.input}")

    if args.action == "RESIZE":
        process_input_file(args.input, action="RESIZE")

    elif args.action == "DELETE":
        process_input_file(args.input, action="DELETE")

    elif args.action == "DELETE-WITH-COMMENTS":
        process_exception_csv(args.input)

    else:
        mu.log_error(f"Unsupported action: {args.action}")




----------------------------------------------------------------------------   input file 

import csv

def process_exception_csv(file_path):
    """
    Processes a CSV file with columns: Instance ID, Action
    - If Action is 'Terminate w/ Backup' → snapshot + delete
    - If Action is 'No Action' or 'N/A' → skip
    """
    try:
        with open(file_path, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                instance_id = row['Instance ID'].strip()
                action = row['Action'].strip().upper()

                if action in ['NO ACTION', 'N/A']:
                    mu.log_info(f"Skipping instance {instance_id} due to comment: {action}")
                    continue

                elif action.startswith("TERMINATE"):
                    mu.log_info(f"Snapshot + delete for instance {instance_id}")
                    if create_final_snapshot(instance_id):
                        delete_rds_instance(instance_id, SkipFinalSnapshot=True)
                    else:
                        mu.log_warning(f"Skipping deletion of {instance_id} due to snapshot failure.")

                else:
                    mu.log_warning(f"Unknown action '{action}' for instance {instance_id}. Skipping.")

    except Exception as e:
        mu.log_error(f"Failed to process exception CSV: {e}")

















-------------------------------------------------------------------------------sent frm ofc

rds 



 and appended for every execution in the script's path, file name has respective date/time stamp
"""




import argparse
import json
import boto3, requests
import mpe_utils as mu
import time
from datetime import datetime
from botocore.exceptions import ClientError

# Initialize a session using Amazon RDS
rds_client = boto3.client('rds')
session = boto3.Session()
compute_optimizer_client = boto3.client('compute-optimizer')
account_no, AWS_REGION = mu.get_aws_account_id_and_region()
msg_key = account_no + "_" + AWS_REGION + "_" + mu.get_current_month() + "_RDS_TERMINATION_R"
msg_value = "Region:" + AWS_REGION 
def get_rds_instances_for_current_account(input = "ALL",action="READ"):
    """
    Get the list of RDS instances for the current AWS account.
    
    :param option: Option to filter instances (e.g., 'ALL', 'RUNNING', 'STOPPED').
    :param connections_count: Number of connections to check.
    :return: List of RDS instance identifiers.
    """
    try:
        response = rds_client.describe_db_instances()
        db_instances = response['DBInstances']

        if action == "COUNT":
            # Count the number of RDS instances
            instance_count = len(db_instances)
            
            return instance_count
        
        header_data = ["DBInstanceIdentifier", "DBInstanceClass", "DBInstanceEngine" ,"DBInstanceStatus", "Average_Connections"]
        instance_details = []
        for db_instance in db_instances:
            instance_id = db_instance['DBInstanceIdentifier']
            instance_state = db_instance['DBInstanceStatus']
            instance_class = db_instance['DBInstanceClass']
            DBInstanceArn = db_instance['DBInstanceArn']
            # Get the average connections for the RDS instance
            instance_arn = db_instance['DBInstanceArn']
            Idle =get_rds_instance_recommendations
            Average_Connections = mu.get_active_db_connections(rds_instance_id=instance_id, days=30)
            instance_engine = db_instance['Engine']
            if input == "ALL":
                instance_details.append([instance_id, instance_class,instance_engine, instance_state, Avergae_Connections])
        
        print(f"RDS Instances for current account: {instance_details}")
        return True
    except ClientError as e:
        mu.log_error(f"Error fetching RDS instances: {e}")
        return False

def get_idle_rds_instances_detail(option="ALL",test="Y"):
    """
    Get the list of idle RDS instances and their details.
    :param option: Option to filter instances (e.g., 'ALL', 'RUNNING', 'STOPPED').
    :return: List of idle RDS instance identifiers.
    """
    global msg_key, msg_value
    header_data = ["DBInstanceIdentifier", "DBInstanceClass", "DBInstanceEngine", "DBInstanceStatus", "AverageConnections","MaxConnections", "Finding", "SavingsOpportunityAfterDiscounts"]
    instance_details = []
    # Create a Boto3 client for Compute Optimizer
    client = boto3.client('compute-optimizer')
    # Initialize a list to hold the ARNs
    rds_instance_arns = []

    # Describe RDS instances
    response = rds_client.describe_db_instances()
    DBInstances = response['DBInstances']
    # Iterate through the instances and collect their ARNs
    for db_instance in DBInstances:
        rds_instance_arns.append(db_instance['DBInstanceArn'])
    # Get recommendations for RDS instances
    response = client.get_idle_recommendations(
        resourceArns=rds_instance_arns
    )
    total_savingsOpportunityAfterDiscounts = 0
    # Iterate through the recommendations
    for recommendation in response['idleRecommendations']:
        # Check the utilization metrics for idle instances
        resourceId = recommendation['resourceId']
        finding = recommendation['finding']
        savingsOpportunityAfterDiscounts = "$" + str(recommendation['savingsOpportunityAfterDiscounts']["estimatedMonthlySavings"]["value"])
        total_savingsOpportunityAfterDiscounts += recommendation['savingsOpportunityAfterDiscounts']["estimatedMonthlySavings"]["value"]
        maxDatabaseConnections = round(recommendation['utilizationMetrics'][1]["value"],2)

        for db_instance in DBInstances:
            instance_id = db_instance['DBInstanceIdentifier']
            if instance_id == resourceId:
                instance_state = db_instance['DBInstanceStatus']
                instance_class = db_instance['DBInstanceClass']
                AverageConnections = mu.get_active_db_connections(rds_instance_id=instance_id, days=30)
                instance_engine = db_instance['Engine']
                instance_details.append([instance_id, instance_class,instance_engine, instance_state, AverageConnections, maxDatabaseConnections, finding, savingsOpportunityAfterDiscounts])
        
    last_6_month_cost = mu.get_monthly_cost(service_name="Amazon Relational Database Service")
    last_month_cost = "Error"
    prev_month = mu.get_previous_month()
    for mandc in last_6_month_cost:
        if mandc[0] == prev_month:
            last_month_cost = mandc[1].split("$")[1]
        else:
            continue
    if len(last_6_month_cost) > 0 and last_6_month_cost[0][1] != "$0.0":
        email_body = "<b>Last 6 months RDS Cost:</b>" 

        email_body = email_body + mu.get_table_html(["Month", "Cost"], last_6_month_cost)  + "<br>"
    else:
        email_body = "<b>Last 6 months RDS Cost:</b> This information is currently not available due to some technical issue." + "<br>"
    
    recommended_resources_count = str(len(instance_details)) + "/" + str(get_rds_instances_for_current_account(input="ALL",action="COUNT"))
    email_body += "Count of Recommended RDS Instances for Termination/Total RDS Count: " + "<b>" + recommended_resources_count + "</b>\n\n"
    
    msg_value += ",OptimizationName:RDS_TERMINATION,OptimizableResourcesCount:" + recommended_resources_count + ",FinOpsSavingOpportunityIn$:" + str(total_savingsOpportunityAfterDiscounts) + ",FinOpsSavingRecommendationDate:" + mu.get_current_date() + ",LastMonthCostIn$:" + last_month_cost
    print("msg_key: " + msg_key)
    print("msg_value: " + msg_value)
    
    if len(response['idleRecommendations']) > 0:
       # mu.write_data_to_confluent_topic(key=msg_key, value=msg_value)
        table_html = mu.get_table_html(header_data, instance_details)
        exec_table_html = mu.get_table_html(['Serial Number','DBInstanceIdentifier','No Action(NA))/Termination with Backup Snapshot(TWB)/Just Stop(JS)'], [['1', ' ', ' '],['2', ' ', ' '],['3', ' ', ' ']])
        
        email_body += '<br><b>Recommended Action:</b> Idle RDS Instances should be terminated to optimize RDS costs without any backup snapshot created before Termination.'
        email_body += '<br><b>Recommended Action Execution Plan:</b> Below list of DB Instances will be terminated as per above Recommended Action  excluding received exceptions from you using automation script present at <a href="https://gitlab.onefiserv.net/mstechpe/utils/finopsautomations/-/tree/main">finopsautomations gitlab repo</a>'
        email_body += table_html
        email_body += '<p style="color: blue;"><br><b>Exceptions:</b>If you want to exclude any DB Instances from above recommended action, please copy the DBInstanceIdentifier into the table below and select only one action against it.</p>'
        email_body += exec_table_html



        if test.upper() == "Y":
            mu.log_info("Test mode is ON. Sending email to santhisri.kankanala@fiserv.com")  
            sender_list = "santhisri.kankanala@fiserv.com"
            cc_list = "mukesh.kumar4@Fiserv.com" 
        else:
            acct_no,region = mu.get_aws_account_id_and_region()
            sender_list,cc_list = mu.get_account_conatct_details(acct_no)
            mu.log_info("Test mode is OFF. Sending email to " + sender_list)   
            
        mu.send_email(email_type="FinOps Recommended Action Report: RDS Termination", sender_list=sender_list, cc_list=cc_list,email_body=email_body,test=test)
    else:
        mu.log_info("No RDS Found for Termination")
 


def get_rds_instance_recommendations():
    try:
        # Call the get_rds_instance_recommendations API
        response = compute_optimizer_client.get_recommendation_summaries()
        
        print(f"Response: {response}")
        # Check if the response contains recommendations
        
       
    
    except Exception as e:
        print(f"Error fetching recommendations: {e}")
        

def wait_for_instance_available(db_instance_identifier, wait_interval=30, max_wait=1800):
    """
    Waits until the RDS instance is in 'available' state.
    """
    waited = 0
    while waited < max_wait:
        _, instance_state, _, _, _ = get_instance_details(db_instance_identifier)
        if instance_state == 'available':
            mu.log_info(f"Instance {db_instance_identifier} is now available.")
            return True
        mu.log_info(f"Waiting for instance {db_instance_identifier} to become available (current state: {instance_state})...")
        time.sleep(wait_interval)
        waited += wait_interval
    mu.log_error(f"Timeout: Instance {db_instance_identifier} did not become available after {max_wait} seconds.")
    return False        



def get_instance_details(db_instance_identifier):
    """
    Fetch the details of an RDS instance, such as its size, state, Multi-AZ status,
    and read replica details.
    
    :param db_instance_identifier: The identifier of the RDS instance.
    :return: A tuple with the instance's size, state, Multi-AZ status, read replica status, and source instance identifier if a read replica.
    """
    try:
        response = rds_client.describe_db_instances(DBInstanceIdentifier=db_instance_identifier)
        db_instance = response['DBInstances'][0]
        
        instance_size = db_instance['DBInstanceClass']
        instance_state = db_instance['DBInstanceStatus']
        
        # Debug log all attributes that might indicate the status of Multi-AZ or read replica
        mu.log_debug(f"Instance attributes: {db_instance}")

        # MultiAZ will be True if the instance is part of a Multi-AZ deployment
        multi_az = db_instance.get('MultiAZ', False)
        
        # If it's a read replica, the 'ReadReplicaSourceDBInstanceIdentifier' field is populated
        read_replica = db_instance.get('ReadReplicaSourceDBInstanceIdentifier')
        source_identifier = db_instance.get('ReadReplicaSourceDBInstanceIdentifier', None)
        
        # Log additional details for clarity
        mu.log_debug(f"Multi-AZ: {multi_az}, Read Replica: {read_replica}, Source Identifier: {source_identifier}")
        
        return instance_size, instance_state, multi_az, bool(read_replica), source_identifier
    
    except ClientError as e:
        mu.log_error(f"Error fetching details for instance {db_instance_identifier}: {e}")
        return None, None, None, None, None

def resize_rds_instance(db_instance_identifier, new_instance_type):
    """
    Resize the RDS instance to a new instance type.
    
    :param db_instance_identifier: The identifier of the RDS instance to resize.
    :param new_instance_type: The new instance type (e.g., 'db.m5.large', 'db.t3.medium').
    """
    instance_size, instance_state, multi_az, is_read_replica, source_identifier = get_instance_details(db_instance_identifier)
    
    if instance_size is None:
        return

    mu.log_info(f"Instance {db_instance_identifier} - Current size: {instance_size}, State: {instance_state}, Multi-AZ: {multi_az}.")
    
    # Check if the instance is a Multi-AZ instance or a read replica
    if multi_az or is_read_replica:
        mu.log_warning(f"Cannot resize Multi-AZ or Read Replica instances directly. Resizing the source instance for read replicas.")
        if is_read_replica:
            mu.log_info(f"Attempting to resize the source instance for read replica: {source_identifier}")
            db_instance_identifier = source_identifier  # Resize the source instance for read replicas
        
        # Proceed with resizing the instance (note: it may not apply to Multi-AZ or read replica directly)
    
    # Ensure the instance is in a resizable state
    if instance_state != 'available':
        mu.log_warning(f"Instance {db_instance_identifier} is not in a resizable state (current state: {instance_state}).")
        return

    try:
        # Modify the RDS instance
        response = rds_client.modify_db_instance(
            DBInstanceIdentifier=db_instance_identifier,
            DBInstanceClass=new_instance_type,
            ApplyImmediately=True  # Apply changes immediately, may cause downtime
        )
        mu.log_info(f"Successfully initiated resize of RDS instance {db_instance_identifier} to {new_instance_type}.")
        mu.log_debug(f"Response: {response}")
    
    except ClientError as e:
        mu.log_error(f"Error resizing RDS instance {db_instance_identifier}: {e}")
        
def create_final_snapshot(db_instance_identifier):
    """
    Creates a final snapshot for a given RDS instance or cluster, and tags it with a FinOps name.
    """
    try:
        response = rds_client.describe_db_instances(DBInstanceIdentifier=db_instance_identifier)
        db_instance = response['DBInstances'][0]
        db_cluster_id = db_instance.get('DBClusterIdentifier')
        date_tag = datetime.now().strftime('%Y-%m-%d')
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')

        if db_cluster_id:
            snapshot_id = f"finops-automation-{db_cluster_id}-snapshot-{date_tag}"
            tag_value = f"finops-automation-{db_cluster_id}-snapshot-{date_tag}"

            mu.log_info(f"Creating cluster snapshot {snapshot_id} for cluster {db_cluster_id}...")
            mu.log_info(f"Tagging snapshot with Name: {tag_value}")
            rds_client.create_db_cluster_snapshot(
                DBClusterSnapshotIdentifier=snapshot_id,
                DBClusterIdentifier=db_cluster_id,
                Tags=[
                    {
                        'Key': 'Name',
                        'Value': tag_value
                    }
                ]
            )
            waiter = rds_client.get_waiter('db_cluster_snapshot_available')
            waiter.wait(DBClusterSnapshotIdentifier=snapshot_id)

        else:
            snapshot_id = f"finops-automation-{db_instance_identifier}-snapshot-{date_tag}"
            tag_value = f"finops-automation-{db_instance_identifier}-snapshot-{date_tag}"

            mu.log_info(f"Creating DB snapshot {snapshot_id} for instance {db_instance_identifier}...")
            mu.log_info(f"Tagging snapshot with Name: {tag_value}")
            rds_client.create_db_snapshot(
                DBInstanceIdentifier=db_instance_identifier,
                DBSnapshotIdentifier=snapshot_id,
                Tags=[
                    {
                        'Key': 'Name',
                        'Value': tag_value
                    }
                ]
            )
            waiter = rds_client.get_waiter('db_snapshot_available')
            waiter.wait(DBSnapshotIdentifier=snapshot_id)

        mu.log_info(f"Snapshot {snapshot_id} created and tagged successfully.")
        return True

    except ClientError as e:
        mu.log_error(f"Snapshot creation failed for {db_instance_identifier}: {e}")
        return False
            

def delete_rds_instance(db_instance_identifier,SkipFinalSnapshot=False):
    """
    Delete an RDS instance.
    
    :param db_instance_identifier: The identifier of the RDS instance to delete.
    """
    instance_size, instance_state, multi_az, is_read_replica, source_identifier = get_instance_details(db_instance_identifier)
    
    if instance_size is None:
        return

    mu.log_info(f"Instance {db_instance_identifier} - Current size: {instance_size}, State: {instance_state}, Multi-AZ: {multi_az}.")
    
    # Check if the instance is in a deletable state
    if instance_state != 'available':
        mu.log_warning(f"Instance {db_instance_identifier} is not in a deletable state (current state: {instance_state}).")
        return

    try:
        # Delete the RDS instance
        response = rds_client.delete_db_instance(
            DBInstanceIdentifier=db_instance_identifier,
            SkipFinalSnapshot=SkipFinalSnapshot  # Skip final snapshot before deletion
        )
        mu.log_info(f"Successfully initiated deletion of RDS instance {db_instance_identifier}.")
        mu.log_debug(f"Response: {response}")
    
    except ClientError as e:
        mu.log_error(f"Error deleting RDS instance {db_instance_identifier}: {e}")
        
        
def read_rds_instance(db_instance_identifier):
    """
    READ an RDS instance.
    
    :param db_instance_identifier: The identifier of the RDS instance to get the detail.
    """
    instance_size, instance_state, multi_az, is_read_replica, source_identifier = get_instance_details(db_instance_identifier)
    
    if instance_size is None:
        return

    mu.log_info(f"Instance {db_instance_identifier} - Current size: {instance_size}, State: {instance_state}, Multi-AZ: {multi_az}.")

def process_rds_actions(input_file, action):
    """
    Processes RDS actions: RESIZE, DELETE, DELETE-WITH-COMMENTS.
    - For RESIZE: expects input_file lines as 'instance_id,target_size'
    - For DELETE: expects input_file lines as 'instance_id'
    - For DELETE-WITH-COMMENTS: expects input_file lines as 'instance_id,action'
    """
    try:
        with open(input_file, 'r') as file:
            lines = file.readlines()

        for line in lines:
            parts = line.strip().split(',')
            db_instance_id = parts[0].strip()

            if action == 'RESIZE' and len(parts) == 2:
                target_size = parts[1].strip()
                mu.log_info(f"Processing instance {db_instance_id} with target size {target_size}...")
                resize_rds_instance(db_instance_id, target_size)

            elif action == 'DELETE' and len(parts) == 1:
                mu.log_info(f"Processing instance {db_instance_id} for deletion...")
                delete_rds_instance(db_instance_id)

            elif action == 'DELETE-WITH-COMMENTS' and len(parts) == 2:
                ex_action = parts[1].strip().upper()
                if ex_action in ['NO ACTION', 'N/A']:
                    mu.log_info(f"Skipping instance {db_instance_id} due to comment: {ex_action}")
                    continue
                elif ex_action in ["TWB", "TERMINATE W/ BACKUP"]:
                    mu.log_info(f"Snapshot + delete for instance {db_instance_id}")
                    if create_final_snapshot(db_instance_id):
                        wait_for_instance_available(db_instance_id)
                        delete_rds_instance(db_instance_id, SkipFinalSnapshot=True)
                    else:
                        mu.log_warning(f"Skipping deletion of {db_instance_id} due to snapshot failure.")
                else:
                    mu.log_info(f"Deleting instance {db_instance_id} (no snapshot)...")
                    delete_rds_instance(db_instance_id, SkipFinalSnapshot=True)

            else:
                mu.log_warning(f"Skipping invalid line: {line.strip()}")

    except FileNotFoundError as e:
        mu.log_error(f"Input file {input_file} not found: {e}")
    except Exception as e:
        mu.log_error(f"Error processing input file {input_file}: {e}")        
        


def get_stopped_rds_instances():
    client = boto3.client('rds')
    response = client.describe_db_instances()
    stopped_rds = []
    for db in response['DBInstances']:
        if db['DBInstanceStatus'] == 'stopped':
            stopped_rds.append({
                'name': db['DBInstanceIdentifier'],
                'databaseEngine': db['Engine'],
                'lastSeen': None,
                'idle': 100,
                'savings': 0,
                'savingsPct': 0,
                'action': 'Terminate',
                'vendorAccountId': None,
                'accountName': None
            })
    return stopped_rds


def get_rds_recommendation_from_cloudability(input="ALL", action="READ", test="Y", override_account_id="675440017561"):
    FD_API_PUBLIC_KEY, FD_API_SECRET_KEY = mu.get_cloudability_secrets_by_view(view_name="GBS_ALL")
    ENV_ID = "8207c224-4499-4cbf-b63d-537d61bb2582"

    if override_account_id:
        aws_account_number = override_account_id
        region= "us-west-2"
        mu.log_info(f"using override account ID: {aws_account_number}")
    else:
         aws_account_number, region = mu.get_aws_account_id_and_region()  

    
    vendor_account_ids = aws_account_number
    product = "rds"
    RIGHTSIZING_API_URL = f"https://api.cloudability.com/v3/rightsizing/aws/recommendations/{product}"

    params = {'keyAccess': FD_API_PUBLIC_KEY, 'keySecret': FD_API_SECRET_KEY}
    auth_response = requests.post('https://frontdoor.apptio.com/service/apikeylogin', json=params)
    if auth_response.status_code != 200:
        print(f'❌ Authentication failed: {auth_response.status_code}')
        exit()

    token = auth_response.headers.get('apptio-opentoken')
    if not token:
        print("❌ Authentication token not found!")
        exit()

    headers = {
        'apptio-opentoken': token,
        'Content-Type': 'application/json',
        'apptio-current-environment': ENV_ID
    }

    api_params = {
        'vendorAccountIds': vendor_account_ids,
        'basis': "effective",
        'limit': 100000,
        'maxRecsPerResource': 1,
        'offset': 0,
        'product': product,
        'duration': "thirty-day",
        'viewId': 1467480,
        'Accept': "text/csv"
    }

    rightsizing_response = requests.get(RIGHTSIZING_API_URL, headers=headers, params=api_params)
    if rightsizing_response.status_code != 200:
        print(f'❌ API call failed: {rightsizing_response.status_code}')
        exit()

    print("✅ API call successful")

    header = ["DBInstanceIdentifier", "Engine", "Instance Type - Current", "Instance Type - Recommended", "Savings ($)", "Savings (%)"]
    data = []

    for account_rds in rightsizing_response.json().get('result', []):
        print ("----incoming RDS:", json.dumps(account_rds, indent =2))

        DBInstanceIdentifier = account_rds.get('name')
        engine = account_rds.get('databaseEngine')


        for recommendation in account_rds.get('recommendations', []):
            if recommendation.get('action') == "Rightsize":
                current_type = account_rds.get('nodeType')
                target_type = recommendation.get('nodeType')
                savings = round(recommendation.get('savings', 0.0), 2)
                savings_pct = recommendation.get('savingsPct', 0.0)
                data.append([DBInstanceIdentifier, engine, current_type, target_type, f"${savings}", f"{savings_pct}%"])


    last_6_month_cost = mu.get_monthly_cost(service_name="Amazon Relational Database Service")
    email_body = "<b>Last 6 months RDS Cost:</b><br>"
    if last_6_month_cost and last_6_month_cost[0][1] != "$0.0":
        email_body += mu.get_table_html(["Month", "Cost"], last_6_month_cost) + "<br>"
    else:
        email_body += "This information is currently not available due to a technical issue.<br>"

    email_body += "Total Recommended RDS Instances for Rightsize: <b>{}/{}</b><br><br>".format(
        len(data), get_rds_instances_for_current_account(input="ALL", action="COUNT")
    )

    if data:
        table_html = mu.get_table_html(header, data)
        email_body += "<b>Recommended Action:</b> Below RDS Instances are eligible for rightsizing to optimize cost.<br>"
        email_body += '<br><b>Recommended Action Execution Plan:</b> Below list of DB Instances will be Rightsized as per above Recommended Action  excluding received exceptions from you using automation script present at <a href="https://gitlab.onefiserv.net/mstechpe/utils/finopsautomations/-/tree/main">finopsautomations gitlab repo</a>'
        email_body += table_html

        exec_table_html = mu.get_table_html(
            [' serial Number', 'DBInstanceIdentifier', ' Action( No Action (NA) / Rightsize with caution)' ],
            [['1', ' ', ' '],['2', ' ', ' '],['3', ' ', ' ']]
            )
          
        email_body += '<p style="color: blue;"><br><b>Exceptions:</b>If you want to exclude any DB Instances from above recommended action, please copy the DBInstanceIdentifier into the table below and select only one action against it.</p>'
        email_body += exec_table_html



        if test.upper() == "Y":
            mu.log_info("Test mode is ON. Sending email to santhisri.kankanala@fiserv.com")
            sender_list = "santhisri.kankanala@fiserv.com"
            cc_list = "mukesh.kumar4@Fiserv.com"
        else:
            acct_no, region = override_account_id if override_account_id else aws_account_number
            sender_list, cc_list = mu.get_account_conatct_details(acct_no)
            mu.log_info("Test mode is OFF. Sending email to " + sender_list)

        mu.send_email(
            email_type="FinOps Recommended Action Report: RDS Rightsize",
            sender_list=sender_list,
            cc_list=cc_list,
            email_body=email_body,
            test=test
        )
    else:
        mu.log_info("No RDS Found for Rightsize Recommendation")


def main():
    log_file = mu.setup_logging(True)

    parser = argparse.ArgumentParser(
        description="RDS automation for RESIZE, DELETE, DELETE-WITH-COMMENTS, and Cloudability recommendations.",
        epilog="Example: python rds3.py -i input.txt -a DELETE-WITH-COMMENTS"
    )

    parser.add_argument(
        "-i", "--input",
        required=True,
        help="Path to input file (format depends on action)"
    )

    parser.add_argument(
        "-a", "--action",
        choices=["RESIZE", "DELETE", "DELETE-WITH-COMMENTS"],
        required=False,
        help="Action to perform"
    )

    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )

    parser.add_argument(
        "-t", "--test",
        help="Set to 'Y' for test mode email.",
        type=str,
        default='N'
    )

    args = parser.parse_args()
    log_file = mu.setup_logging(args.verbose)

    mu.log_info(f"Running action: {args.action}, using input file: {args.input}")

    if args.action in ["RESIZE", "DELETE", "DELETE-WITH-COMMENTS"]:
        process_rds_actions(args.input, action=args.action)
    else:
        mu.log_info(f"Getting RDS recommendations from Cloudability for input: {args.input}")
        get_rds_recommendation_from_cloudability(input=args.input, action="READ", test=args.test)

if __name__ == '__main__':
    main()
      
      
        
        
   ---------------------------------------------------------------------mpeutils


   
        """script_owner/author:Sriram S
E-mail:sriram.sundaravaradhan@fiserv.com
Desc: importable header file - includes logging ability with custom wrappers & account detail logging

(i)calling file needs to call setup_logging() method to log


    mpe_utils.setup_logging()

"""
import logging,sys,json,csv
#import pandas as pd
import os,requests
import pytz
import boto3
from datetime import datetime, timedelta
import inspect,base64
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
# from confluent_kafka import Producer
# from confluent_kafka import Consumer,KafkaError
# import socket,ntplib, configparser
from boto3.dynamodb.conditions import Key, Attr

def add_multiple_items_to_dynamodb(table_name="stage-finops-cost-optimization-report-ddb", region_name='us-east-2',items_to_add=[]):
    """
    Adds multiple items to a DynamoDB table using batch_writer.

    Args:
        table_name (str): The name of the DynamoDB table.
        items_to_add (list): A list of dictionaries, where each dictionary
                             represents an item to be added.
        region_name (str): The AWS region where the DynamoDB table is located.
    """
    try:
        dynamodb = boto3.resource('dynamodb', region_name=region_name)
        table = dynamodb.Table(table_name)

        with table.batch_writer() as batch:
            for item in items_to_add:
                batch.put_item(Item=item)
        print(f"Successfully added {len(items_to_add)} items to table '{table_name}'.")

    except Exception as e:
        print(f"Error adding items to DynamoDB: {e}")

def get_all_dynamodb_records(table_name="dev-finops-cost-optimization-report-ddb", region_name='us-east-1'):
    """
    Reads all records from a specified DynamoDB table.

    Args:
        table_name (str): The name of the DynamoDB table.
        region_name (str): The AWS region where the table resides.

    Returns:
        list: A list of dictionaries, where each dictionary represents a record.
              Returns an empty list if the table is empty or an error occurs.
    """
    dynamodb = boto3.resource('dynamodb', region_name=region_name)
    table = dynamodb.Table(table_name)

    all_items = []
    response = None

    while True:
        if response:
            response = table.scan(ExclusiveStartKey=response.get('LastEvaluatedKey'))
        else:
            response = table.scan()

        items = response.get('Items', [])
        all_items.extend(items)

        if 'LastEvaluatedKey' not in response:
            break
    
    return all_items

def get_services_count_for_current_account(service="AmazonCloudWatch"):
    """Retrieves the count of a specific AWS service for the current account.   
    Args:
    service (str): The name of the AWS service for which to retrieve the count. Default is "AmazonCloudWatch".
    Returns:
    int: The count of the specified AWS service for the current account.
    """
    try:
        if service == "AmazonCloudWatch":
            total_log_groups_count = len(get_log_groups_with_retention(0))
            return total_log_groups_count

        elif service == "Amazon Relational Database Service":
            rds_client = boto3.client('rds')
            response = rds_client.describe_db_instances()
            db_instances = response['DBInstances']

            instance_count = len(db_instances)
                
            return instance_count
        elif "SnapshotUsage" in service:
            ec2_client = boto3.client('ec2')
            response = ec2_client.describe_snapshots(OwnerIds=['self'])
            snapshots = response['Snapshots']
            snapshot_count = len(snapshots)
            
            return snapshot_count 
        elif service == "Amazon Elastic Block Store":
            ec2_client = boto3.client('ec2')
            response = ec2_client.describe_volumes()
            volumes = response['Volumes']
            volume_count = len(volumes)
            
            return volume_count

    except Exception as e:
        print(f"Error retrieving RDS instances: {e}")
        return 0

def get_ntp_time():
    try:
        client = ntplib.NTPClient()
        response = client.request('pool.ntp.org')
        return response.tx_time
    except Exception as e:
        print(f"Failed to get NTP time: {e}")
        return None

def check_clock_skew():
    ntp_time = get_ntp_time()
    if ntp_time is not None:
        local_time = datetime.now().timestamp()
        skew = local_time - ntp_time
        print(f"NTP time: {ntp_time}")
        print(f"Local time: {local_time}")
        print(f"Clock skew (in seconds): {skew}")
    else:
        print("Could not fetch NTP time. Ensure you have network access.")


def post_data_to_url(url="https://stage-write-data-to-ddb.merch-tech-pe-dev-nonprod.aws.fisv.cloud/", data=None):
    """
    Posts data to a specified URL using a POST request. 
    Args:
    url (str): The URL to which data will be posted.    
    data (dict): The data to be posted to the URL.
    Returns:
    String: The response from the POST request.
    """

    # Define the headers
    headers = {
        'Content-Type': 'application/json'
    }
    print(data)

    # Make the POST request
    response = requests.post(url, headers=headers, data=json.dumps(data))

    # Check the status code and response
    if response.status_code == 200:
        print('Request was successful.')
        print('Response:', response)
    else:
        print(f'Failed to make the request. Status code: {response.status_code}')
        print('Response:', response)

def update_data_to_url(url="https://stage-update-data-to-ddb.merch-tech-pe-dev-nonprod.aws.fisv.cloud/", data=None):
    """
    Posts data to a specified URL using a POST request. 
    Args:
    url (str): The URL to which data will be posted.    
    data (dict): The data to be posted to the URL.
    Returns:
    String: The response from the POST request.
    """

    # Define the headers
    headers = {
        'Content-Type': 'application/json'
    }
    print(data)

    # Make the POST request
    response = requests.post(url, headers=headers, data=json.dumps(data))

    # Check the status code and response
    if response.status_code == 200:
        print('Request was successful.')
        print('Response:', response)
    else:
        print(f'Failed to make the request. Status code: {response.status_code}')
        print('Response:', response)

def update_dynamodb_row(table_name="dev-finops-cost-optimization-report-ddb", AccountNumber='307946647371',RegRecTypeDt='us-east-1LOG_GROUP_UPDATE_R2025-06',update_attributes=None):
    """
    Updates attributes of an existing item in a DynamoDB table based on partition and sort key.

    Args:
        table_name (str): The name of the DynamoDB table.
        partition_key_value: The value of the item's partition key.
        sort_key_value: The value of the item's sort key.
        update_attributes (dict): A dictionary of attributes to update and their new values.

    Returns:
        dict: The response from the DynamoDB update_item operation.
    """
    app_env = os.environ.get('APP_ENV', 'dev')
    if app_env == 'stage':
        table_name = "stage-finops-cost-optimization-report-ddb"

    dynamodb = boto3.resource('dynamodb') # You might need to specify region_name based on your setup.
    table = dynamodb.Table(table_name)

    # Build the UpdateExpression and ExpressionAttributeValues
    update_expression_parts = []
    expression_attribute_values = {}
    expression_attribute_names = {} # Needed for reserved keywords or symbols

    for key, value in update_attributes.items():
        # Handle reserved keywords or special characters in attribute names
        # This is a basic example; you might need more complex logic for complex cases
        safe_key = f'#{key}'
        update_expression_parts.append(f'{safe_key} = :{key}')
        expression_attribute_values[f':{key}'] = value
        expression_attribute_names[safe_key] = key

    update_expression = 'SET ' + ', '.join(update_expression_parts)

    try:
        response = table.update_item(
            Key={
                'AccountNumber': AccountNumber,  # Replace 'PartitionKeyName' with your actual partition key name
                'RegRecTypeDt': RegRecTypeDt              # Replace 'SortKeyName' with your actual sort key name
            },
            UpdateExpression=update_expression,
            ExpressionAttributeValues=expression_attribute_values,
            ExpressionAttributeNames=expression_attribute_names,
            ReturnValues='UPDATED_NEW'  # Return the updated attributes
        )
        return response
    except Exception as e:
        print(f"Error updating item: {e}")
        return None



def update_dynamodb_table(table_name="dev-finops-cost-optimization-report-ddb", item=None):
    """
    Updates an item in a DynamoDB table.
    
    Args:
    table_name (str): The name of the DynamoDB table.
    item (dict): The item to be updated in the table.
    
    Returns:
    dict: The response from the DynamoDB update operation.
    """
    app_env = os.environ.get('APP_ENV', 'dev')
    if app_env == 'stage':
        table_name = "stage-finops-cost-optimization-report-ddb"

    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table(table_name)

    try:
        response = table.put_item(Item=item)
        return response
    except Exception as e:
        print(f"Error updating DynamoDB table {table_name}: {e}")
        return None

def read_data_from_dynamodb_table(table_name="dev-finops-cost-optimization-report-ddb", AccountNumber=None, RegRecTypeDt=None):
    """
    Reads an item from a DynamoDB table.
    
    Args:
    table_name (str): The name of the DynamoDB table.
    key (dict): The key of the item to be read from the table.
    
    Returns:
    dict: The item retrieved from the DynamoDB table.
    """
    app_env = os.environ.get('APP_ENV', 'dev')
    if app_env == 'stage':
        table_name = "stage-finops-cost-optimization-report-ddb"

    dynamodb = boto3.resource('dynamodb')
    if not AccountNumber or not RegRecTypeDt:
        print("AccountNumber and RegRecTypeDt are required to read data from DynamoDB.")
        return None
    
    # Query DynamoDB table with the specified Account number and RegRecTypeDt
    try:
        table = dynamodb.Table(table_name)
        # Query the table
        response = table.query(
            KeyConditionExpression=Key('AccountNumber').eq(AccountNumber) & Key('RegRecTypeDt').eq(RegRecTypeDt)
        )

        # Get the items from the response
        ddb_response = response.get('Items', [])
        print(f"Query response: {response}")
        return ddb_response
    
    except Exception as e:
        print(f"Error reading from DynamoDB table {table_name}: {e}")
        return None

def get_data_from_url(url="https://stage-get-data-from-ddb.merch-tech-pe-dev-nonprod.aws.fisv.cloud", AccountNumber=None, RegRecTypeDt=None):
    """
    Retrieves data from a specified URL using a GET request.    
    Args:
    url (str): The URL from which to retrieve data.
    AccountNumber (str): The AWS account number for which to retrieve data.
    RegRecTypeDt (str): The region and record type date for which to retrieve data.
    Returns:
    dict: The item retrieved from the DynamoDB table.
    """
    try:
        params = {'AccountNumber': AccountNumber, 'RegRecTypeDt': RegRecTypeDt}
        response = requests.get(url, params=params)
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error during API request: {e}")
        return None

def get_savings_opportunities_for_aws_account():
    """
    Retrieves the savings opportunities for an AWS account using the Cost Explorer API.
    
    Returns:
    list: A list of dictionaries containing savings opportunity details.
    """
    # Create a Compute Optimizer client
    client = boto3.client('compute-optimizer')
    try:
        # Get recommendation summaries
        recommendations = client.get_recommendation_summaries(
            accountIds=[
                '544643336122', # Replace with your AWS account ID
            ]
        )
        # Print the recommendations
        print('Estimated Savings Opportunities:')
        for summary in recommendations['recommendationSummaries']:
            
            if summary['recommendationResourceType'] == 'RdsDBInstance':
                print(f"Resource Type: {summary['recommendationResourceType']}")
                print(f"Estimated Monthly Savings Amount: ${summary['idleSavingsOpportunity']['estimatedMonthlySavings']['value']}")
            elif summary['recommendationResourceType'] == 'EcsService':
                print(f"Resource Type: {summary['recommendationResourceType']}")
                print(f"Estimated Monthly Savings Amount: ${summary['savingsOpportunity']['estimatedMonthlySavings']['value']}")
            elif summary['recommendationResourceType'] == 'RdsDBInstanceStorage':
                print(f"Resource Type: {summary['recommendationResourceType']}")
                for item in summary['summaries']:
                    if item['name'] == 'Overprovisioned':
                        print(f"Estimated Monthly Savings Amount: ${item['value']}")
            elif summary['recommendationResourceType'] == 'EbsVolume':
                print(f"Resource Type: {summary['recommendationResourceType']}")
                print(f"Estimated Monthly Savings Amount: ${summary['idleSavingsOpportunity']['estimatedMonthlySavings']['value']}")
            elif summary['recommendationResourceType'] == 'Ec2Instance':
                print(f"Resource Type: {summary['recommendationResourceType']}")
                print(f"Estimated Monthly Savings Amount: ${summary['aggregatedSavingsOpportunity']['estimatedMonthlySavings']['value']}")
   
    except Exception as e:
        print(f"Error retrieving savings opportunities: {e}")
        return []   

# def write_data_to_kafka_topic(topic_name="mstech-pe-apm0011436-cert-costoptimization", key="test_key", value="test_value_from_mpe_utils"):
#     '''

#     '''
#     # Load properties from file
#     config = configparser.ConfigParser()
#     config.read('./config/producer.properties')

#     # Convert config to dictionary
#     kafka_config = dict(config['DEFAULT'])

#     # Test Producer

#     producer = Producer(kafka_config)

#     def delivery_report(err, msg):
#         if err is not None:
#             print(f"Message delivery failed: {err}")
#         else:
#             print(f"Message delivered to {msg.topic()} [{msg.partition()}]")

#     producer.produce(topic_name, value=value, callback=delivery_report)
#     producer.flush()


# def write_data_to_confluent_topic(topic_name="mstech-pe-apm0011436-cert-costoptimization", key="test_key", value="test_value_from_mpe_utils"):
#     """Writes data to a specified Confluent topic.
#     Args:
#     topic_name (str): The name of the Confluent topic to which data will be written.
#     data (str): The data to be written to the topic.
#     Returns:"""
#     try:
#         # Initialize the Confluent producer
#         '''
        
#         conf = {'bootstrap.servers': 'lkc-1nr9kj.domxp88kzpd.us-east-1.aws.confluent.cloud:9092',
#                 'security.protocol': 'SASL_SSL',
#                 'sasl.mechanism': 'PLAIN',
#                 'sasl.username': '3PAXLHVNV3Q2TSX6',
#                 'sasl.password': 'r44Rc3AySN3vBrS8J+9W0VYrGnn26wm55ypXScmHSkZ6TCnW/g9QWmggH7COHeHg',
#                 'client.dns.lookup':'use_all_dns_ips',
#                 'session.timeout.ms':45000,
#                 'client.id': 'sales-1',
#                 'linger.ms':200}
#         '''
#         # Load properties from file
#         config = configparser.ConfigParser()
#         config.read('config/producer.properties')

#         # Convert config to dictionary
#         kafka_config = dict(config['DEFAULT'])
#         producer = Producer(kafka_config)

#         # Produce the data to the specified topic
#         def delivery_report(err, msg):
#             """ Called once for each message produced to indicate delivery result.
#                 Triggered by poll() or flush(). """
#             if err is not None:
#                 print('Message delivery failed: {}'.format(err))
#             else:
#                 print('Message delivered to {} [{}]'.format(msg.topic(), msg.partition()))
#         producer.produce(topic_name, key=key, value=value, callback=delivery_report)
#         print('Debug2')
#         # Wait up to 1 second for events. Callbacks will be invoked during
#         producer.poll(1)
#         # this method call if the message is acknowledged.
#         print('Debug3')
#         producer.flush()  # Ensure all messages are sent
#         print('Debug4')
#         print(f"Data written to topic '{topic_name}' successfully.")
#         return True
#     except BufferError:
#         print("Local producer queue is full ({} messages awaiting delivery): try again\n".format(len(producer)))

#     # Wait for any outstanding messages to be delivered and delivery report callbacks to be triggered.
#     producer.flush() 

# def read_data_from_confluent_topic(topic_name="mstech-pe-apm0011436-cert-costoptimization",key="test_key"):
#     """Reads data from a specified Confluent topic.     
#     Args:
#     topic_name (str): The name of the Confluent topic from which data will be read.
#     Returns:
#     list: A list of messages read from the topic.
#     """
#     # Get the current time and calculate the time 24 hours ago
#     now = datetime.now()
#     twenty_four_hours_ago = now - timedelta(hours=24)

   
#     try:
#         # Initialize the Confluent consumer
#         conf = {'bootstrap.servers': 'lkc-1nr9kj.domxp88kzpd.us-east-1.aws.confluent.cloud:9092',
#                 'security.protocol': 'SASL_SSL',
#                 'sasl.mechanism': 'PLAIN',
#                 'sasl.username': 'RGZMS37EO5VLE2FD',
#                 'sasl.password': 'V3bVi08/NUOA+UrgW1OnlpbHj6Esopn45oh5sG7QdnluWm77k0cU8lErPyqxDZ9Z',
#                 'group.id': 'mstech-pe-apm0011436-cert-costoptimization_consumer_group',
#                 'auto.offset.reset': 'earliest'}
        
#         consumer = Consumer(conf)
#         consumer.subscribe([topic_name])

#         messages = []
#         while True:
#             msg = consumer.poll(timeout=2.0)  # Wait for a message for up to 2 second
#             print(f"Polling topic '{topic_name}' for messages...")  # Debugging line to indicate polling
#             if msg is None:
#                 continue  
            
#             if msg.error():
#                 if msg.error().code() == KafkaError._PARTITION_EOF:
#                     print('End of partition reached {0}/{1}'
#                           .format(msg.topic(), msg.partition()))
#                     continue
#                 elif msg.error():
#                     print('Error occurred: {0}'.format(msg.error().str()))
#                     break
                
#             else:
#                 # Check if the message key matches the given key
#                 #if msg.key() == key.encode('utf-8'):
#                     #return msg.value().decode('utf-8')
#                 # Convert the message timestamp to a datetime object
#                 msg_timestamp = datetime.fromtimestamp(msg.timestamp()[1] / 1000.0)

#                 # Check if the message timestamp is within the last 24 hours
#                 if msg_timestamp >= twenty_four_hours_ago:
#                     print(f"Received message: {msg.value().decode('utf-8')}")
             

#         print(f"Data read from topic '{topic_name}' successfully.")
#         return True
#     except Exception as e:
#         print(f"Error reading data from topic: {e}")
#         return [] 
#     except KeyboardInterrupt:
#         print("Consumer interrupted by user.")  
#         pass
#     finally:
#         # Close the consumer
#         consumer.close()
#     return None


def create_csv_file(file_name, data):
    """
    Creates a CSV file with the specified name and data.
    
    Args:
    file_name (str): The name of the CSV file to be created.
    data (list): A list of lists containing the data to be written to the CSV file.
    
    Returns:
    None
    """
    try:
        # Check if the file already exists
        if os.path.exists(file_name):
            print(f"File '{file_name}' already exists. Overwriting...")
        
        # Create a DataFrame and write to CSV
        # Writing to CSV
        with open(file_name, mode='w', newline='') as file:
            writer = csv.writer(file)
    
            # Write the data
            writer.writerows(data)
            print(f"CSV file '{file_name}' created successfully.")
            return True


        
    except Exception as e:
        print(f"Error creating CSV file: {e}")
        return {"Error": str(e)}


# def create_csv_file_using_pd(file_name, data):
#     """
#     Creates a CSV file with the specified name and data.
    
#     Args:
#     file_name (str): The name of the CSV file to be created.
#     data (list): A list of lists containing the data to be written to the CSV file.
    
#     Returns:
#     None
#     """
#     try:
#         # Check if the file already exists
#         if os.path.exists(file_name):
#             print(f"File '{file_name}' already exists. Overwriting...")
        
#         # Create a DataFrame and write to CSV
#         df = pd.DataFrame(data)
#         df.to_csv(file_name, index=False, header=False)
#         print(f"CSV file '{file_name}' created successfully.")
#         return True
#     except Exception as e:
#         print(f"Error creating CSV file: {e}")
#         return {"Error": str(e)}

def get_current_date():
    """
    Returns the current date in the format YYYY-MM-DD.
    
    Returns:
    str: Current date in YYYY-MM-DD format.
    """
    current_date = datetime.now()
    formatted_date = current_date.strftime("%Y-%m-%d")
    return formatted_date


def get_previous_month():   
    """
    Returns the previous month in the format YYYY-MM.
    
    Returns:
    str: Previous month in YYYY-MM format.
    """
    current_date = datetime.now()
    first_day_of_current_month = current_date.replace(day=1)
    last_month = first_day_of_current_month - timedelta(days=1)
    formatted_date = last_month.strftime("%Y-%m")
    return formatted_date

def get_current_date_time():
    """
    Returns the current date and time in the format YYYY-MM-DD HHMM.
    
    Returns:
    str: Current date and time in YYYY-MM-DD-HHMM format.
    """
    current_date_time = datetime.now()
    formatted_date_time = current_date_time.strftime("%Y-%m-%d-%H%M")
    return formatted_date_time

def get_current_month():
    """
    Returns the current date in the format YYYY-MM-DD.
    
    Returns:
    str: Current date in YYYY-MM-DD format.
    """
    current_date = datetime.now()
    formatted_date = current_date.strftime("%Y-%m")
    return formatted_date

def get_aae_date():
    """
    Returns the current date in the format YYYY-MM-DD.
    
    Returns:
    str: Current date in YYYY-MM-DD format.
    """
    account_type = ''
    account_no, AWS_REGION = get_aws_account_id_and_region()
    if not account_no:
        print("AWS Account ID not found. Please check your AWS credentials.")
        return {"Error": "AWS Account ID not found."}
    
    acct_name = get_aws_account_name_by_id(account_no)
    if 'nonprod' in acct_name.lower():
        account_type = 'nonprod'
    else:
        account_type = 'prod'
    
    current_date = datetime.now()
    if account_type == 'nonprod':
        # Add 7 days to the current date
        aae_date = current_date + timedelta(days=7) 
    else:
         # Add 14 days to the current date
        aae_date = current_date + timedelta(days=14) 
    formatted_aae_date = aae_date.strftime("%m/%d/%Y")
    return formatted_aae_date

def get_monthly_cost_by_snapshot_id(snapshot_id):
    """Calculate the  1 month of cost for a specified EBS snapshot using.
    Note: botocore.errorfactory.AccessDeniedException: An error occurred (AccessDeniedException) when calling the GetProducts operation: You are not authorized to perform this operation. Please contact your AWS account administrator for assistance.
    Args:
    snapshot_id (str): The ID of the EBS snapshot for which to retrieve the cost.
    
    Returns:
    monthly_cost (float): The estimated monthly cost of the EBS snapshot in USD.
    """
    
    # Initialize the Boto3 EC2 client
    acct_no, region = get_aws_account_id_and_region()
    ec2 = boto3.client('ec2')
    pricing = boto3.client('pricing', region_name=region)  # Pricing API is only available in us-east-1


    response = ec2.describe_snapshots(SnapshotIds=[snapshot_id])
    snapshot = response['Snapshots'][0]
    size_gb = snapshot['VolumeSize']  # Size in GB
   
    print(f"Snapshot ID: {snapshot_id}, Size in GB: {size_gb}")  # Debugging line to check the snapshot size

    response = pricing.get_products(
        ServiceCode='AmazonEC2',
        Filters=[
            {'Type': 'TERM_MATCH', 'Field': 'productFamily', 'Value': 'Storage'},
            {'Type': 'TERM_MATCH', 'Field': 'storageMedia', 'Value': 'AmazonEBS'},
            {'Type': 'TERM_MATCH', 'Field': 'volumeType', 'Value': 'EBS:Snapshot'},
            {'Type': 'TERM_MATCH', 'Field': 'location', 'Value': region}
        ],
        MaxResults=1
    )
    print(f"Response from Pricing API: {response}")  # Debugging line to check the response structure
    return
    # Parse the pricing information
    price_list = response['PriceList']
    price_details = price_list[0]
    
    import json
    price_json = json.loads(price_details)
    price_per_gb_month = float(price_json['terms']['OnDemand'].values().__iter__().__next__()['priceDimensions'].values().__iter__().__next__()['pricePerUnit']['USD'])
    
    # Calculate the monthly cost
    monthly_cost = size_gb * price_per_gb_month

    print(f'Monthly cost for snapshot {snapshot_id}: ${monthly_cost:.2f}')
    return monthly_cost
 
def get_monthly_cost(service_name="AmazonCloudWatch"):
    """Retrieves the last 3 months of cost for a specified AWS service using the Cost Explorer API.
    Args:
    service_name (str): The name of the AWS service for which to retrieve the cost. Default is "AmazonCloudWatch".
    Returns:
    list: A list containing the last 3 months of costs for the specified service, formatted as [month, cost].
    """
    
    start_date = (datetime.now() - timedelta(days=180)).strftime('%Y-%m-01')  # Start of the month 30 days ago
    end_date = datetime.now().strftime('%Y-%m-%d')  # Current date

    
    client = boto3.client('ce')  # Cost Explorer client
    try:
        if service_name and service_name.strip() == "AmazonCloudWatch":
            response = client.get_cost_and_usage(
                TimePeriod={
                    'Start': start_date,
                    'End': end_date
                },
                Granularity='MONTHLY',
                Filter={
                    'Dimensions': {
                        'Key': 'SERVICE',
                        'Values': [service_name]
                    }
                },
                Metrics=['UnblendedCost']
            )
        elif  "SnapshotUsage" in service_name :
            response = client.get_cost_and_usage(
                TimePeriod={
                    'Start': start_date,
                    'End': end_date
                },
                Granularity='MONTHLY',
                Filter={
                    'Dimensions': {
                        'Key': 'USAGE_TYPE',
                        'Values': [service_name]
                    }
                },
                Metrics=['UnblendedCost']
            )
        elif service_name and service_name.strip() == "Amazon Relational Database Service":
            response = client.get_cost_and_usage(
                TimePeriod={
                    'Start': start_date,
                    'End': end_date
                },
                Granularity='MONTHLY',
                Filter={
                    'Dimensions': {
                        'Key': 'SERVICE',
                        'Values': [service_name]
                    }
                },
                Metrics=['UnblendedCost']
            )
        elif service_name and service_name.strip() == "Amazon Elastic Block Store":
            # This else will handle "Amazon Elastic Block Store" and any other service
            response = client.get_cost_and_usage(
                TimePeriod={'Start': start_date, 'End': end_date},
                Granularity='MONTHLY',
                Filter={
                    'Dimensions': {
                        'Key': 'SERVICE',
                        'Values': [service_name]
                    }
                },
                Metrics=['UnblendedCost']
            )

    except client.exceptions.InvalidParameterValueException as e:
        print(f"Invalid parameter value: {e}")
        return []
    last_6_mnths_cost = []
    rec_count = 0
    #print(response)
    for result in response['ResultsByTime']:
        rec_count += 1
        last_6_mnths_cost.append([result['TimePeriod']['Start'][:-3],"$"+str(round(float(result['Total']['UnblendedCost']['Amount']),2))])
        #print(f"Billing Period: {result['TimePeriod']['Start']} to {result['TimePeriod']['End']}")
       # print(f"Monthly cost for {service_name}: ${result['Total']['UnblendedCost']['Amount']}")
        if rec_count == 6:
            break

    return last_6_mnths_cost[::-1]  # Reverse the list to show the most recent month first

def get_active_db_connections(rds_instance_id,days=7): 
    """
    Retrieves the active database connections for a given RDS instance ID using AWS CloudWatch metrics.
    Args:       
    rds_instance_id (str): The RDS instance identifier for which to retrieve active connections.
    Returns:
    None: Prints the active database connections for the specified RDS instance.
    """
    # Create a CloudWatch client
    cloudwatch = boto3.client('cloudwatch')
    # Define the time range for the last month
    end_time = datetime.now()
    start_time = end_time - timedelta(days=days)

    # Get the CloudWatch metrics for DatabaseConnections
    response = cloudwatch.get_metric_statistics(
        Namespace='AWS/RDS',
        MetricName='DatabaseConnections',
        Dimensions=[
            {'Name': 'DBInstanceIdentifier', 'Value': rds_instance_id}
        ],
        StartTime=start_time,
        EndTime=end_time,
        Period=86400,  # One data point per day
        Statistics=['Average']
    )
    
    # Extract the data points
    connections_data_points = response['Datapoints']
    if connections_data_points:
        # for dp in connections_data_points:
        #     dp['Average'] = round(dp['Average'], 2)
        # connections_data_points.sort(key=lambda x: x['Timestamp'])
        # # Print the data points
        # print(f"Database Connections for instance '{rds_instance_id}' over the last {days} days:")
        # for dp in connections_data_points:
        #     print(f"Date: {dp['Timestamp'].strftime('%Y-%m-%d')}, Average Connections: {dp['Average']}")
        # Calculate the average connections
        average_connections = sum(dp['Average'] for dp in connections_data_points) / len(connections_data_points)
        print(f"Average Database Connections for instance '{rds_instance_id}' over the last {days} days: {average_connections:.2f}")
        return round(average_connections, 2)
    else:
        print("No data points found for the specified time range.")
        return None


def get_table_html(header, data):
    """
    Generates an HTML table from the provided header and data.
    
    Args:
    header (list): List of column headers for the table.
    data (list): List of rows, where each row is a list of values.
    
    Returns:
    str: HTML string representing the table.
    """
    html = "<table border='1'>\n"
    html += "<tr bgcolor='#FF6600' style='color: white;' >" + "".join(f"<th>{col}</th>" for col in header) + "</tr>\n"
    for row in data:
        html += "<tr>" 
        for val in row:
                html += f"<td>{val}</td>"
        html += "</tr>\n"
    html += "</table>"
    return html

def get_aws_account_id_and_region():
    """Retrieves the AWS account ID and region using the Boto3 library.
    
    Returns:
    tuple: (account_id, region)
    """
    # Initialize a Boto3 session
    session = boto3.Session()
    
    # Get the current region
    region = session.region_name

    # Get the account ID by calling STS
    sts_client = session.client('sts')
    account_id = sts_client.get_caller_identity().get('Account')

    return account_id, region

def setup_logging(log_to_console=False):
    """
    Sets up logging with a dynamically created log file based on the timestamp 
    and the name of the calling script. Optionally logs to the console.
    
    Args:
    log_to_console (bool): If True, logs to the console. Default is False.
    """
    # Get the calling script's name
    caller_name = inspect.stack()[1].filename
    script_name = os.path.basename(caller_name).split('.')[0]

    # Get AWS account ID and region
    account_id, region = get_aws_account_id_and_region()

    # Setting timezone to IST
    ist_tz = pytz.timezone('Asia/Kolkata')
    current_timestamp = datetime.now(ist_tz).strftime('%d-%m-%Y_%H:%M:%S')
    
    # Log file will have the timestamp as before
    log_file = f"{script_name}_{current_timestamp}.log"

    # Set up logging configuration
    handlers = [logging.FileHandler(log_file)]
    
    # If log_to_console is True, add a console handler
    if log_to_console:
        handlers.append(logging.StreamHandler())

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=handlers
    )

    # Log AWS account and region info only once at the start
    logging.info(f"Logging started for {script_name}. AWS Account ID: {account_id}, Region: {region}")
    return log_file 

# Wrapper functions for various log levels
def log_info(message):
    logging.info(message)

def log_warning(message):
    logging.warning(message)

def log_error(message):
    logging.error(message)

def log_debug(message):
    logging.debug(message)

def log_critical(message):
    logging.critical(message)

def log_exception(exception):
    logging.exception(f"An exception occurred: {exception}")

def get_cloudability_secrets_by_view(view_name="GBS_ALL"):
    """Retrieves the Cloudability secrets for a given view name from a JSON file.
    Args:
    view_name (str): The name of the view for which to retrieve secrets. Default is "GBS_ALL".
    Returns:
    tuple: A tuple containing the public key and secret key for the specified view.
    """
    cloudability_secrets = "./config/cloudability_secrets.json"
    if not os.path.exists(cloudability_secrets):
        log_error(f"account contact file not found: {cloudability_secrets}")
        return ""
    
    with open(cloudability_secrets, 'r') as file:
        try:
            secrets_data = json.load(file)
            sec_json = secrets_data.get(view_name, {})
            if sec_json:
                pub_key = sec_json.get('FD_API_PUBLIC_KEY', "")
                sec_key = sec_json.get('FD_API_SECRET_KEY', "")

                return pub_key, sec_key
        except json.JSONDecodeError as e:
            log_exception(e)
            return "",""

def get_accounts_for_gbs_org(detail_type="all",chris_direct_name=""):    
    """Retrieves the AWS accounts for the GBS organization from a JSON file."""

    gbs_accounts_file = "./config/monthly_report_mapings.json"
    if not os.path.exists(gbs_accounts_file):
        log_error(f"GBS accounts file not found: {gbs_accounts_file}")
        return []
    
    accounts_list = []
    with open(gbs_accounts_file, 'r') as file:
        try:
            accounts_data = json.load(file)
            if detail_type == "all":
                return accounts_data
            elif detail_type == "chris_directs":
                return list(accounts_data.keys())
            elif detail_type == "accounts":
                for chris_direct in list(accounts_data.keys()):
                    cd_json = accounts_data.get(chris_direct, {})
                    if cd_json:
                        accounts = cd_json.get('accounts', "")
                        if accounts:
                            accounts_list.extend(accounts)
                return accounts_list
            elif detail_type == "chris_direct_accounts" and chris_direct_name:
                
                cd_json = accounts_data.get(chris_direct_name, {})
                if cd_json:
                    accounts = cd_json.get('accounts', "")
                    if accounts:
                        accounts_list.extend(accounts)
                return accounts_list
            elif detail_type == "report_data_keys":
                report_data_keys = accounts_data.get('pradeep.pai@Fiserv.com', {}).get('report_data_keys', [])
                return report_data_keys
                
            else:
                log_error(f"Invalid detail_type: {detail_type}. Expected 'all' or 'account_ids'.")
                return []
        except json.JSONDecodeError as e:
            log_exception(e)
            return []

def get_account_conatct_details(account_id):
    """
    Retrieves the contact details for a given AWS account ID from a JSON file.
    
    Args:
    account_id (str): The AWS account ID for which to retrieve contact details.
    
    Returns:
    string: A string containing the contacts with , separated values for the specified account ID.
    """
    account_contacts_file = "./config/account_contacts.json"
    if not os.path.exists(account_contacts_file):
        log_error(f"account contact file not found: {account_contacts_file}")
        return ""
    
    with open(account_contacts_file, 'r') as file:
        try:
            accounts_data = json.load(file)
            cont_json = accounts_data.get(account_id, {})
            if cont_json:
                contacts = cont_json.get('contacts', "")
                CCList = cont_json.get('CCList', "")

                return contacts, CCList
        except json.JSONDecodeError as e:
            log_exception(e)
            return "",""

def get_splunk_destination_arn_region(region_name):
    """
    Retrieves the Splunk destination ARN based on the specified AWS region.
    Args:
    region_name (str): The AWS region for which to retrieve the Splunk destination ARN.
    Returns:
    str: The Splunk destination ARN for the specified region, or an error message if the region is unsupported.
    """
    splunk_sub_fil_arns_file = "./config/splunk_subscription_filter_arns.json"
    destination_arn = ""
    if not os.path.exists(splunk_sub_fil_arns_file):
        log_error(f"splunk subscription filter arns file not found: {splunk_sub_fil_arns_file}")
        return ""
    with open(splunk_sub_fil_arns_file, 'r') as file:
        try:
            arn_data = json.load(file)
            destination_arn_json = arn_data.get(region_name, None)
            if destination_arn_json:
                destination_arn = destination_arn_json.get("destination_arn", None)
                return destination_arn
            else:   
                log_error(f"Region {region_name} not found in splunk subscription filter arns file.")
                return ""
        except json.JSONDecodeError as e:
            log_exception(e)
            return ""


def check_subscription_filter(log_group_name, destination_arn=""):
    # Create a CloudWatch Logs client
    client = boto3.client('logs')
    arn_found = 'N'
    # Retrieve the subscription filters for the specified log group
    response = client.describe_subscription_filters(
        logGroupName=log_group_name
    )
    
    # Check if there are any subscription filters attached
    if response['subscriptionFilters']: 
        for filter in response['subscriptionFilters']:
            if filter['destinationArn'] == destination_arn:
                #print(f"Subscription filter found for log group '{log_group_name}' with ARN: {filter['destinationArn']}")
                arn_found = 'Y' 
    else:
        arn_found = 'N'
    
    return arn_found


def get_log_groups_with_retention(retention_days=7):
    """
    Retrieves all CloudWatch log groups with a retention period greater than or equal to the specified number of days.
    Args:
    retention_days (int): The minimum retention period in days to filter log groups. Default is 1 day.
    Returns:
    list: A list of log group names with their retention periods that match the specified criteria.
    """
    # Create a CloudWatch Logs client
    client = boto3.client('logs')

    # Initialize variables
    acct_no, region = get_aws_account_id_and_region()
    sp_sub_fltr_arn = get_splunk_destination_arn_region(region)
    next_token = None
    list_of_log_groups_with_retention_detail_and_sub_fltr_stat = []

    # Loop to handle pagination
    while True:
        # Build the parameters for the describe_log_groups call
        params = {}
        if next_token:
            params['nextToken'] = next_token

        # Retrieve log groups
        response = client.describe_log_groups(**params)

        # Process each log group
        for log_group in response.get('logGroups', []):
            # Check if log group is already having required splunk subscription filter or not
            sp_sub_fltr_found = check_subscription_filter(log_group['logGroupName'], sp_sub_fltr_arn)
            # Get the retention period for the log group
            retention_in_days = log_group.get('retentionInDays')

            # Check if the log group's retention period matches the specified period
            if retention_in_days and retention_in_days > retention_days:
                gr_name_n_ret_days_sub_ft_stat = log_group['logGroupName'] + ":" + str(retention_in_days) + ":" + sp_sub_fltr_found
                list_of_log_groups_with_retention_detail_and_sub_fltr_stat.append(gr_name_n_ret_days_sub_ft_stat)
            elif not retention_in_days:  
                # If retentionInDays is None, it means the log group never expires
                gr_name_n_ret_days_sub_ft_stat = log_group['logGroupName'] + ":Never expire" + ":" + sp_sub_fltr_found
                list_of_log_groups_with_retention_detail_and_sub_fltr_stat.append(gr_name_n_ret_days_sub_ft_stat)
        # Check if there is a next token
        next_token = response.get('nextToken')
        if not next_token:
            break

    return list_of_log_groups_with_retention_detail_and_sub_fltr_stat

def get_given_log_groups_with_retention(log_groups,retention_days=1):
    """
    Retrieves all CloudWatch log groups with a retention period greater than or equal to the specified number of days.
    Args:
    retention_days (int): The minimum retention period in days to filter log groups. Default is 1 day.
    Returns:
    list: A list of log group names with their retention periods that match the specified criteria.
    """
    # Create a CloudWatch Logs client
    client = boto3.client('logs')

    # Initialize variables
    acct_no, region = get_aws_account_id_and_region()
    sp_sub_fltr_arn = get_splunk_destination_arn_region(region)
    next_token = None
    list_of_log_groups_with_retention_detail_and_sub_fltr_stat = []

    # Loop to handle pagination
    while True:
        # Build the parameters for the describe_log_groups call
        params = {}
        if next_token:
            params['nextToken'] = next_token

        # Retrieve log groups
        response = client.describe_log_groups(**params)

        # Process each log group
        for log_group in response.get('logGroups', []):
            if log_groups:
                for lg in log_groups:
                    if lg.split(',')[0].strip().replace('\n','') not in log_group['logGroupName']:
                        continue 
                    else:
                        print(f"Log group found: {log_group['logGroupName']}")
                        # Check if log group is already having required splunk subscription filter or not
                        sp_sub_fltr_found = check_subscription_filter(log_group['logGroupName'], sp_sub_fltr_arn)
                        # Get the retention period for the log group
                        retention_in_days = log_group.get('retentionInDays')

                        # Check if the log group's retention period matches the specified period
                        if retention_in_days and retention_in_days >= retention_days:
                            gr_name_n_ret_days_sub_ft_stat = log_group['logGroupName'] + ":" + str(retention_in_days) + ":" + sp_sub_fltr_found
                            list_of_log_groups_with_retention_detail_and_sub_fltr_stat.append(gr_name_n_ret_days_sub_ft_stat)
                        else:
                            gr_name_n_ret_days_sub_ft_stat = log_group['logGroupName'] + ":Never expire" + ":" + sp_sub_fltr_found
                            list_of_log_groups_with_retention_detail_and_sub_fltr_stat.append(gr_name_n_ret_days_sub_ft_stat)
                continue
            

        # Check if there is a next token
        next_token = response.get('nextToken')
        if not next_token:
            break
    return list_of_log_groups_with_retention_detail_and_sub_fltr_stat


def add_subscription_filter_to_log_group(log_group_name, filter_name="Splunk",filter_pattern="", destination_arn=""):
    """
    Adds a subscription filter to a specified CloudWatch log group.
    
    Args:
    log_group_name (str): The name of the log group to which the subscription filter will be added.
    filter_name (str): The name of the subscription filter.
    filter_pattern (str): The pattern to match log events.
    destination_arn (str): The ARN of the destination for the subscription filter.
    
    Returns:
    dict: Response from the AWS API call.
    """
    client = boto3.client('logs')
    
    AWS_REGION = os.getenv('AWS_REGION')
    if not AWS_REGION:
        session = boto3.Session()
        AWS_REGION = session.region_name

    destination_arn = get_splunk_destination_arn_region(AWS_REGION)
    if not destination_arn:
        log_error(f"Splunk destination ARN not found for region {AWS_REGION}.")
        return {"Error": f"Splunk destination ARN not found for region {AWS_REGION}."}
    chk_sub_fltr = check_subscription_filter(log_group_name, destination_arn)
    if chk_sub_fltr == 'Y':
        log_info(f"Subscription filter already exists for log group '{log_group_name}' with ARN: {destination_arn}")
        return {"Message": f"Subscription filter already exists for log group '{log_group_name}' with ARN: {destination_arn}"}
    
    try:
        response = client.put_subscription_filter(
        logGroupName=log_group_name,
        filterName=filter_name,
        filterPattern=filter_pattern,
        destinationArn=destination_arn
        )
        
        return response
    except Exception as e:
        log_exception(e)
        return {"Error": str(e)}
    
def get_aws_account_name_by_id(account_id):
    """
    Retrieves the AWS account name based on the provided account ID.
    
    Args:
    account_id (str): The AWS account ID for which to retrieve the name.
    
    Returns:
    str: The name of the AWS account, or an error message if not found.
    """
    jetbridge_accounts_file = "./config/jetbridge_accounts.json"
    if not os.path.exists(jetbridge_accounts_file):
        log_error(f"Jetbridge accounts file not found: {jetbridge_accounts_file}")
        return "Jetbridge accounts file not found."
    with open(jetbridge_accounts_file, 'r') as file:
        try:
            accounts_data = json.load(file)
            account_name = accounts_data.get(account_id, {}).get('name', None)
            if account_name:
                return account_name
            else:
                log_error(f"Account ID {account_id} not found in jetbridge-accounts.json.")
                return f"Account ID {account_id} not found in jetbridge-accounts.json." 
        except json.JSONDecodeError as e:
            log_exception(e)
            return "Error decoding JSON from jetbridge-accounts.json file."


def send_email(menv="", email_type="FinOps-Automation-Report", sender_list="mukesh.kumar4@fiserv.com",cc_list="gurminder.sidhu@fiserv.com",email_body="",test="N",file_name=""):
    """
    Sends an email notification with the specified parameters.
    
    Args:
    menv (str): The environment for which the email is being sent.
    email_type (str): The type of release or report. Default is "Jacoco".
    sender_list (str): Comma-separated list of email addresses to send the notification to.
    cc_list (str): Comma-separated list of email addresses to CC. Default is "  
    email_body (str): The body of the email to be sent. 
   
    Returns:
    None
    """
    account_no, AWS_REGION = get_aws_account_id_and_region()
    if not account_no:
        print("AWS Account ID not found. Please check your AWS credentials.")
        return {"Error": "AWS Account ID not found."}
    
    if not menv:
        menv = get_aws_account_name_by_id(account_no)
    sender_list = sender_list.split(",")
    dear_address = ""
    for sender in sender_list:
        if dear_address.strip() == "":
            dear_address = sender.split('.')[0].strip().capitalize()
        else:
            dear_address = dear_address + ", " + sender.split('.')[0].strip().capitalize()
    if test.upper() == "Y":
        CCADDRESSES = ["mukesh.kumar4@fiserv.com"]  
    else:
        CCADDRESSES = ["sreedhar.potturi@Fiserv.com", "mukesh.kumar4@fiserv.com", "carlos.torrens@fiserv.com"] 

    CCADDRESSES = CCADDRESSES + cc_list.split(",") 
    
    mysub = email_type + "(" + menv + ")"
    env_name = account_no + "-" + menv + " <b>Region:</b>" + AWS_REGION

    if "Action Execution Report" in email_type:
        email_start_text = "As per approval and exception received from you, below FinOps Cost Optimization  has been executed successfully. Please monitor any functionality directly or indirectly impacted due to this execution for 1-2 weeks from Today and reply to this email with any issue or new exception. " \
        "A meeting to discuss the same will be scheduled if required and recommended action execution Logic will be updated to overcome similar issues in future."
    else:
        email_start_text = "Please review below FinOps Cost Optimization Recommendation and reply to this email with your approval to allow automation to execute the recommended action. If you have any applicable exceptions, please include them as well."
    
    try:
        SENDER = "finops-automations@mail.fiserv.com"
        RECIPIENT = sender_list
        AWS_REGION = AWS_REGION
        SUBJECT = mysub
        BODY_HTML = """<html>
        <head></head>
        <body> Dear """ + dear_address + """,
        <br>
        """ + email_start_text + """ <br>
        <br>
        <h1> """ + email_type + """ </h1>
        <p>
        <b>ENV Name:</b> """ + env_name + """ <br>
        """ + email_body + """ <br>

        <br>
        Thanks, <br>
        MSTech Platform Engineering Team<br>
        DL-NA-MSTech-Platform-Eng@fiserv.com <br>
        </p>
        </body>
        </html>
        """
        # The character encoding for the email.
        CHARSET = "UTF-8"

        ses = boto3.client("ses", region_name=AWS_REGION)
        
        # Try to send the email.
        try:
            response = ses.send_email(
            Destination={
            'ToAddresses': RECIPIENT,
            'CcAddresses': CCADDRESSES
            },
            ReplyToAddresses=['mukesh.kumar4@fiserv.com'],
            Message={
            'Body': {
            'Html': {
            'Charset': CHARSET,
            'Data': BODY_HTML,
            },
            'Text': {
            'Charset': CHARSET,
            'Data': "",
            },
            },
            'Subject': {
            'Charset': CHARSET,
            'Data': SUBJECT,
            },
            },
            Source=SENDER,
            # # If you are not using a configuration set, comment or delete the
            # # following line
            # ConfigurationSetName=CONFIGURATION_SET,
            )
            # Display an error if something goes wrong.
            
        except Exception as e:
            log_exception(e)
            print(f"Error sending email: {e}")
            return {"Error": str(e)}
        else:
            print(f"Email sent! Message ID: {response['MessageId']}")
            return response
    except Exception as e:
        log_exception(e)
        print(f"Error in send_email function: {e}")
        return {"Error": str(e)}    


def send_email_with_attachment(menv="Test", email_type="FinOps-Monthly-Cost-Saving-Report", sender_list="mukesh.kumar4@fiserv.com",cc_list="mukesh.kumar4@fiserv.com",email_body="Test",test="Yes",filename="/Users/mukesh.kumar4/mpe/finopsautomations/test.txt"): 
    """
    Sends an email with an attachment using AWS SES.
    
    Args:
    menv (str): The environment for which the email is being sent.
    email_type (str): The type of release or report. Default is "Jacoco".
    sender_list (str): Comma-separated list of email addresses to send the notification to.
    cc_list (str): Comma-separated list of email addresses to CC. Default is "  
    email_body (str): The body of the email to be sent. 
   
    Returns:
    None
    """
    # Email configuration
    sender_email = "finops-automations@mail.fiserv.com"
    RECIPIENT = sender_email.split(",")
    receiver_email = sender_list
    RECIPIENT = receiver_email.split(",")
    CCADDRESSES = ["mukesh.kumar4@fiserv.com"]
    subject = 'Test Email with Attachment'
    body_html = """
    <html>
    <head></head>
    <body>
        <h1>This is Test Email</h1>
        <p>FinOps Cost Saving Report</p>
    </body>
    </html>
    """

    # Create a multipart message
    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = receiver_email
    msg['Subject'] = subject

    # Add body to email
    body = MIMEText(body_html, 'html')
    msg.attach(body)

    # Attach the file
    with open(filename, 'rb') as attachment:
        part = MIMEApplication(attachment.read())
        part.add_header(
            "Content-Disposition",
            f"attachment; filename= {os.path.basename(filename)}",
        )
        msg.attach(part)

    # Convert message to string
    raw_msg = msg.as_string()
    print(os.path.basename(filename))
    # Encode the message in base64
    raw_msg_bytes = raw_msg.encode('utf-8')
    raw_msg_base64 = base64.b64encode(raw_msg_bytes).decode('utf-8')

    # Initialize Boto3 SES client
    ses_client = boto3.client('ses')

    # Send email
    try:
        response = ses_client.send_raw_email(
            RawMessage={
                'Data': raw_msg_base64
            },
            Source=sender_email,
            Destinations=RECIPIENT
        )
        print("Email sent successfully.")
        print(response)
    except Exception as e:
        print(f"Error: {e}")

def send_monthly_finops_report_email(menv="", email_type="FinOps-Automation-Report", sender_list="mukesh.kumar4@fiserv.com",cc_list="sreedhar.potturi@Fiserv.com",email_body="",test="N"):
    """
    Sends an email notification with the specified parameters.
    
    Args:
    menv (str): The environment for which the email is being sent.
    email_type (str): The type of release or report. Default is "Jacoco".
    sender_list (str): Comma-separated list of email addresses to send the notification to.
    cc_list (str): Comma-separated list of email addresses to CC. Default is "  
    email_body (str): The body of the email to be sent. 
   
    Returns:
    None
    """
    account_no, AWS_REGION = get_aws_account_id_and_region()
    if not account_no:
        print("AWS Account ID not found. Please check your AWS credentials.")
        return {"Error": "AWS Account ID not found."}
    
    if not menv:
        menv = get_aws_account_name_by_id(account_no)
    sender_list = sender_list.split(",")
    dear_address = ""
    for sender in sender_list:
        if dear_address.strip() == "":
            dear_address = sender.split('.')[0].strip().capitalize()
        else:
            dear_address = dear_address + ", " + sender.split('.')[0].strip().capitalize()
    if test.upper() == "Y":
        CCADDRESSES = ["mukesh.kumar4@fiserv.com"]  
    else:
        CCADDRESSES = ["sreedhar.potturi@Fiserv.com"] 

    CCADDRESSES = CCADDRESSES + cc_list.split(",") 
    
    mysub = email_type 
    
    try:
        SENDER = "finops-automations@mail.fiserv.com"
        RECIPIENT = sender_list
        AWS_REGION = AWS_REGION
        SUBJECT = mysub
        BODY_HTML = """<html>
        <head></head>
        <body> Dear """ + dear_address + """,
        <br>
        
        <p>
        """ + email_body + """ <br>

        <br>
        Thanks, <br>
        MSTech Platform Engineering Team<br>
        DL-NA-MSTech-Platform-Eng@fiserv.com <br>
        </p>
        </body>
        </html>
        """
        # The character encoding for the email.
        CHARSET = "UTF-8"

        ses = boto3.client("ses", region_name=AWS_REGION)
        
        # Try to send the email.
        try:
            response = ses.send_email(
            Destination={
            'ToAddresses': RECIPIENT,
            'CcAddresses': CCADDRESSES
            },
            ReplyToAddresses=['mukesh.kumar4@fiserv.com'],
            Message={
            'Body': {
            'Html': {
            'Charset': CHARSET,
            'Data': BODY_HTML,
            },
            'Text': {
            'Charset': CHARSET,
            'Data': "",
            },
            },
            'Subject': {
            'Charset': CHARSET,
            'Data': SUBJECT,
            },
            },
            Source=SENDER,
            # # If you are not using a configuration set, comment or delete the
            # # following line
            # ConfigurationSetName=CONFIGURATION_SET,
            )
            # Display an error if something goes wrong.
            
        except Exception as e:
            log_exception(e)
            print(f"Error sending email: {e}")
            return {"Error": str(e)}
        else:
            print(f"Email sent! Message ID: {response['MessageId']}")
            return response
    except Exception as e:
        log_exception(e)
        print(f"Error in send_email function: {e}")
        return {"Error": str(e)} 

if __name__ == '__main__':
    print("This module is not meant to be run directly. Please import it in your script and call required function from its available list.")
    # Example usage
    # log_groups = []
    # retention_days = 1  # Specify the retention period in days
    # log_groups = get_log_groups_with_retention(retention_days)
    # print(f"Log groups with retention period >= {retention_days} days:")
    # print("Total log groups found:", len(log_groups))

    # for log_group in log_groups:
    #     print(log_group)

    #print(add_subscription_filter_to_log_group("/ecs/dev-hello-world-lg", filter_name="Splunk", filter_pattern="", destination_arn=""))
    # print(response)

    #send_email(menv="nonprod", email_type="test-email",email_body="This is a test email body for FinOps Automation Report.", sender_list="mukesh.kumar4@fiserv.com")
    #print(get_aws_account_name_by_id("058264069035"))  # Replace with a valid account ID for testing
    # resp=check_subscription_filter("/ecs/qa-hello-world-lg","arn:aws:logs:us-east-1:871681779858:destination:6f8c45cc-97d5-4fc6-9165-18fea6640d16")  # Replace with a valid log group name for testing
    # print(resp)
    # print(get_splunk_destination_arn_region("us-east-4"))
    # print(get_account_conatct_details('958612202038'))
    #print(get_splunk_destination_arn_region("us-west-2"))
    # Example usage
    # send_email(menv="nonprod", email_type="FinOps-Automation-Report", sender_list="mukesh.kumar4@fiserv.com", email_body="This is a test email body for FinOps Automation Report.")
    # print(get_log_groups_with_retention(retention_days=7))
    #print(get_active_db_connections('database-3-instance-3',30))
    #print(get_monthly_cost(service_name="USW2-EBS:SnapshotUsage"))
    #print(get_monthly_cost(service_name="Amazon Relational Database Service"))
    #print(get_monthly_cost(service_name="AmazonCloudWatch"))
    #get_monthly_cost_by_snapshot_id('snap-03604bf47b272dc51')
    #print(get_cloudability_secrets_by_view("GBS_ALL"))
    #print(get_aae_date())
    #create_csv_file("test.csv", [["Name", "Location"], ["Mukesh", "NE"], ["Sreedhar", "NJ"]])
    #send_email_with_attachment()
    #write_data_to_confluent_topic()
    #get_savings_opportunities_for_aws_account()
    #write_data_to_confluent_topic(key="test_key1", value="test_value1")
    #write_data_to_kafka_topic()
    #write_data_to_confluent_topic(key="test_ke4", value="test_value4")
    #write_data_to_confluent_topic(key="test_ke7", value="test_value7")
    #read_data_from_confluent_topic()
    #print(get_current_month())
    #print(get_previous_month())
    #print(get_accounts_for_gbs_org(detail_type="chris_directs"))
    #print(get_accounts_for_gbs_org(detail_type="accounts"))
    #print(get_accounts_for_gbs_org(detail_type="report_data_keys"))
    #print(get_accounts_for_gbs_org(detail_type="chris_direct_accounts", chris_direct_name="pradeep.pai@Fiserv.com"))
    #print(update_dynamodb_table())
    #print(read_data_from_dynamodb_table(AccountNumber="307946647371"))


    account_no, aws_region = get_aws_account_id_and_region()
    with open('update_log_groups_exceptions.input', "r") as file:
        app_log_groups_det = file.readlines()

    mydata = []
    for line in app_log_groups_det:
        mydata.append(line.strip().replace('\n', ''))
    
    print(mydata)
    excep_data = json.dumps(mydata)

    print(post_data_to_url(data={"AccountNumber": account_no,"RegRecTypeDt":aws_region+"LOG_GROUP_UPDATE_EXCEPTIONS","ExecutableData":excep_data}))
    
    
    
    #print(get_services_count_for_current_account(service="Amazon Elastic Block Store"))
    #print(get_monthly_cost(service_name="EBS:SnapshotUsage"))
    #print(get_current_date_time())
    # attributes_to_update = {
    # 'SavingExecutionDate': '2025-06-12',
    # 'OptimizedResourcesCount': '(5/70)'
    # }
    # print(update_dynamodb_row(update_attributes=attributes_to_update))
    # resp = get_data_from_url(AccountNumber="307946647371", RegRecTypeDt="us-east-1LOG_GROUP_UPDATE_EXCEPTIONS")
    # excep_data = resp[0].get('ExecutableData', "")
    # if excep_data:
    #     excep_data = json.loads(excep_data)
    #     print("Log Groups with exceptions:")
    #     for lg in excep_data:
    #         print(lg)
    # else:
    #     print("No exceptions found for log groups.")
    # file_name = "test.csv"
    # #data = [{"name": "John Doe", "age": 30, "city": "New York"},{"name": "Jane Smith", "age": 25, "city": "Los Angeles"}]
    # data = [['Chris Direct', 'AWS Account Number', 'Account Name', 'Region', 'Cost Optimization Initiative', 'Optimizable Resources Count', 'Saving Opportunity', 'Saving Recommendation Date', 'Saving Execution Date', 'Optimized Resources Count', 'Realised Saving', 'Service Prev Month Cost', 'Service Execution Month Cost', 'Service Execution Month Count'], ['pradeep.pai@Fiserv.com', '544643336122', 'fdaws-marketplace-tca-nonprod', 'us-west-2', 'RDS_TERMINATION', '(2/37)', '$94.58', '2025-06-09', '', '', '', '$3369.45', '$3369.45', '37'], ['inderjeet.rana@fiserv.com', '307946647371', 'fdaws-merch-tech-pe-dev-nonprod', 'us-east-1', 'RDS_TERMINATION', '(1/9)', '$30.9', '2025-06-12', '', '', '', '$489.31', '$489.31', '9'], ['inderjeet.rana@fiserv.com', '307946647371', 'fdaws-merch-tech-pe-dev-nonprod', 'us-east-1', 'SNAPSHOT_DELETION', '(2/426)', 'TBD', '2025-06-09', '', '', '', '$10.75', '$10.75', '438'], ['inderjeet.rana@fiserv.com', '307946647371', 'fdaws-merch-tech-pe-dev-nonprod', 'us-east-1', 'LOG_GROUP_UPDATE', '(3/69)', 'TBD', '2025-06-16', '2025-06-16', '(3/69)', 'TBD', '$66.73', '$66.73', '70'], ['srikanth.muthukrishnan@Fiserv.com', '446589977811', 'FDAWS BusinessTrack Nonprod', 'us-west-2', 'RDS_TERMINATION', '(6/27)', '$553.62', '2025-06-09', '', '', '', '$12427.71', '$12427.71', '27'], ['srikanth.muthukrishnan@Fiserv.com', '446589977811', 'FDAWS BusinessTrack Nonprod', 'us-west-2', 'SNAPSHOT_DELETION', '(74/176)', 'TBD', '2025-06-09', '', '', '', '$145.87', '$145.87', '176'], ['srikanth.muthukrishnan@Fiserv.com', '675440017561', 'FDAWS BusinessTrack Prod', 'us-west-2', 'RDS_TERMINATION', '(1/15)', '$423.4', '2025-06-09', '', '', '', '$42980.66', '$42980.66', '15'], ['srikanth.muthukrishnan@Fiserv.com', '675440017561', 'FDAWS BusinessTrack Prod', 'us-west-2', 'SNAPSHOT_DELETION', '(42/181)', 'TBD', '2025-06-09', '', '', '', '$114.13', '$114.13', '178']]
    # create_csv_file(file_name, data)
    # account = "544643336122"
    # RegRecTypeDt = "us-east-1MED2025-05"
    # print(get_data_from_url(AccountNumber=account, RegRecTypeDt=RegRecTypeDt))
    # data = {
    #     "AccountNumber": "449280153920",
    #     "RegRecTypeDt": "us-west-2LOG_GROUP_UPDATE_R2025-06",
    #     "update_attributes": {"SavingExecutionDate": "2025-06-20", "OptimizedResourcesCount": "(130/142)","RealisedSaving": "TBD"}
    # }
    # print(update_data_to_url(data=data))

    #print(get_data_from_url(AccountNumber="307946647371", RegRecTypeDt="us-east-1LOG_GROUP_UPDATE_EXCEPTIONS"))
    # mydata = {'AccountNumber': '130382812681', 'RegRecTypeDt': 'us-west-2SNAPSHOT_DELETION_R2025-06', 'AccountName': 'fdaws-umm-tca-prod', 'Region': 'us-west-2', 'OptimizationName': 'SNAPSHOT_DELETION', 'OptimizableResourcesCount': '24/304', 'FinOpsSavingOpportunity': 'TBD', 'FinOpsSavingRecommendationDate': '2025-06-24', 'LastMonthCost': '$176.82', 'SavingExecutionDate': '', 'OptimizedResourcesCount': '', 'RealisedSaving': ''}
    # print(post_data_to_url(data=mydata))
    
        
        
        
       

        
        

