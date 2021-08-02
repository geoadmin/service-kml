import logging
import unittest

from flask import abort

import boto3

from botocore.exceptions import ClientError
from botocore.exceptions import EndpointConnectionError

from app import app
from app.settings import AWS_DB_ENDPOINT_URL
from app.settings import AWS_DB_REGION_NAME
from app.settings import AWS_DB_TABLE_NAME
from app.settings import AWS_S3_BUCKET_NAME
from app.settings import AWS_S3_REGION_NAME

logger = logging.getLogger(__name__)


class BaseRouteTestCase(unittest.TestCase):

    @classmethod
    def get_kml_dict(cls):
        '''Read the 3 kml strings from the 3 sample files

        An example for a valid, an invalid and an updated kml string is provided in 3 sample files
        in the ./tests/samples dir. These 3 files are stored in the kml_dict dictionary so they
        can be easily used in unit tests.

        Returns:
            kml_dict: dictionary containing a valid, an invalid and an updated kml string.'''
        kml_dict = {}
        for kml_sample in ["valid", "invalid", "updated"]:
            with open(f'./tests/samples/{kml_sample}-kml.xml', 'r') as file:
                kml_string = file.read()
            kml_dict[kml_sample] = kml_string

        return kml_dict

    def create_test_kml(self):
        '''Method that creates a mocked s3 bucket for unit testing

        An initial kml is created via a POST request and stored in the s3 bucket as well as in the
        dynamo db. This initial kml will be used in unit tests, e.g. when a PUT is tested, it can
        be applied to this initial kml, that is guaranteed to already exist.

        Returns:
            response.json: json containing the response of the POST request.'''
        response = self.app.post(
            "/kml",
            data=self.kml_dict["valid"],
            content_type="application/vnd.google-earth.kml+xml",
            headers=self.origin_headers["allowed"]
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.content_type, "application/json")
        self.compare_kml_contents(response, self.kml_dict["valid"])
        return response.json

    @classmethod
    def create_bucket(cls):
        try:
            s3bucket = boto3.resource('s3', region_name=AWS_S3_REGION_NAME)
            location = {'LocationConstraint': AWS_S3_REGION_NAME}
            s3bucket.create_bucket(Bucket=AWS_S3_BUCKET_NAME, CreateBucketConfiguration=location)
        except s3bucket.meta.client.exceptions.BucketAlreadyExists as err:
            logger.debug(
                "Bucket %s already exists but should not.", err.response['Error']['BucketName']
            )
            raise err
        return s3bucket

    @classmethod
    def create_dynamodb(cls):
        '''Method that creates a mocked DynamoDB for unit testing

        Returns:
            dynamodb: dynamodb resource'''
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
        return dynamodb

    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True
        self.origin_headers = {
            "allowed": {
                "Origin": "map.geo.admin.ch"
            }, "bad": {
                "Origin": "big-bad-wolf.com"
            }
        }
        self.kml_dict = self.get_kml_dict()
        self.s3bucket = self.create_bucket()
        self.dynamodb = self.create_dynamodb()
        self.sample_kml = self.create_test_kml()

    def compare_kml_contents(self, response, expected_kml):
        # pylint: disable=duplicate-code
        '''Check content of kml on s3 bucket

        A request has created/updated a kml on s3. The corresponding response is passed to this
        method. From this the admin_id is extracted and used to retrieve the corresponding file_id
        from the DynamoDB. With this file_id the content of the kml from s3 is fetched and
        compared to the expected kml_string.

        Args:
            response: Response object
                Response of the request, which created/updated a kml on s3.
            expected_kml: string
                String containing the expected content of the kml file.
        '''
        kml_admin_id = response.json['id']
        item = self.dynamodb.Table(AWS_DB_TABLE_NAME).get_item(Key={
            'admin_id': kml_admin_id
        }).get('Item', None)
        if item is None:
            logger.error("Could not find the following kml id in the database: %s", kml_admin_id)
            abort(404, f"Could not find {kml_admin_id} within the database.")

        file_id = item["file_id"]

        try:
            obj = self.s3bucket.meta.client.get_object(Bucket=AWS_S3_BUCKET_NAME, Key=file_id)
        except EndpointConnectionError as error:
            logger.exception('Failed to connect to S3: %s', error)
            abort(502, 'Backend file storage connection error, please consult logs')
        except ClientError as error:
            if error.response['Error']['Code'] == "NoSuchKey":
                logger.exception('Object with the given key %s not found in s3 bucket.', file_id)
                abort(404, f'Object with the given key {file_id} not found in s3 bucket.')
        # pylint: enable=duplicate-code
        body = obj['Body'].read()
        self.assertEqual(body.decode("utf-8"), expected_kml)

    def tearDown(self):
        for key in self.s3bucket.Bucket(AWS_S3_BUCKET_NAME).objects.all():
            key.delete()
        self.s3bucket.Bucket(AWS_S3_BUCKET_NAME).delete()
        self.dynamodb.Table(AWS_DB_TABLE_NAME).delete()
