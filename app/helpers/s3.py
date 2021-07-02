import logging

import boto3

from botocore.client import Config

logger = logging.getLogger(__name__)


def get_s3_client(region, endpoint_url):
    '''Return a S3 client
    NOTE: Authentication is done via the following environment variables:
        - AWS_ACCESS_KEY_ID
        - AWS_SECRET_ACCESS_KEY
    '''
    return boto3.client(
        's3',
        endpoint_url=endpoint_url,
        region_name=region,
        config=Config(signature_version='s3v4')
    )


class S3FileHandling:

    def __init__(self, region, endpoint_url):
        self.s3 = get_s3_client(region, endpoint_url)  # pylint: disable=invalid-name

    def get_file_from_bucket(self, bucket_name, file_name):
        response = self.s3.get_object(Bucket=bucket_name, Key=file_name)
        return response

    def delete_file_in_bucket(self, bucket_name, file_name):
        return self.s3.delete_object(Bucket=bucket_name, Key=file_name)

    def upload_object_to_bucket(self, file_id, data, bucket_name):
        logger.debug("Uploading file %s to bucket %s.", file_id, bucket_name)
        return self.s3.put_object(Body=data, Bucket=bucket_name, Key=file_id)
