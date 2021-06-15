import logging

import boto3
from botocore.client import Config

from app import settings

logger = logging.getLogger(__name__)


def get_s3_client():
    '''Return a S3 client
    NOTE: Authentication is done via the following environment variables:
        - AWS_ACCESS_KEY_ID
        - AWS_SECRET_ACCESS_KEY
    '''
    return boto3.client(
        's3',
        endpoint_url=settings.AWS_S3_ENDPOINT_URL,
        region_name=settings.AWS_S3_REGION_NAME,
        config=Config(signature_version='s3')
    )


'''
S3 client used by the async task.
'''
s3_client = get_s3_client()


def put_s3_img_async(kml_path, content, headers):
    task_logger.info('Celery task for caching %s', kml_path)
    try:
        s3_client.put_object(
            Bucket=settings.AWS_S3_BUCKET_NAME,
            Body=content,
            Key=kml_path,
            CacheControl=headers.get('Cache-Control', settings.DEFAULT_CACHE),
            ContentLength=len(content),
            ContentType=headers.get('Content-Type', '')
        )
    except BaseException as error:  # in service stac nachschauen was für exeption error
        task_logger.critical(
            'Celery task for caching %s failed: %s', kml_path, error, exc_info=True
        )
        raise
