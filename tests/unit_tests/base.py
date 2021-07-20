import logging
import unittest

import boto3

from app import app
from app.settings import AWS_DB_ENDPOINT_URL
from app.settings import AWS_DB_REGION_NAME
from app.settings import AWS_DB_TABLE_NAME
from app.settings import AWS_S3_BUCKET_NAME
from app.settings import AWS_S3_REGION_NAME

logger = logging.getLogger(__name__)


class BaseRouteTestCase(unittest.TestCase):

    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True
        self.kml_string = """<root xmlns    = "https://www.exampel.ch/"
        xmlns:py = "https://www.exampel.ch/">
        <py:elem1 />
        <elem2 xmlns="" />
        </root>"""

        self.kml_invalid_string = """Hi <root xmlns    = "https://www.exampel.ch/"
        xmlns:py = "https://www.exampel.ch/">
        <py:elem1 />
        <elem2 xmlns="" />
        </root>"""

        self.new_kml_string = """<root xmlns    = "https://www.update.de/"
        xmlns:py = "https://www.update.de/">
        <py:elem1 />
        <elem2 xmlns="" />
        </root>"""

        try:
            s3bucket = boto3.resource('s3', region_name=AWS_S3_REGION_NAME)
            location = {'LocationConstraint': AWS_S3_REGION_NAME}
            s3bucket.create_bucket(Bucket=AWS_S3_BUCKET_NAME, CreateBucketConfiguration=location)
        except s3bucket.meta.client.exceptions.BucketAlreadyExists as err:
            logger.debug(
                "Bucket %s already exists but should not.", err.response['Error']['BucketName']
            )
            raise err

        try:
            dynamodb = boto3.resource(
                'dynamodb', region_name=AWS_DB_REGION_NAME, endpoint_url=AWS_DB_ENDPOINT_URL
            )
            dynamodb.create_table(
                TableName=AWS_DB_TABLE_NAME,
                AttributeDefinitions=[
                    {
                        'AttributeName': 'admin_id', 'AttributeType': 'S'
                    },
                ],
                KeySchema=[
                    {
                        'AttributeName': 'admin_id', 'KeyType': 'HASH'
                    },
                ]
            )
        except dynamodb.meta.client.exceptions.ResourceInUseException as err:
            logger.debug("Table %s already exists but should not.", AWS_DB_TABLE_NAME)
            raise err

    def tearDown(self):
        s3bucket = boto3.resource('s3', region_name=AWS_S3_REGION_NAME).Bucket(AWS_S3_BUCKET_NAME)
        for key in s3bucket.objects.all():
            key.delete()
        s3bucket.delete()
        dynamodb = boto3.resource(
            'dynamodb', region_name=AWS_DB_REGION_NAME, endpoint_url=AWS_DB_ENDPOINT_URL
        )
        dynamodb.Table(AWS_DB_TABLE_NAME).delete()
