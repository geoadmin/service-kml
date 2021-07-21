import logging

from urllib3.exceptions import HTTPError

from flask import abort

import boto3

from botocore.client import Config
from botocore.exceptions import EndpointConnectionError

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

    def get_file_from_bucket(self, bucket_name, file_id):
        try:
            response = self.s3.get_object(Bucket=bucket_name, Key=file_id)
        except EndpointConnectionError as error:
            logger.exception('Failed to connect to S3: %s', error)
            abort(502, 'Backend file storage connection error, please consult logs')
        return response

    def delete_file_in_bucket(self, bucket_name, file_id):
        try:
            response = self.s3.delete_object(Bucket=bucket_name, Key=file_id)
        except HTTPError as error:
            if error == 400:
                logger.warning("Can not delete file %s. The file is already deleted.", file_id)
            else:
                logger.error("Could not delete the kml %s: %s", file_id, error)
                raise
        except EndpointConnectionError as error:
            logger.exception('Failed to connect to S3: %s', error)
            abort(502, 'Backend file storage connection error, please consult logs')
        return response

    def upload_object_to_bucket(self, file_id, data, bucket_name):
        logger.debug("Uploading file %s to bucket %s.", file_id, bucket_name)
        try:
            response = self.s3.put_object(Body=data, Bucket=bucket_name, Key=file_id)
        except EndpointConnectionError as error:
            logger.exception('Failed to connect to S3: %s', error)
            abort(502, 'Backend file storage connection error, please consult logs')
        return response
