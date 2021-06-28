import unittest

import boto3

from app import app
from app.settings import AWS_DB_ENDPOINT_URL
from app.settings import AWS_DB_REGION_NAME
from app.settings import AWS_DB_TABLE_NAME
from app.settings import AWS_S3_BUCKET_NAME
from app.settings import AWS_S3_REGION_NAME
from app.version import APP_VERSION


class CheckerTests(unittest.TestCase):

    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True

    def test_checker(self):
        response = self.app.get("/checker")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content_type, "application/json")
        self.assertEqual(response.json, {"message": "OK", "success": True, "version": APP_VERSION})


class TestPostEndpoint(unittest.TestCase):

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
        s3bucket = boto3.resource('s3', region_name=AWS_S3_REGION_NAME)
        location = {'LocationConstraint': AWS_S3_REGION_NAME}
        s3bucket.create_bucket(Bucket=AWS_S3_BUCKET_NAME, CreateBucketConfiguration=location)
        dynamodb = boto3.resource(
            'dynamodb', region_name=AWS_DB_REGION_NAME, endpoint_url=AWS_DB_ENDPOINT_URL
        )
        dynamodb.create_table(
            TableName=AWS_DB_TABLE_NAME,
            AttributeDefinitions=[
                {
                    'AttributeName': 'adminId', 'AttributeType': 'S'
                },
            ],
            KeySchema=[
                {
                    'AttributeName': 'adminId', 'KeyType': 'HASH'
                },
            ]
        )

    def test_kml_post(self):
        response = self.app.post(
            "/kml", data=self.kml_string, content_type="application/vnd.google-earth.kml+xml"
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.content_type, "application/json")
