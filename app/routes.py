import base64
import datetime
import logging
import uuid
from urllib.parse import unquote_plus

from flask import jsonify
from flask import make_response
from flask import request

from app import app
from app.helpers.dynamodb import get_db
from app.helpers.s3 import get_storage
from app.helpers.utils import validate_content_type
from app.helpers.utils import validate_kml_string
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
    timestamp = datetime.datetime.utcnow().replace(tzinfo=datetime.timezone.utc).isoformat()
    storage = get_storage()
    storage.upload_object_to_bucket(kml_id, kml_string)
    db = get_db()  # pylint: disable=invalid-name
    db.save_item(kml_admin_id, kml_id, timestamp)
    item = db.get_item(kml_admin_id)

    return make_response(
        jsonify(
            {
                'success': True,
                'id': kml_admin_id,
                'created': item['created'],
                'updated': item['updated'],
                'links':
                    {
                        'self': f'{request.host_url}kml/{kml_admin_id}',
                        'kml': f'{KML_STORAGE_URL}/{kml_id}'
                    }
            }
        ),
        201
    )


@app.route('/kml/<kml_admin_id>', methods=['GET'])
def get_id(kml_admin_id):
    db = get_db()  # pylint: disable=invalid-name
    item = db.get_item(kml_admin_id)

    return make_response(
        jsonify(
            {
                'success': True,
                'id': kml_admin_id,
                'created': item['created'],
                'updated': item['updated'],
                'links':
                    {
                        'self': f'{request.host_url}kml/{item["admin_id"]}',
                        'kml': f'{KML_STORAGE_URL}/{item["file_id"]}'
                    }
            }
        ),
        200
    )


@app.route('/kml/<kml_admin_id>', methods=['PUT'])
@validate_content_type("application/vnd.google-earth.kml+xml")
def put_kml(kml_admin_id):
    db = get_db()  # pylint: disable=invalid-name
    item = db.get_item(kml_admin_id)

    kml_id = item['file_id']

    quoted_str = request.get_data().decode('utf-8')
    data = unquote_plus(quoted_str)
    kml_string = validate_kml_string(data)

    storage = get_storage()
    storage.upload_object_to_bucket(kml_id, kml_string)

    timestamp = datetime.datetime.utcnow().replace(tzinfo=datetime.timezone.utc).isoformat()
    db.update_item_timestamp(kml_admin_id, timestamp)
    item = db.get_item(kml_admin_id)

    return make_response(
        jsonify(
            {
                'success': True,
                'id': kml_admin_id,
                'created': item['created'],
                'updated': item['updated'],
                'links':
                    {
                        'self': f'{request.host_url}kml/{item["admin_id"]}',
                        'kml': f'{KML_STORAGE_URL}/{item["file_id"]}'
                    }
            }
        ),
        200
    )


@app.route('/kml/<kml_admin_id>', methods=['DELETE'])
def delete_id(kml_admin_id):
    db = get_db()  # pylint: disable=invalid-name
    item = db.get_item(kml_admin_id)

    file_id = item['file_id']

    storage = get_storage()
    storage.delete_file_in_bucket(file_id)

    db.delete_item(kml_admin_id)

    return make_response(
        jsonify(
            {
                "success": True,
                "id": kml_admin_id,
                "message": f'The kml {item["admin_id"]} was successfully deleted.'
            }
        ),
        200
    )
