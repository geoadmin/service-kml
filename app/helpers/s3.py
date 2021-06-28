import logging

from app.helpers.utils import get_s3_client

logger = logging.getLogger(__name__)


class S3FileHandling:

    def __init__(self, region, endpoint_url):
        self.s3 = get_s3_client(region, endpoint_url)  # pylint: disable=invalid-name

    def get_file_from_bucket(self, bucket_name, file_name):
        response = self.s3.get_object(Bucket=bucket_name, Key=file_name)
        return response

    def delete_file_in_bucket(self, bucket_name, file_name):
        return self.s3.delete_object(Bucket=bucket_name, Key=file_name)

    def upload_object_to_bucket(self, file_id, data, bucket_name):
        return self.s3.put_object(Body=data, Bucket=bucket_name, Key=file_id)
