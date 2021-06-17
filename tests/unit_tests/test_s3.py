# pylint: disable=wildcard-import,unused-wildcard-import,wrong-import-position,wrong-import-order
from moto import mock_s3
s3mock = mock_s3()
s3mock.start()

#from config.settings import *

AWS_ACCESS_KEY_ID = 'my-key'
AWS_SECRET_ACCESS_KEY = 'my-key'
AWS_DEFAULT_ACL = 'public-read'
AWS_S3_REGION_NAME = 'us-east-1'
AWS_S3_ENDPOINT_URL = None
AWS_S3_CUSTOM_DOMAIN = 'testserver'

MY_PREFIX = "mock_folder"
AWS_BUCKET_NAME = "my_bucket"

import os
import unittest

from app import app
from app.version import APP_VERSION
from tests.unit_tests.utils import mock_s3_asset_file

import boto3
import botocore
from moto import mock_s3


from app.helpers.s3 import S3FileHandling
from tests.unit_tests import settings_test
import uuid
import base64

MY_PREFIX = "mock_folder"
MY_BUCKET = "my_bucket"

#@mock_s3
class TestUploadObjectToBucket(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True
        self.client = boto3.client(
            "s3",
            region_name=AWS_S3_REGION_NAME,
            aws_access_key_id=AWS_ACCESS_KEY_ID,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
            )
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

        try:
            self.s3 = boto3.resource(
                "s3",
                region_name=AWS_S3_REGION_NAME,
                aws_access_key_id=AWS_ACCESS_KEY_ID,
                aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
                )
            self.s3.meta.client.head_bucket(Bucket=MY_BUCKET)
        except botocore.exceptions.ClientError:
            pass
        else:
            err = "{bucket} should not exist.".format(bucket=MY_BUCKET)
            raise EnvironmentError(err)

        self.client.create_bucket(Bucket=MY_BUCKET)


    def tearDown(self):
        self.s3 = boto3.resource(
            "s3",
            region_name=AWS_S3_REGION_NAME,
            aws_access_key_id=AWS_ACCESS_KEY_ID,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
            )
        bucket = self.s3.Bucket(MY_BUCKET)
        for key in bucket.objects.all():
            key.delete()
        bucket.delete()

    @mock_s3_asset_file
    def test_kml_post(self):
        response = self.app.post(
            "/kml", data=self.kml_string, content_type="application/vnd.google-earth.kml+xml"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content_type, "application/json")
        self.assertEqual(response.json, {"message": "OK", "success": True, "version": APP_VERSION})

        # kml_id = base64.urlsafe_b64encode(uuid.uuid4().bytes).decode('utf8').replace('=', '')
        # self.s3.Bucket(MY_BUCKET).put_object(Key=kml_id, Body=self.kml_string)