import logging
import logging.config
import os
import re
from functools import wraps

import yaml

import defusedxml.ElementTree as ET
from defusedxml.ElementTree import ParseError

from flask import abort
from flask import jsonify
from flask import make_response
from flask import request

logger = logging.getLogger(__name__)

ALLOWED_DOMAINS = [
    r'.*\.geo\.admin\.ch',
    r'.*bgdi\.ch',
    r'.*\.swisstopo\.cloud',
]

ALLOWED_DOMAINS_PATTERN = '({})'.format('|'.join(ALLOWED_DOMAINS))

EXPECTED_KML_CONTENT_TYPE = 'application/vnd.google-earth.kml+xml'


def make_error_msg(code, msg):
    return make_response(jsonify({'success': False, 'error': {'code': code, 'message': msg}}), code)


def get_logging_cfg():
    cfg_file = os.getenv('LOGGING_CFG', 'logging-cfg-local.yml')

    config = {}
    with open(cfg_file, 'rt') as fd:
        config = yaml.safe_load(fd.read())

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
    byte_float = float(byte)
    return byte / (b_size**choice[too.lower()])


def validate_content_type(content):

    def inner_decorator(func):

        @wraps(func)
        def wrapped(*args, **kwargs):
            if request.content_type != content:
                abort(make_error_msg(415, 'Unsupported Media Type'))
            return func(*args, **kwargs)

        return wrapped

    return inner_decorator


def validate_kml_string(kml_string):

    max_file_size = 1024 * 1024 * 2

    if len(kml_string) > max_file_size:
        error_msg = 'File size exceed {} MB. The actual file size is {} MB'.format(
            bytes_conversion(max_file_size, 'MB'), bytes_conversion(len(kml_string), 'MB')
        )
        logger.error(error_msg)
        abort(413, error_msg)
    prevent_erroneous_kml(kml_string)
    try:
        ET.fromstring(kml_string)
    except ParseError as err:
        logger.error("Invalid kml file %s", err)
        abort(400, 'Invalid kml file')

    return kml_string
