import gzip
import logging
import logging.config
import os
import re
from functools import wraps
from itertools import chain
from urllib.parse import unquote_plus

import yaml

import defusedxml.ElementTree as ET
from defusedxml.ElementTree import ParseError

from flask import abort
from flask import jsonify
from flask import make_response
from flask import request

from app.settings import KML_FILE_CONTENT_TYPE
from app.settings import KML_MAX_SIZE
from app.settings import KML_STORAGE_HOST_URL

logger = logging.getLogger(__name__)


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


def validate_content_length():

    def inner_decorator(func):

        @wraps(func)
        def wrapped(*args, **kwargs):
            # NOTE: the multipart/form-data has an unknown overhead (boundary string is set by the
            # client), but with a 1KB overhead we are good. The goal of this check is to avoid
            # uploading huge file which would starve the memory and rejecting them later by
            # validate_file_length()
            multipart_overhead = 1024
            max_length = KML_MAX_SIZE + multipart_overhead
            if request.content_length > max_length:
                logger.error(
                    'Payload too large: payload=%s MB, max_allowed=%s MB',
                    bytes_conversion(request.content_length, 'MB'),
                    bytes_conversion(max_length, 'MB'),
                )
                abort(413, f"Payload too large, max allowed={bytes_conversion(max_length, 'MB')}MB")
            return func(*args, **kwargs)

        return wrapped

    return inner_decorator


def validate_file_length(file_content, max_length):
    if len(file_content) > max_length:
        logger.error(
            'KML file too large: payload=%s MB, max_allowed=%s MB',
            bytes_conversion(request.content_length, 'MB'),
            bytes_conversion(max_length, 'MB'),
        )
        abort(413, f"KML file too large, max allowed={bytes_conversion(max_length, 'MB')}MB")


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
    file_content = file.read()
    validate_file_length(file_content, KML_MAX_SIZE)
    file_content = decompress_if_gzipped(file_content)
    try:
        if 'charset' in file.mimetype_params:
            quoted_data = file_content.decode(file.mimetype_params['charset'])
        else:
            quoted_data = file_content.decode('utf-8')
    except UnicodeDecodeError as error:
        logger.error("Could not decode file content: %s", error)
        abort(400, "Could not decode file content")
    kml_string, empty = validate_kml_string(unquote_plus(quoted_data))
    return gzip_string(kml_string), empty


def get_kml_file_link(file_key):
    if KML_STORAGE_HOST_URL:
        return f'{KML_STORAGE_HOST_URL}/{file_key}'
    return f'{request.host_url}{file_key}'


def get_registered_method(app, url_rule):
    '''Returns the list of registered method for the given endpoint'''

    # The list of registered method is taken from the werkzeug.routing.Rule. A Rule object
    # has a methods property with the list of allowed method on an endpoint. If this property is
    # missing then all methods are allowed.
    # See https://werkzeug.palletsprojects.com/en/2.0.x/routing/#werkzeug.routing.Rule
    all_methods = ['GET', 'HEAD', 'OPTIONS', 'POST', 'PUT', 'DELETE']
    return set(
        chain.from_iterable(
            [
                r.methods if r.methods else all_methods
                for r in app.url_map.iter_rules()
                if r.rule == str(url_rule)
            ]
        )
    )


def gzip_string(string):
    try:
        data = string.encode('utf-8')
    except (UnicodeDecodeError, AttributeError) as error:
        logger.error("Error when encoding string: %s", error)
        raise error
    gzipped_data = gzip.compress(data, compresslevel=5)

    return gzipped_data


def decompress_if_gzipped(file_content):
    '''Returns the file content as bytes object, after unzipping the file if necessary'''

    try:
        ret = gzip.decompress(file_content)
    except OSError as error:
        if "Not a gzipped file" in str(error):
            ret = file_content
            logger.info("Received unzipped kml-string: %s", file_content)
        else:
            logger.error("Error when trying to decompress kml file: %s", error)
            raise error
    return ret
