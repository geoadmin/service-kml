import os
import unittest

import boto3
from moto import mock_s3

from app import app
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

        # set the ENV variables to unit test values:
        os.environ['AWS_ACCESS_KEY_ID'] = 'my-key'
        os.environ['AWS_SECRET_ACCESS_KEY'] = 'my-key'
        os.environ['AWS_DEFAULT_ACL'] = 'public-read'
        os.environ['AWS_S3_REGION_NAME'] = 'us-east-1'
        del os.environ['AWS_S3_ENDPOINT_URL']
        os.environ['AWS_S3_CUSTOM_DOMAIN'] = 'testserver'
        os.environ['AWS_S3_BUCKET_NAME'] = 'my_bucket'

        s3mock = mock_s3()
        s3mock.start()
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

    @mock_s3
    def test_kml_post(self):
        conn = boto3.resource('s3', region_name=os.getenv('AWS_S3_REGION_NAME'))
        conn.create_bucket(Bucket=os.getenv('AWS_S3_BUCKET_NAME'))
        response = self.app.post(
            "/kml", data=self.kml_string, content_type="application/vnd.google-earth.kml+xml"
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.content_type, "application/json")
