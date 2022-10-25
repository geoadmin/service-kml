import logging

from flask import abort
from flask import g

from boto3 import resource
from boto3.dynamodb.conditions import Key

from botocore.client import Config
from botocore.exceptions import EndpointConnectionError

from app.settings import AWS_DB_ENDPOINT_URL
from app.settings import AWS_DB_REGION_NAME
from app.settings import AWS_DB_TABLE_NAME
from app.settings import AWS_S3_BUCKET_NAME
from app.settings import KML_FILE_CONTENT_ENCODING
from app.settings import KML_FILE_CONTENT_TYPE

logger = logging.getLogger(__name__)


def get_dynamodb_resource(region, endpoint_url):
    return resource('dynamodb', endpoint_url=endpoint_url, config=Config(region_name=region))


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

    def save_item(
        self, kml_id, kml_admin_id, file_key, file_length, timestamp, author, author_version, empty
    ):
        logger.debug('Saving dynamodb item with primary key %s', kml_id)
        db_item = {
            'kml_id': kml_id,
            'admin_id': kml_admin_id,
            'created': timestamp,
            'updated': timestamp,
            'bucket': self.bucket_name,
            'file_key': file_key,
            'empty': empty,
            'length': file_length,
            'encoding': KML_FILE_CONTENT_ENCODING,
            'content_type': KML_FILE_CONTENT_TYPE,
            'author': author,
            'author_version': author_version
        }
        try:
            self.table.put_item(Item=db_item)
        except EndpointConnectionError as error:
            logger.exception('Failed to connect to DynamoDB: %s', error)
            abort(502, 'Backend DB connection error, please consult logs')
        return db_item

    def get_item(self, kml_id):
        logger.debug('Get dynamodb item with primary key %s', kml_id)
        try:
            item = self.table.get_item(Key={'kml_id': kml_id}).get('Item', None)
        except EndpointConnectionError as error:
            logger.exception('Failed to connect to DynamoDB: %s', error)
            abort(502, 'Backend DB connection error, please consult logs')

        if item is None:
            logger.error("Could not find the following kml id in the database: %s", kml_id)
            abort(404, f"Could not find {kml_id} within the database.")

        return item

    def get_item_by_admin_id(self, admin_id):
        logger.debug('Get dynamodb item with admin_id %s', admin_id)
        try:
            items = self.table.query(
                IndexName='admin_id-index',
                KeyConditionExpression=Key('admin_id').eq(admin_id),
            ).get('Items', None)
        except EndpointConnectionError as error:
            logger.exception('Failed to connect to DynamoDB: %s', error)
            abort(502, 'Backend DB connection error, please consult logs')

        if items is None or len(items) == 0:
            logger.error(
                "Could not find the following kml admin_id %s in the database: %s", admin_id, items
            )
            abort(404, f"Could not find {admin_id} within the database.")

        if len(items) > 1:
            logger.error(
                "Find more than one kml_id %s within the database !",
                admin_id,
                extra={'kml_items': items}
            )

        return items[0]

    def update_item(self, kml_id, db_item, file_length, timestamp, empty, author_version=None):
        logger.debug('Updating dynamodb item with primary key %s', kml_id)
        db_item['updated'] = timestamp
        db_item['empty'] = empty
        db_item['length'] = file_length
        attribute_updates = {
            'updated': {
                'Value': timestamp, 'Action': 'PUT'
            },
            'empty': {
                'Value': empty, 'Action': 'PUT'
            },
            'length': {
                'Value': file_length, 'Action': 'PUT'
            }
        }
        if author_version is not None:
            attribute_updates['author_version'] = {'Value': author_version, 'Action': 'PUT'}
            db_item['author_version'] = author_version
        try:
            self.table.update_item(Key={'kml_id': kml_id}, AttributeUpdates=attribute_updates)
        except EndpointConnectionError as error:
            logger.exception('Failed to connect to DynamoDB: %s', error)
            abort(502, 'Backend DB connection error, please consult logs')

        return db_item

    def delete_item(self, kml_id):
        logger.debug('Deleting dynamodb item with primary key %s', kml_id)
        try:
            self.table.delete_item(Key={'kml_id': kml_id})
        except EndpointConnectionError as error:
            logger.exception('Failed to connect to DynamoDB: %s', error)
            abort(502, 'Backend DB connection error, please consult logs')
