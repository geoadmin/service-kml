import logging
import logging.config
import os
import re
from functools import wraps
from urllib.parse import unquote_plus

import yaml

import defusedxml.ElementTree as ET
from defusedxml.ElementTree import ParseError

from flask import abort
from flask import jsonify
from flask import make_response
from flask import request

from app.settings import KML_FILE_CONTENT_TYPE
from app.settings import KML_STORAGE_HOST_URL

logger = logging.getLogger(__name__)

ALLOWED_DOMAINS = [
    r'.*\.geo\.admin\.ch',
    r'.*bgdi\.ch',
    r'.*\.swisstopo\.cloud',
]

ALLOWED_DOMAINS_PATTERN = '({})'.format('|'.join(ALLOWED_DOMAINS))


def make_error_msg(code, msg):
    return make_response(jsonify({'success': False, 'error': {'code': code, 'message': msg}}), code)


def get_logging_cfg():
    cfg_file = os.getenv('LOGGING_CFG', 'app/config/logging-cfg-local.yml')
    print(f"LOGS_DIR is {os.getenv('LOGS_DIR')}")
    print(f"LOGGING_CFG is {cfg_file}")

    config = {}
    with open(cfg_file, 'rt', encoding='utf-8') as fd:
        config = yaml.safe_load(os.path.expandvars(fd.read()))

    logger.debug('Load logging configuration from file %s', cfg_file)
    return config


def init_logging():
    config = get_logging_cfg()
    logging.config.dictConfig(config)


def prevent_erroneous_kml(kml_string):
    # remove all attributes with on prefix and all script elements
    kml_string = re.sub(r'on\w*=(".+?"|\'.+?\')', '', kml_string, flags=re.IGNORECASE)
    kml_string = re.sub(
        r'(<|&lt;)\s*\bscript\b.*?(>|&gt;).*?(<|&lt;)/\s*\bscript\b\s*(>|&gt;)',
        ' ',
        kml_string,
        flags=re.IGNORECASE | re.DOTALL
    )
    return kml_string


def bytes_conversion(byte, too, b_size=1024):
    choice = {'kb': 1, 'mb': 2, 'gb': 3, 'tb': 4}
    return byte / (b_size**choice[too.lower()])


def validate_content_type(content):

    def inner_decorator(func):

        @wraps(func)
        def wrapped(*args, **kwargs):
            if request.mimetype != content:
                logger.error('Unsupported Media Type %s: should be %s', request.mimetype, content)
                abort(415, 'Unsupported Media Type')
            return func(*args, **kwargs)

        return wrapped

    return inner_decorator


def validate_content_length(max_length):

    def inner_decorator(func):

        @wraps(func)
        def wrapped(*args, **kwargs):
            if request.content_length > max_length:
                logger.error(
                    'Payload too large: payload=%s MB, max_allowed=%s MB',
                    bytes_conversion(request.content_length, 'MB'),
                    bytes_conversion(max_length, 'MB'),
                )
                abort(413, "Payload too large")
            return func(*args, **kwargs)

        return wrapped

    return inner_decorator


def validate_kml_string(kml_string):
    prevent_erroneous_kml(kml_string)
    try:
        root = ET.fromstring(kml_string)
    except ParseError as err:
        logger.error("Invalid kml file %s", err)
        abort(400, 'Invalid kml file')

    def no_text(text):
        if text is None:
            return True
        if text.strip(r'\n\t ') == '':
            return True
        return False

    # Check if this is an empty kml; <kml></kml>
    empty = False
    if len(root.findall('./')) == 0 and no_text(root.text) and len(root.attrib) == 0:
        empty = True

    return kml_string, empty


def validate_permissions(db_item):
    admin_id = request.form.get('admin_id', '')

    if db_item['admin_id'] != admin_id:
        logger.error(
            'Permission denied for kml %s, admin_id=%s, request.form.admin_id=%s',
            db_item['kml_id'],
            db_item['admin_id'],
            admin_id
        )
        abort(403, "Permission denied")
    return admin_id


def validate_kml_file():
    if 'kml' not in request.files:
        logger.error('KML file missing in request')
        abort(400, 'KML file missing in request')
    file = request.files['kml']
    if file.mimetype != KML_FILE_CONTENT_TYPE:
        logger.error(
            'Unsupported KML media type %s; only %s is allowed',
            file.mimetype,
            KML_FILE_CONTENT_TYPE
        )
        abort(415, "Unsupported KML media type")
    if 'charset' in file.mimetype_params:
        quoted_data = file.read().decode(file.mimetype_params['charset'])
    else:
        quoted_data = file.read().decode('utf-8')

    return validate_kml_string(unquote_plus(quoted_data))


def get_kml_file_link(file_key):
    if KML_STORAGE_HOST_URL:
        return f'{KML_STORAGE_HOST_URL}/{file_key}'
    return f'{request.host_url}{file_key}'
