from app.helpers.utils import get_dynamodb_connection

class DynamoDBFilesHandler:

    def __init__(self):
        self.dynamodb = get_dynamodb_connection()

    def get_dynamodb_table(self, table_name='shorturl', region='eu-west-1'):
        table = self.dynamodb.Table(table_name, region)
        return table


    def __init__(self, table_name, bucket_name, table_region):
        # We use instance roles
        self.table = self.get_dynamodb_table()
        self.bucket_name = bucket_name

    def save_item(self, kml_admin_id, file_id, timestamp):
        self.table.put_item(
                Item={
                    'adminId': kml_admin_id,
                    'fileId': file_id,
                    'timestamp': timestamp,
                    'bucket': self.bucket_name
                }
            )

    def get_item(self, kml_admin_id):
        item = self.table.get_item(Key={'adminId': str(kml_admin_id)}).get('Item', None)
        return item

    def update_item_timestamp(self, kml_admin_id, timestamp):
        self.table.update_item(Key={
            'adminId': kml_admin_id
        }, AttributeUpdates={
            'timestamp': {
                'Value': timestamp,
                'Action': 'PUT'
            }
        })









































































