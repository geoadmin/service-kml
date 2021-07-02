from app.helpers.utils import get_dynamodb_resource


class DynamoDBFilesHandler:

    def __init__(self, table_name, bucket_name, endpoint_url, table_region):
        self.dynamodb = get_dynamodb_resource(table_region, endpoint_url)
        self.table = self.dynamodb.Table(table_name)
        self.bucket_name = bucket_name
        self.endpoint = endpoint_url

    def save_item(self, kml_admin_id, file_id, timestamp):
        self.table.put_item(
            Item={
                'adminId': kml_admin_id,
                'file_id': file_id,
                'timestamp': timestamp,
                'bucket': self.bucket_name
            }
        )

    def get_item(self, kml_admin_id):
        item = self.table.get_item(Key={'adminId': str(kml_admin_id)}).get('Item', None)
        return item

    def update_item_timestamp(self, kml_admin_id, timestamp):
        self.table.update_item(
            Key={'adminId': kml_admin_id},
            AttributeUpdates={'timestamp': {
                'Value': timestamp, 'Action': 'PUT'
            }}
        )
