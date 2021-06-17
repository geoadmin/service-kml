import functools
import hashlib
import logging
import time
from io import BytesIO

import botocore
from moto import mock_s3

from app.helpers.utils import get_s3_client
from app.helpers.utils import get_s3_resource

from tests.unit_tests import settings_test


logger = logging.getLogger(__name__)


class S3TestMixin():
    '''Check if object on s3 exists

    This TestCase mixin provides helpers to check whether an
    object exists at a specific location on s3 or not
    '''

    def assertS3ObjectExists(self, path):  # pylint: disable=invalid-name
        s3 = get_s3_resource()

        try:
            s3.Object(settings_test.AWS_BUCKET_NAME, path).load()
        except botocore.exceptions.ClientError as error:
            if error.response['Error']['Code'] == "404":
                # Object Was Not Found
                self.fail("the object was not found at the expected location")
            self.fail(f"object lookup failed for unexpected reason: {error}")

    def assertS3ObjectNotExists(self, path):  # pylint: disable=invalid-name
        s3 = get_s3_resource()
        with self.assertRaises(
            botocore.exceptions.ClientError, msg=f'Object {path} found on S3'
        ) as exception_context:
            s3.Object(settings_test.AWS_BUCKET_NAME, path).load()
        error = exception_context.exception
        self.assertEqual(error.response['Error']['Code'], "404")


def mock_s3_bucket():
    '''Mock an S3 bucket

    This functions check if a S3 bucket exists and create it if not. This
    can be used to mock the bucket for unittest.
    '''
    start = time.time()
    s3 = get_s3_resource()
    try:
        s3.meta.client.head_bucket(Bucket=settings_test.AWS_BUCKET_NAME)
    except botocore.exceptions.ClientError as error:
        # If a client error is thrown, then check that it was a 404 error.
        # If it was a 404 error, then the bucket does not exist.
        error_code = error.response['Error']['Code']
        if error_code == '404':
            # We need to create the bucket since this is all in Moto's 'virtual' AWS account
            s3.create_bucket(
                Bucket=settings_test.AWS_BUCKET_NAME,
                CreateBucketConfiguration={'LocationConstraint': settings_test.AWS_S3_REGION_NAME}
            )
            logger.debug('Mock S3 bucket created in %fs', time.time() - start)
    logger.debug('Mock S3 bucket in %fs', time.time() - start)


def mock_s3_asset_file(test_function):
    '''Mock S3 Asset file decorator

    This decorator can be used to mock Asset file on S3. This can be used for unittest that want
    to create/update Assets.
    '''

    @mock_s3
    @functools.wraps(test_function)
    def wrapper(*args, **kwargs):
        mock_s3_bucket()
        test_function(*args, **kwargs)

    return wrapper


def upload_file_on_s3(file_path, file, params=None):
    '''Upload a file on S3 using boto3

    Args:
        file_path: string
            file path on S3 (key)
        file: bytes | BytesIO | File
            file to upload
        params: None | dict
            parameters to path to boto3.upload_fileobj() as ExtraArgs
    '''
    s3 = get_s3_resource()
    obj = s3.Object(settings_test.AWS_BUCKET_NAME, file_path)
    if isinstance(file, bytes):
        file = BytesIO(file)
    if params is not None:
        extra_args = params
    else:
        extra_args = {
            'Metadata': {
                'sha256': hashlib.sha256(file.read()).hexdigest()
            },
            "CacheControl": f"max-age={settings_test.STORAGE_ASSETS_CACHE_SECONDS}, public"
        }
    obj.upload_fileobj(file, ExtraArgs=extra_args)


# def mock_requests_asset_file(mocker, asset, **kwargs):
#     '''Mock the HEAD request to the Asset file

#     When creating/updating an Asset, the serializer verify if the file exists by doing a HEAD
#     request to the File on S3. This function mock this request.

#     Args:
#         mocker:
#             python requests mocker.
#         asset:
#             Asset sample used to create/modify an asset
#         **kwargs:
#             Arguments to pass to the mocker.
#     '''
#     headers = kwargs.pop('headers', {})

#     if 'exc' not in kwargs:
#         kwargs['headers'] = headers
#     mocker.head(
#         f'http://{settings.AWS_S3_CUSTOM_DOMAIN}/{asset["item"].collection.name}/{asset["item"].name}/{asset["name"]}',
#         **kwargs
#     )


class disableLogger:  # pylint: disable=invalid-name
    """Disable temporarily a logger with a with statement

    Args:
        logger_name: str | None
            logger name to disable, by default use the root logger (None)

    Example:
        with disableLogger('stac_api.apps'):
            # the stac_api.apps logger is totally disable within the with statement
            logger = logging.getLogger('stac_api.apps')
            logger.critical('This log will not be printed anywhere')
    """

    def __init__(self, logger_name=None):
        if logger_name:
            self.logger = logging.getLogger(logger_name)
        else:
            self.logger = logging.getLogger()

    def __enter__(self):
        self.logger.disabled = True

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.logger.disabled = False
