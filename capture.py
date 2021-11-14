import logging
import boto3
import uuid
import argparse
import sys
import os
from botocore.exceptions import ClientError

parser = argparse.ArgumentParser()
parser.add_argument('--profile', '-p', help="AWS profile", type=str)
parser.add_argument('--region', '-r', help="AWS region", type=str)
parser.add_argument('--toolzip', '-t', help="Memory Capture tool zip file",
        type=str)

args = parser.parse_args()
profile = args.profile
region = args.region
tool_zip = args.toolzip

bucket_prefix = "mem-capture"

session = boto3.Session(region_name=region, profile_name=profile)
sts_client = session.client('sts')
s3_client = session.client('s3')
s3_resource = session.resource('s3')

def get_account():
    response = sts_client.get_caller_identity()
    return response.get('Account')


def make_bucket():
    account_id = get_account()
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
    return bucket_name

def delete_bucket(bucket_name):
    try:
        bucket = s3_resource.Bucket(bucket_name)
        bucket.objects.all().delete()
        bucket.delete()
    except ClientError as e:
        logging.error(e)




def main():
    bucket_name = make_bucket()


    #delete_bucket(bucket_name)
    


if __name__ == "__main__":
    main()

