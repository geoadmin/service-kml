import logging
from urllib.parse import unquote_plus

from flask import jsonify
from flask import make_response
from flask import request

from app import app
from app.helpers.utils import validate_content_type
from app.helpers.utils import validate_kml_string
from app.helpers.s3 import S3FileHandling
from app.helpers.dynamodb import DynamoDBFilesHandler
from app.version import APP_VERSION
from datetime import datetime
from datetime import timezone
import uuid
import base64

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
    timestamp = datetime.now(timezone.utc)
    executor = S3FileHandling()
    executor.upload_object_to_bucket(kml_id, kml_string)
    # enforcer = DynamoDBFilesHandler()
    # enforcer.save_item(kml_admin_id, kml_id, timestamp)
    return make_response(jsonify({'code': 201, 'id': kml_admin_id, "links": { "self": f'service-url/kml/{kml_admin_id}', 'kml': f"public.geo.admin.ch/{kml_id}"}}), 201)
