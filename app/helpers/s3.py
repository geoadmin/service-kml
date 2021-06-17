import logging

import boto3
from botocore.client import Config

from app.helpers.utils import get_s3_client

from app import settings

logger = logging.getLogger(__name__)


class S3FileHandling:

    def __init__(self):
        self.s3 = get_s3_client()

    def get_file_from_bucket(self, bucket_name, file_name):
        response = self.s3.get_object(Bucket=bucket_name, Key=file_name)
        return response


    def delete_file_in_bucket(self, bucket_name, file_name):
        return self.s3.delete_object(Bucket=bucket_name,Key=file_name)


    def upload_object_to_bucket(self, file_id, data, bucket_name=settings.AWS_S3_BUCKET_NAME):
        return self.s3.put_object(
            Body=data,
            Bucket=bucket_name,
            Key=file_id
        )
