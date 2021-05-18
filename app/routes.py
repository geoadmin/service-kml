import logging
from urllib.parse import unquote_plus

from flask import jsonify
from flask import make_response
from flask import request

from app import app
from app.helpers.utils import validate_content
from app.helpers.utils import validate_kml_string
from app.version import APP_VERSION

logger = logging.getLogger(__name__)


@app.route('/checker', methods=['GET'])
def check():
    return make_response(jsonify({'success': True, 'message': 'OK', 'version': APP_VERSION}))


@app.route('/kml', methods=['POST'])
@validate_content("application/vnd.google-earth.kml+xml")
def post_kml():
    # IE9 sends data urlencoded
    quoted_str = request.get_data().decode('utf-8')
    data = unquote_plus(quoted_str)
    kml_string = validate_kml_string(data)
    return make_response(jsonify({'success': True, 'message': 'OK', 'version': APP_VERSION}))
