import logging
import boto3
import uuid
import argparse
import sys
import os
import time
from botocore.exceptions import ClientError

logging.basicConfig(level=logging.INFO)

TEMP_INSTANCE_TYPE = "m5.large"


def parse_cmd_line_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--profile', '-p', help="AWS profile", type=str)
    parser.add_argument('--region', '-r', help="AWS region", type=str)
    parser.add_argument('--toolzip', '-t', help="Memory Capture tool zip file", type=str)
    parser.add_argument('--targetid', '-i', help="ID of the target machine.", type=str)
    parser.add_argument('--role', '-l', help="Role to attach to TempWorkstation", type=str)
    parser.add_argument('--workami', '-a', help="AMI to use for TempWorkstation", type=str)
    parser.add_argument('--outputfile', '-o-', help="Output file name", type=str)


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
                InstanceType=TEMP_INSTANCE_TYPE,
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

        waiter = ec2_client.get_waiter('instance_running')
        waiter.wait(InstanceIds=[response['Instances'][0]['InstanceId']])
    except ClientError as e:
        logging.error(e)


    workstation_id = response['Instances'][0]['InstanceId']
    logging.info(workstation_id)
    return workstation_id


def create_workdrive(target_az, work_drive_size, ec2_client):
    logging.info("Creating WorkDrive...")
    response = "" 

    try:
        response = ec2_client.create_volume(
                AvailabilityZone=target_az,
                Size=work_drive_size,
                VolumeType='gp2')

        waiter = ec2_client.get_waiter('volume_available')
        waiter.wait(VolumeIds=[response['VolumeId']])
    except ClientError as e:
        logging.error(e)

    workdrive_id = response['VolumeId']
    logging.info(str(workdrive_id))

    return workdrive_id


def attach_work_drive_to_system(device_name, system_id, drive_id, ec2_client):
    logging.info("Attaching volume to system...")

    try:
        ec2_client.attach_volume(Device=device_name,
                                 InstanceId=system_id,
                                 VolumeId=drive_id)
    except ClientError as e:
        logging.error(e)


def detatch_work_drive_from_system(drive_id, ec2_client):
    logging.info("Detatching volume from system...")

    try:
        ec2_client.detach_volume(VolumeId=drive_id)

        waiter = ec2_client.get_waiter('volume_available')
        waiter.wait(VolumeIds=[drive_id])
    except ClientError as e:
        logging.error(e)


def delete_work_drive(drive_id, ec2_client):
    logging.info("Deleting work drive...")

    try:
        ec2_client.delete_volume(VolumeId=drive_id)
    except ClientError as e:
        logging.error(e)

def terminate_temp_workstation(temp_workstation_id, ec2_client):
    logging.info("Terminating temp workstation...")

    try:
        ec2_client.terminate_instances(InstanceIds=[temp_workstation_id])
    except ClientError as e:
        logging.error(e)


def build_work_drive(temp_workstation_id, tool_zip, bucket_name, ssm_client):
    logging.info("Building work drive...")

    format_raw_drive = 'Get-Disk | Where PartitionStyle -eq "RAW" | Initialize-Disk -PartitionStyle MBR -PassThru | New-Partition -AssignDriveLetter -UseMaximumSize | Format-Volume -FileSystem NTFS -NewFileSystemLabel "Forensic_Tools" -Confirm:$false'


    get_drive_letter = '$toolsDrive = (Get-Volume -FileSystemLabel Forensic_Tools).DriveLetter'

    get_drive_path = '$toolsDrivePath = $toolsDrive + ":\"'

    make_tools_dir = 'New-Item -Path $toolsDrivePath -Name tools -ItemType directory'

    make_tools_path = f'$toolsPath = $toolsDrivePath + "tools\{tool_zip}"'

    copy_tools_from_s3 = f'Read-S3Object -BucketName {bucket_name} -Key {tool_zip} -File $toolsPath'

    unzip_tools = f'Expand-Archive -LiteralPath $toolsPath -DestinationPath $toolsDrivePath + "\\tools"'

    get_disk_number = '$diskNumber = (Get-Partition -DriveLetter $toolsDrive).DiskNumber'

    unmount_drive = 'Set-Disk -Number $diskNumber -IsOffLine $True'

    logging.info(copy_tools_from_s3)

    try:
        response = ssm_client.send_command(
                InstanceIds=[temp_workstation_id],
                DocumentName="AWS-RunPowerShellScript",
                Parameters={'commands': [format_raw_drive,
                                         get_drive_letter,
                                         get_drive_path,
                                         make_tools_dir,
                                         make_tools_path,
                                         copy_tools_from_s3,
                                         unzip_tools,
                                         get_disk_number,
                                         unmount_drive
                                         ],
                            },
                )

        logging.info(response)
        command_id = response['Command']['CommandId']
        waiter = ssm_client.get_waiter('command_executed')
        waiter.wait(CommandId=command_id, InstanceId=temp_workstation_id)
        output = ssm_client.get_command_invocation(
            CommandId=command_id,
            InstanceId=temp_workstation_id
        )
        print(output)
    except ClientError as e:
        logging.error(e)


def capture_memory_image(workstation_id, ssm_client):
    logging.info("Building work drive...")

    take_drive_online = 'Get-Disk | Where-Object IsOffline -Eq $True | Set-Disk -IsOffline $False'

    get_drive_letter = '$toolsDrive = (Get-Volume -FileSystemLabel Forensic_Tools).DriveLetter'

    get_drive_path = '$toolsDrivePath = $toolsDrive + ":\"'

    dump_memory = ''

    get_disk_number = '$diskNumber = (Get-Partition -DriveLetter $toolsDrive).DiskNumber'

    unmount_drive = 'Set-Disk -Number $diskNumber -IsOffLine $True'

    logging.info(copy_tools_from_s3)

    try:
        response = ssm_client.send_command(
                InstanceIds=[temp_workstation_id],
                DocumentName="AWS-RunPowerShellScript",
                Parameters={'commands': [take_drive_online,
                                         get_drive_letter,
                                         get_drive_path,
                                         dump_memory,
                                         get_disk_number,
                                         unmount_drive
                                         ],
                            },
                )

        logging.info(response)
        command_id = response['Command']['CommandId']
        waiter = ssm_client.get_waiter('command_executed')
        waiter.wait(CommandId=command_id, InstanceId=temp_workstation_id)
        output = ssm_client.get_command_invocation(
            CommandId=command_id,
            InstanceId=temp_workstation_id
        )
        print(output)
    except ClientError as e:
        logging.error(e)


def wait_for_ssm_agent(instance_id, ssm_client):
    result = ""
    while True:
        try:
            logging.info("Waiting for SSM agent to activate...")
            result = ssm_client.describe_instance_information(
                    InstanceInformationFilterList=[
                        {
                            'key': 'InstanceIds',
                            'valueSet': [instance_id]
                        }])

            if result['InstanceInformationList']:
                break
            else:
                time.sleep(10)
        except ClientError as e:
            logging.error(e)



def main(profile, region, tool_zip, target_id, role_name, work_ami_id, output_file):
    bucket_prefix = "mem-capture"

    session = boto3.Session(region_name=region, profile_name=profile)
    sts_client = session.client('sts')
    s3_client = session.client('s3')
    s3_resource = session.resource('s3')
    ec2_client = session.client('ec2')
    ssm_client = session.client('ssm')
    account_id = get_account_id(sts_client)
    
    bucket_name = make_bucket(account_id, region, bucket_prefix, s3_client)
    upload_tools(tool_zip, bucket_name, s3_client)
    target_az = get_target_az(target_id, ec2_client)
    target_subnet = get_target_subnet(target_id, ec2_client)

    instance_type = get_instance_type_of_target(target_id, ec2_client)
    memory_size = get_memory_size_by_instance_type(instance_type, ec2_client)
    work_drive_size = int(memory_size / 1024) * 2 + 1 # 2x memory + 1Gib for tools

    temp_workstation_id = create_temp_workstation(ec2_client, target_az, role_name, 
            work_ami_id, target_subnet)
    work_drive_id = create_workdrive(target_az, work_drive_size, ec2_client)
    attach_work_drive_to_system("/dev/sdh", temp_workstation_id, work_drive_id, ec2_client)
    wait_for_ssm_agent(temp_workstation_id, ssm_client)
    build_work_drive(temp_workstation_id, tool_zip, bucket_name, ssm_client)
    detatch_work_drive_from_system(work_drive_id, ec2_client)
    attach_work_drive_to_system("/dev/sdx", target_id, work_drive_id, ec2_client)
    #capture_memory_image(target_id, ec2_client)


    #delete_work_drive(work_drive_id, ec2_client)
    terminate_temp_workstation(temp_workstation_id, ec2_client)
    delete_bucket(bucket_name, s3_resource)
    


if __name__ == "__main__":
    args = parse_cmd_line_args()
    profile = args.profile
    region = args.region
    tool_zip = os.path.basename(args.toolzip)
    logging.info(tool_zip)
    target_id = args.targetid
    role_name = args.role
    work_ami_id = args.workami
    output_file = args.outputfile

    main(profile, region, tool_zip, target_id, role_name, work_ami_id, output_file)

