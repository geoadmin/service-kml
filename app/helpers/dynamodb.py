import logging

from flask import abort
from flask import g

import boto3

from botocore.client import Config
from botocore.exceptions import EndpointConnectionError

from app.settings import AWS_DB_ENDPOINT_URL
from app.settings import AWS_DB_REGION_NAME
from app.settings import AWS_DB_TABLE_NAME
from app.settings import AWS_S3_BUCKET_NAME

logger = logging.getLogger(__name__)


def get_dynamodb_resource(region, endpoint_url):
    return boto3.resource('dynamodb', endpoint_url=endpoint_url, config=Config(region_name=region))


def get_db():
    if 'db' not in g:
        g.db = DynamoDBFilesHandler(
            table_name=AWS_DB_TABLE_NAME,
            bucket_name=AWS_S3_BUCKET_NAME,
            table_region=AWS_DB_REGION_NAME,
            endpoint_url=AWS_DB_ENDPOINT_URL
        )
    return g.db


class DynamoDBFilesHandler:

    def __init__(self, table_name, bucket_name, endpoint_url, table_region):
        self.dynamodb = get_dynamodb_resource(table_region, endpoint_url)
        self.table = self.dynamodb.Table(table_name)
        self.bucket_name = bucket_name
        self.endpoint = endpoint_url

    def save_item(self, kml_admin_id, file_id, timestamp):
        try:
            self.table.put_item(
                Item={
                    'admin_id': kml_admin_id,
                    'file_id': file_id,
                    'created': timestamp,
                    'updated': timestamp,
                    'deleted': 'False',
                    'bucket': self.bucket_name
                }
            )
        except EndpointConnectionError as error:
            logger.exception('Failed to connect to DynamoDB: %s', error)
            abort(502, 'Backend DB connection error, please consult logs')

    def get_item(self, kml_admin_id):
        try:
            item = self.table.get_item(Key={'admin_id': kml_admin_id}).get('Item', None)
        except EndpointConnectionError as error:
            logger.exception('Failed to connect to DynamoDB: %s', error)
            abort(502, 'Backend DB connection error, please consult logs')

        if item is None:
            logger.error("Could not find the following kml id in the database: %s", kml_admin_id)
            abort(404, f"Could not find {kml_admin_id} within the database.")

        return item

    def update_item_timestamp(self, kml_admin_id, timestamp):
        try:
            self.table.update_item(
                Key={'admin_id': kml_admin_id},
                AttributeUpdates={'updated': {
                    'Value': timestamp, 'Action': 'PUT'
                }}
            )
        except EndpointConnectionError as error:
            logger.exception('Failed to connect to DynamoDB: %s', error)
            abort(502, 'Backend DB connection error, please consult logs')

    def delete_item(self, kml_admin_id):
        try:
            self.table.delete_item(Key={'admin_id': kml_admin_id})
        except EndpointConnectionError as error:
            logger.exception('Failed to connect to DynamoDB: %s', error)
            abort(502, 'Backend DB connection error, please consult logs')
