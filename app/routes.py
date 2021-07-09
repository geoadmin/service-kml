import base64
import logging
import time
import uuid
from urllib.parse import unquote_plus

from flask import abort
from flask import jsonify
from flask import make_response
from flask import request

from app import app
from app.helpers.dynamodb import DynamoDBFilesHandler
from app.helpers.s3 import S3FileHandling
from app.helpers.utils import validate_content_type
from app.helpers.utils import validate_kml_string
from app.settings import AWS_DB_ENDPOINT_URL
from app.settings import AWS_DB_REGION_NAME
from app.settings import AWS_DB_TABLE_NAME
from app.settings import AWS_S3_BUCKET_NAME
from app.settings import AWS_S3_ENDPOINT_URL
from app.settings import AWS_S3_REGION_NAME
from app.settings import KML_STORAGE_URL
from app.version import APP_VERSION

logger = logging.getLogger(__name__)


@app.route('/checker', methods=['GET'])
def check():
    return make_response(jsonify({'success': True, 'message': 'OK', 'version': APP_VERSION}))


@app.route('/kml', methods=['POST'])
@validate_content_type("application/vnd.google-earth.kml+xml")
def post_kml():
    # IE9 sends data urlencoded
    quoted_str = request.get_data().decode('utf-8')
    data = unquote_plus(quoted_str)
    kml_string = validate_kml_string(data)
    kml_admin_id = base64.urlsafe_b64encode(uuid.uuid4().bytes).decode('utf8').replace('=', '')
    kml_id = base64.urlsafe_b64encode(uuid.uuid4().bytes).decode('utf8').replace('=', '')
    timestamp = time.strftime('%Y-%m-%d %X', time.localtime())
    executor = S3FileHandling(AWS_S3_REGION_NAME, AWS_S3_ENDPOINT_URL)
    executor.upload_object_to_bucket(kml_id, kml_string, bucket_name=AWS_S3_BUCKET_NAME)
    enforcer = DynamoDBFilesHandler(
        table_name=AWS_DB_TABLE_NAME,
        bucket_name=AWS_S3_BUCKET_NAME,
        table_region=AWS_DB_REGION_NAME,
        endpoint_url=AWS_DB_ENDPOINT_URL
    )
    enforcer.save_item(kml_admin_id, kml_id, timestamp)
    return make_response(
        jsonify(
            {
                'success': True,
                'id': kml_admin_id,
                'links':
                    {
                        'self': f'{request.host_url}/kml/{kml_admin_id}',
                        'kml': f'{KML_STORAGE_URL}/{kml_id}
                    }
            }
        ),
        201
    )


@app.route('/kml/<kml_admin_id>', methods=['GET'])
def get_id(kml_admin_id):
    enforcer = DynamoDBFilesHandler(
        table_name=AWS_DB_TABLE_NAME,
        bucket_name=AWS_S3_BUCKET_NAME,
        table_region=AWS_DB_REGION_NAME,
        endpoint_url=AWS_DB_ENDPOINT_URL
    )
    item = enforcer.get_item(kml_admin_id)

    # Fetching a non existing Item will return "None"
    if item is None:
        logger.error("Could not find the following kml id in the database: %s", kml_admin_id)
        abort(400, f"Could not find {kml_admin_id} within the database.")

    return make_response(
        jsonify(
            {
                'success': True,
                'id': kml_admin_id,
                'links':
                    {
                        'self': f'{request.host_url}/kml/{item["admin_id"]}',
                        'kml': f'{KML_STORAGE_URL}/{item["file_id"]}'
                    }
            }
        ),
        200
    )
