import logging
from base64 import urlsafe_b64encode
from datetime import datetime
from datetime import timezone
from uuid import uuid4

from flask import abort
from flask import jsonify
from flask import make_response
from flask import request

from app import app
from app.helpers.dynamodb import get_db
from app.helpers.s3 import get_storage
from app.helpers.utils import get_json_metadata
from app.helpers.utils import validate_author
from app.helpers.utils import validate_content_length
from app.helpers.utils import validate_content_type
from app.helpers.utils import validate_kml_file
from app.helpers.utils import validate_permissions
from app.settings import DEFAULT_AUTHOR_VERSION
from app.settings import SCRIPT_NAME
from app.version import APP_VERSION

logger = logging.getLogger(__name__)


@app.route('/checker', methods=['GET'])
def checker():
    return make_response(jsonify({'success': True, 'message': 'OK', 'version': APP_VERSION}))


# NOTE the /files/<kml_id> route is directly served by S3


@app.route('/admin', methods=['POST'])
@validate_content_length()
@validate_content_type("multipart/form-data")
def create_kml():
    # Get the kml file data
    kml_string_gzip, empty = validate_kml_file()
    # Get the author
    author = validate_author()
    # Get the client version
    author_version = request.form.get('author_version', DEFAULT_AUTHOR_VERSION)

    kml_admin_id = urlsafe_b64encode(uuid4().bytes).decode('utf8').replace('=', '')
    kml_id = urlsafe_b64encode(uuid4().bytes).decode('utf8').replace('=', '')
    file_key = f'{SCRIPT_NAME}/files/{kml_id}'.lstrip('/')
    timestamp = datetime.utcnow().replace(tzinfo=timezone.utc).isoformat(timespec='milliseconds')

    storage = get_storage()
    storage.upload_object_to_bucket(file_key, kml_string_gzip)

    db = get_db()
    db_item = db.save_item(
        kml_id,
        kml_admin_id,
        file_key,
        len(kml_string_gzip),
        timestamp,
        empty,
        author,
        author_version
    )

    return make_response(jsonify(get_json_metadata(db_item, with_admin_id=True)), 201)


@app.route('/admin', methods=['GET'])
def get_kml_metadata_by_admin_id():
    admin_id = request.args.get('admin_id')
    if not admin_id:
        logger.error("Query parameter admin_id is required: query=%s", request.args)
        abort(400, "Query parameter admin_id is required")
    db_item = get_db().get_item_by_admin_id(admin_id)
    return make_response(jsonify(get_json_metadata(db_item, with_admin_id=True)), 200)


@app.route('/admin/<kml_id>', methods=['GET'])
def get_kml_metadata(kml_id):
    db_item = get_db().get_item(kml_id)
    return make_response(jsonify(get_json_metadata(db_item, with_admin_id=False)), 200)


@app.route('/admin/<kml_id>', methods=['PUT'])
@validate_content_length()
@validate_content_type("multipart/form-data")
def update_kml(kml_id):
    db = get_db()

    db_item = db.get_item(kml_id)
    admin_id = validate_permissions(db_item)

    # Get the client version
    author_version = request.form.get('author_version', None)

    # Get the kml file data
    kml_string_gzip, empty = validate_kml_file()

    storage = get_storage()
    storage.upload_object_to_bucket(db_item['file_key'], kml_string_gzip)

    timestamp = datetime.utcnow().replace(tzinfo=timezone.utc).isoformat(timespec='milliseconds')
    db_item = db.update_item(
        kml_id, db_item, len(kml_string_gzip), timestamp, empty, author_version
    )

    return make_response(jsonify(get_json_metadata(db_item, with_admin_id=True)), 200)


@app.route('/admin/<kml_id>', methods=['DELETE'])
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
