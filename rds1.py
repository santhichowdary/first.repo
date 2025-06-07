
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
