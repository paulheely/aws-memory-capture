import logging
import boto3
import uuid
import argparse
import sys
import os
import time
from botocore.exceptions import ClientError

logging.basicConfig(level=logging.INFO)


def parse_cmd_line_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--profile', '-p', help="AWS profile", type=str)
    parser.add_argument('--region', '-r', help="AWS region", type=str)
    parser.add_argument('--toolzip', '-t', help="Memory Capture tool zip file", type=str)
    parser.add_argument('--targetid', '-i', help="ID of the target machine.", type=str)
    parser.add_argument('--role', '-l', help="Role to attach to TempWorkstation", type=str)
    parser.add_argument('--workami', '-a', help="AMI to use for TempWorkstation", type=str)


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


def get_target_az(target_id, ec2_client):
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


def get_target_subnet(target_id, ec2_client):
    logging.info("Getting AZ of the target system...")
    response = "" 

    try:
        response = ec2_client.describe_instances(InstanceIds=[target_id])
    except ClientError as e:
        logging.error(e)

    instance = response["Reservations"][0]['Instances'][0]
    #logging.info(instance)
    target_subnet_id = instance['SubnetId']
    logging.info(target_subnet_id)

    return target_subnet_id



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

    return memory_size


def create_temp_workstation(ec2_client, target_az, role_name, work_ami_id, subnet_id):
    logging.info("Creating TempWorksation....")

    try:
        response = ec2_client.run_instances(
                ImageId=work_ami_id,
                InstanceType='t2.micro',
                Placement={'AvailabilityZone': target_az},
                MaxCount=1,
                MinCount=1,
                SubnetId=subnet_id,
                IamInstanceProfile={
                    'Name': role_name
                },
                TagSpecifications=[
                    {
                        'ResourceType': 'instance',
                        'Tags': [
                            {
                                'Key': 'Name',
                                'Value': 'TempWorkstation'
                            }
                        ]
                    }
                ]
            )
    except ClientError as e:
        logging.error(e)


    workstation_id = response['Instances'][0]['InstanceId']
    logging.info(workstation_id)
    return workstation_id


def wait_for_workstation_to_start(temp_workstation_id, ec2_client):
    logging.info("Waiting for workstation to start...")

    try:
        while True:
            response = ec2_client.describe_instance_status(
                    InstanceIds=[temp_workstation_id])
            if response['InstanceStatuses']:
                if response['InstanceStatuses'][0]['InstanceState']['Name'] == 'running':
                    break
                else:
                    time.sleep(2)
            else:
                time.sleep(2)
    except ClientError as e:
        logging.error(e)

    logging.info('Workstation instance is running.')


def create_workdrive(target_az, work_drive_size, ec2_client):
    logging.info("Creating WorkDrive...")
    response = "" 

    try:
        response = ec2_client.create_volume(
                AvailabilityZone=target_az,
                Size=work_drive_size,
                VolumeType='gp2')
    except ClientError as e:
        logging.error(e)

    workdrive_id = response['VolumeId']
    logging.info(str(workdrive_id))

    return workdrive_id


def main(profile, region, tool_zip, target_id, role_name, work_ami_id):
    bucket_prefix = "mem-capture"

    session = boto3.Session(region_name=region, profile_name=profile)
    sts_client = session.client('sts')
    s3_client = session.client('s3')
    s3_resource = session.resource('s3')
    ec2_client = session.client('ec2')
    account_id = get_account_id(sts_client)
    
    #bucket_name = make_bucket(account_id, region, bucket_prefix, s3_client)
    #upload_tools(tool_zip, bucket_name, s3_client)
    target_az = get_target_az(target_id, ec2_client)
    target_subnet = get_target_subnet(target_id, ec2_client)

    instance_type = get_instance_type_of_target(target_id, ec2_client)
    memory_size = get_memory_size_by_instance_type(instance_type, ec2_client)
    work_drive_size = int(memory_size / 1024) * 2 + 1 # 2x memory + 1Gib for tools

    #temp_workstation_id = create_temp_workstation(ec2_client, target_az, role_name, 
    #        work_ami_id, target_subnet)
    #wait_for_workstation_to_start(temp_workstation_id, ec2_client)
    work_drive_id = create_workdrive(target_az, work_drive_size, ec2_client)

    #delete_bucket(bucket_name, s3_resource)
    


if __name__ == "__main__":
    args = parse_cmd_line_args()
    profile = args.profile
    region = args.region
    tool_zip = args.toolzip
    target_id = args.targetid
    role_name = args.role
    work_ami_id = args.workami

    main(profile, region, tool_zip, target_id, role_name, work_ami_id)

