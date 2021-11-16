import logging
import boto3
import uuid
import argparse
import sys
import os
from botocore.exceptions import ClientError

logging.basicConfig(level=logging.INFO)


def parse_cmd_line_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--profile', '-p', help="AWS profile", type=str)
    parser.add_argument('--region', '-r', help="AWS region", type=str)
    parser.add_argument('--toolzip', '-t', help="Memory Capture tool zip file", type=str)
    parser.add_argument('--targetid', '-i', help="ID of the target machine.", type=str)
    parser.add_argument('--role', '-l', help="Role to attach to TempWorkstation", type=str)


    args = parser.parse_args()
    return args


def get_account_id(sts_client):
    response = sts_client.get_caller_identity()
    return response.get('Account')


def make_bucket(account_id, region, bucket_prefix, s3_client):
    location = {'LocationConstraint': region}
    bucket_name = ""

    while True:
        try:
            my_uuid = str(uuid.uuid4())[:8]
            bucket_name = bucket_prefix + "-" + account_id + "-" + region + "-" + my_uuid  
            s3_client.create_bucket(Bucket=bucket_name)
        except ClientError as e:
            logging.error(e)
            next
        break
    logging.info("Created bucket: " + bucket_name)
    return bucket_name

def delete_bucket(bucket_name, s3_resource):
    try:
        bucket = s3_resource.Bucket(bucket_name)
        bucket.objects.all().delete()
        bucket.delete()
        logging.info("Bucket deleted: " + bucket_name)
    except ClientError as e:
        logging.error(e)


def upload_tools(tool_zip, bucket_name, s3_client):
    logging.info("Uploading tools to bucket...")

    object_name = os.path.basename(tool_zip)
    try:
        s3_client.upload_file(tool_zip, bucket_name, object_name)
    except ClientError as e:
        logging.error(e)

    logging.info("Tool upload complete.")


def build_temp_workstation(role, target_az):
    logging.info("Bulding TempWorkstation...")
    logging.info("TempWorkstation complete.")


def get_az_of_target(target_id, ec2_client):
    logging.info("Getting AZ of the target system...")
    response = "" 

    try:
        response = ec2_client.describe_instances(InstanceIds=[target_id])
    except ClientError as e:
        logging.error(e)

    instance = response["Reservations"][0]['Instances'][0]
    target_az = instance['Placement']['AvailabilityZone']
    logging.info(target_az)

    return target_az


def get_instance_type_of_target(target_id, ec2_client):
    logging.info("Getting Instance Type of the target system...")
    response = "" 

    try:
        response = ec2_client.describe_instances(InstanceIds=[target_id])
    except ClientError as e:
        logging.error(e)

    instance = response["Reservations"][0]['Instances'][0]
    instance_type = instance['InstanceType']
    logging.info(instance_type)

    return instance_type


def get_memory_size_by_instance_type(instance_type, ec2_client):
    logging.info("Getting getting memory size of target instance...")
    response = "" 

    try:
        response = ec2_client.describe_instance_types(InstanceTypes=[instance_type])
    except ClientError as e:
        logging.error(e)

    memory_size = response['InstanceTypes'][0]['MemoryInfo']['SizeInMiB']
    logging.info(str(memory_size))

    return instance_type


def get_win_2016_ami_id(ec2_client):
    logging.info("Getting Windows 2016 AMI ID...")
    response = "" 

    try:
        response = ec2_client.describe_images()
    except ClientError as e:
        logging.error(e)

    logging.info(str(response))

    return instance_type


def create_temp_workstation(ec2_client, target_az, role):
    logging.info("Creating TempWorksation....")


def main(profile, region, tool_zip, target_id, role):
    bucket_prefix = "mem-capture"

    session = boto3.Session(region_name=region, profile_name=profile)
    sts_client = session.client('sts')
    s3_client = session.client('s3')
    s3_resource = session.resource('s3')
    ec2_client = session.client('ec2')
    account_id = get_account_id(sts_client)
    
    #bucket_name = make_bucket(account_id, region, bucket_prefix, s3_client)
    #upload_tools(tool_zip, bucket_name, s3_client)
    #target_az = get_az_of_target(target_id, ec2_client)
    #instance_type = get_instance_type_of_target(target_id, ec2_client)
    #memory_size = get_memory_size_by_instance_type(instance_type, ec2_client)
    win_2016_ami_id = get_win_2016_ami_id(ec2_client)

    #temp_workstation_id = create_temp_workstation(ec2_client, target_az, role)

    #delete_bucket(bucket_name, s3_resource)
    


if __name__ == "__main__":
    args = parse_cmd_line_args()
    profile = args.profile
    region = args.region
    tool_zip = args.toolzip
    target_id = args.targetid
    role = args.role

    main(profile, region, tool_zip, target_id, role)

