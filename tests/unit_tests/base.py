import io
import logging
import os
import re
import unittest

from flask.helpers import url_for

import boto3

from botocore.exceptions import ClientError
from botocore.exceptions import EndpointConnectionError

from app import app
from app.helpers.utils import decompress_if_gzipped
from app.helpers.utils import gzip_string
from app.settings import ALLOWED_DOMAINS_PATTERN
from app.settings import AWS_DB_ENDPOINT_URL
from app.settings import AWS_DB_REGION_NAME
from app.settings import AWS_DB_TABLE_NAME
from app.settings import AWS_S3_BUCKET_NAME
from app.settings import AWS_S3_REGION_NAME
from app.settings import KML_FILE_CONTENT_ENCODING
from app.settings import KML_FILE_CONTENT_TYPE

logger = logging.getLogger(__name__)


def create_bucket():
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


def create_dynamodb():
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
                    'AttributeName': 'kml_id', 'AttributeType': 'S'
                },
                {
                    'AttributeName': 'admin_id', 'AttributeType': 'S'
                },
            ],
            KeySchema=[
                {
                    'AttributeName': 'kml_id', 'KeyType': 'HASH'
                },
            ],
            GlobalSecondaryIndexes=[
                {
                    "IndexName": "admin_id-index",
                    "KeySchema": [{
                        "AttributeName": "admin_id", "KeyType": "HASH"
                    }],
                    "Projection": {
                        "ProjectionType": "ALL"
                    },
                    "ProvisionedThroughput": {
                        "ReadCapacityUnits": 1, "WriteCapacityUnits": 1
                    }
                }
            ],
            ProvisionedThroughput={
                "ReadCapacityUnits": 1, "WriteCapacityUnits": 1
            },
        )
    except dynamodb.meta.client.exceptions.ResourceInUseException as err:
        logger.debug("Table %s already exists but should not.", AWS_DB_TABLE_NAME)
        raise err
    return dynamodb


def prepare_kml_payload(
    kml_data=None, admin_id=None, kml_file=None, content_type=KML_FILE_CONTENT_TYPE
):
    author = 'unittest'
    if kml_file and kml_data is None:
        with open(f'./tests/samples/{kml_file}', 'rb') as file:
            kml_data = file.read()
    if admin_id and kml_data:
        return dict(
            admin_id=admin_id, kml=(io.BytesIO(kml_data), 'kml.xml', content_type), author=author
        )
    if kml_data:
        return dict(kml=(io.BytesIO(kml_data), 'kml.xml', content_type), author=author)
    if admin_id:
        return dict(admin_id=admin_id)
    raise ValueError('No admin_id and no kml_string given')


class BaseRouteTestCase(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.context = app.test_request_context()
        cls.context.push()
        cls.app = app.test_client()
        cls.app.testing = True
        cls.origin_headers = {
            "allowed": {
                "Origin": "map.geo.admin.ch"
            }, "bad": {
                "Origin": "big-bad-wolf.com"
            }
        }
        cls.s3bucket = create_bucket()
        cls.dynamodb = create_dynamodb()

    @classmethod
    def tearDownClass(cls):
        for key in cls.s3bucket.Bucket(AWS_S3_BUCKET_NAME).objects.all():
            key.delete()
        cls.s3bucket.Bucket(AWS_S3_BUCKET_NAME).delete()
        cls.dynamodb.Table(AWS_DB_TABLE_NAME).delete()

    def setUp(self):
        super().setUp()
        self.kmls = []

    def tearDown(self):
        super().tearDown()
        for kml in self.kmls:
            self.delete_test_kml(kml['id'], kml['admin_id'])

    def assertCors(self, response, expected_allowed_methods, check_origin=True):  # pylint: disable=invalid-name
        if check_origin:
            self.assertIn('Access-Control-Allow-Origin', response.headers)
            self.assertTrue(
                re.match(ALLOWED_DOMAINS_PATTERN, response.headers['Access-Control-Allow-Origin'])
            )
        self.assertIn('Access-Control-Allow-Methods', response.headers)
        self.assertListEqual(
            sorted(expected_allowed_methods),
            sorted(
                map(
                    lambda m: m.strip(),
                    response.headers['Access-Control-Allow-Methods'].split(',')
                )
            )
        )
        self.assertIn('Access-Control-Allow-Headers', response.headers)
        self.assertEqual(response.headers['Access-Control-Allow-Headers'], '*')

    def create_test_kml(self, file_name):
        response = self.app.post(
            url_for('create_kml'),
            data=prepare_kml_payload(kml_file=file_name),
            content_type="multipart/form-data",
            headers=self.origin_headers["allowed"]
        )
        self.assertEqual(response.status_code, 201, msg="Failed to create initial kml")
        metadata = response.json
        self.assertIn('id', metadata)
        self.assertIn('admin_id', metadata)
        self.kmls.append({'id': metadata['id'], 'admin_id': metadata['admin_id']})
        return response

    def delete_test_kml(self, kml_id, admin_id):
        response = self.app.delete(
            url_for('delete_kml', kml_id=kml_id),
            data=prepare_kml_payload(admin_id=admin_id),
            content_type="multipart/form-data",
            headers=self.origin_headers["allowed"]
        )
        return response

    def assertKml(self, response, expected_kml_file):
        '''Check content of kml on s3 bucket and kml DB entry in DynamoDB.

        A request has created/updated a kml on s3. The corresponding response is passed to this
        method. From this the kml_id is extracted and used to retrieve the corresponding item
        from the DynamoDB. With this kml_id the content of the kml from s3 is fetched and
        compared to the expected kml_string.

        Args:
            response: Response object
                Response of the request, which created/updated a kml on s3.
            expected_kml_file: string
                Original kml file name.
        '''
        expected_kml_path = f'./tests/samples/{expected_kml_file}'
        # read the expected kml file
        with open(expected_kml_path, 'rb') as fd:
            expected_kml = decompress_if_gzipped(fd).decode('utf-8')
        kml_id = response.json['id']
        item = self.dynamodb.Table(AWS_DB_TABLE_NAME).get_item(Key={
            'kml_id': kml_id
        }).get('Item', None)
        if item is None:
            self.fail(f"Could not find the following kml id in the database: {kml_id}")

        self.assertIn('length', item)
        expected_kml_size = os.path.getsize(expected_kml_path)
        if expected_kml_file.endswith('.xml'):
            # original file is not compressed get the compressed size
            expected_kml_size = len(gzip_string(expected_kml))
        self.assertEqual(int(item['length']), expected_kml_size)
        self.assertIn('encoding', item)
        self.assertEqual(item['encoding'], KML_FILE_CONTENT_ENCODING)
        self.assertIn('content_type', item)
        self.assertEqual(item['content_type'], KML_FILE_CONTENT_TYPE)
        self.assertEqual(item['author'], 'unittest')

        try:
            obj = self.s3bucket.meta.client.get_object(
                Bucket=AWS_S3_BUCKET_NAME, Key=item['file_key']
            )
        except EndpointConnectionError as error:
            self.fail(f'Failed to connect to S3: {error}')
        except ClientError as error:
            if error.response['Error']['Code'] == "NoSuchKey":
                self.fail(f'Object with the given key {kml_id} not found in s3 bucket.')
            else:
                self.fail(f'S3 client error: {error}')

        body = decompress_if_gzipped((obj['Body']))
        self.assertEqual(body.decode('utf-8'), expected_kml)

    def get_s3_object(self, file_key):
        try:
            obj = self.s3bucket.meta.client.get_object(Bucket=AWS_S3_BUCKET_NAME, Key=file_key)
        except EndpointConnectionError as error:
            self.fail(f'Failed to connect to S3: {error}')
        except ClientError as error:
            if error.response['Error']['Code'] == "NoSuchKey":
                obj = None
            else:
                self.fail(f'S3 client error: {error}')
        return obj
