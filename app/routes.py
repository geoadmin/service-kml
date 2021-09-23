import logging
from base64 import urlsafe_b64encode
from datetime import datetime
from datetime import timezone
from uuid import uuid4

from flask import abort
from flask import jsonify
from flask import make_response
from flask import request
from flask.helpers import url_for

from app import app
from app.helpers.dynamodb import get_db
from app.helpers.s3 import get_storage
from app.helpers.utils import get_kml_file_link
from app.helpers.utils import validate_content_length
from app.helpers.utils import validate_content_type
from app.helpers.utils import validate_kml_file
from app.helpers.utils import validate_permissions
from app.settings import KML_MAX_SIZE
from app.settings import ROUTE_ADMIN_PREFIX
from app.settings import ROUTE_BASE_PREFIX
from app.settings import ROUTE_FILES_PREFIX
from app.version import APP_VERSION

logger = logging.getLogger(__name__)


@app.route(f'/{ROUTE_BASE_PREFIX}/checker', methods=['GET'])
def checker():
    return make_response(jsonify({'success': True, 'message': 'OK', 'version': APP_VERSION}))


# NOTE the /kml/files/<kml_id> route is directly served by S3


@app.route(f'/{ROUTE_ADMIN_PREFIX}', methods=['POST'])
@validate_content_type("multipart/form-data")
@validate_content_length(KML_MAX_SIZE)
def create_kml():
    # Get the kml file data
    kml_string, empty = validate_kml_file()

    # Get the author
    author = request.form.get('author', 'unknown')

    kml_admin_id = urlsafe_b64encode(uuid4().bytes).decode('utf8').replace('=', '')
    kml_id = urlsafe_b64encode(uuid4().bytes).decode('utf8').replace('=', '')
    file_key = f'{ROUTE_FILES_PREFIX}/{kml_id}'
    timestamp = datetime.utcnow().replace(tzinfo=timezone.utc).isoformat()

    storage = get_storage()
    storage.upload_object_to_bucket(file_key, kml_string)

    db = get_db()
    db.save_item(kml_id, kml_admin_id, file_key, timestamp, empty, author)

    return make_response(
        jsonify(
            {
                'id': kml_id,
                'admin_id': kml_admin_id,
                'success': True,
                'created': timestamp,
                'updated': timestamp,
                'empty': empty,
                'links':
                    {
                        'self': f'{request.base_url}/{kml_id}',
                        'kml': get_kml_file_link(file_key),
                    }
            }
        ),
        201
    )


@app.route(f'/{ROUTE_ADMIN_PREFIX}', methods=['GET'])
def get_kml_metadata_by_admin_id():
    admin_id = request.args.get('admin_id')
    if not admin_id:
        logger.error("Query parameter admin_id is required: query=%s", request.args)
        abort(400, "Query parameter admin_id is required")
    item = get_db().get_item_by_admin_id(admin_id)
    return make_response(
        jsonify(
            {
                'id': item['kml_id'],
                'admin_id': admin_id,
                'success': True,
                'created': item['created'],
                'updated': item['updated'],
                'empty': item['empty'],
                'links':
                    {
                        'self': url_for('get_kml_metadata', kml_id=item['kml_id'], _external=True),
                        'kml': get_kml_file_link(item['file_key']),
                    }
            }
        ),
        200
    )


@app.route(f'/{ROUTE_ADMIN_PREFIX}/<kml_id>', methods=['GET'])
def get_kml_metadata(kml_id):
    item = get_db().get_item(kml_id)
    return make_response(
        jsonify(
            {
                'id': kml_id,
                'success': True,
                'created': item['created'],
                'updated': item['updated'],
                'empty': item['empty'],
                'links': {
                    'self': request.base_url,
                    'kml': get_kml_file_link(item['file_key']),
                }
            }
        ),
        200
    )


@app.route(f'/{ROUTE_ADMIN_PREFIX}/<kml_id>', methods=['PUT'])
@validate_content_type("multipart/form-data")
@validate_content_length(KML_MAX_SIZE)
def update_kml(kml_id):
    db = get_db()

    item = db.get_item(kml_id)
    admin_id = validate_permissions(item)

    # Get the kml file data
    kml_string, empty = validate_kml_file()

    storage = get_storage()
    storage.upload_object_to_bucket(item['file_key'], kml_string)

    timestamp = datetime.utcnow().replace(tzinfo=timezone.utc).isoformat()
    db.update_item(kml_id, timestamp, empty)

    return make_response(
        jsonify(
            {
                'id': kml_id,
                'admin_id': admin_id,
                'success': True,
                'created': item['created'],
                'updated': timestamp,
                'empty': empty,
                'links': {
                    'self': request.base_url,
                    'kml': get_kml_file_link(item['file_key']),
                }
            }
        ),
        200
    )


@app.route(f'/{ROUTE_ADMIN_PREFIX}/<kml_id>', methods=['DELETE'])
@validate_content_type("multipart/form-data")
def delete_kml(kml_id):
    db = get_db()
    item = db.get_item(kml_id)

    validate_permissions(item)

    storage = get_storage()
    storage.delete_file_in_bucket(item['file_key'])

    db.delete_item(kml_id)

    return make_response(
        jsonify(
            {
                "success": True,
                "id": kml_id,
                "message": f'The kml {kml_id} was successfully deleted.'
            }
        ),
        200
    )
