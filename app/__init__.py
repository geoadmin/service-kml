import logging
import re
import time

from werkzeug.exceptions import HTTPException

from flask import Flask
from flask import abort
from flask import g
from flask import request
from flask import url_for

from app.helpers.utils import get_registered_method
from app.helpers.utils import make_error_msg
from app.settings import ALLOWED_DOMAINS_PATTERN
from app.settings import CACHE_CONTROL
from app.settings import CACHE_CONTROL_4XX

logger = logging.getLogger(__name__)

# Standard Flask application initialisation

app = Flask(__name__)


# Add quick log of the routes used to all request.
# Important: this should be the first before_request method, to ensure
# a failure in another pre request method would stop logging.
@app.before_request
def log_route():
    g.setdefault('request_started', time.time())
    logger.info('%s %s', request.method, request.path)


# Add CORS Headers to all request
@app.after_request
def add_cors_header(response):
    # Do not add CORS header to internal /checker endpoint.
    if request.endpoint == 'checker':
        return response

    if (
        'Origin' in request.headers and
        re.match(ALLOWED_DOMAINS_PATTERN, request.headers['Origin'])
    ):
        response.headers['Access-Control-Allow-Origin'] = request.headers['Origin']

    # Always add the allowed methods.
    response.headers.set(
        'Access-Control-Allow-Methods', ', '.join(get_registered_method(app, request.endpoint))
    )
    response.headers.set('Access-Control-Allow-Headers', '*')
    return response


@app.after_request
def add_cache_control_header(response):
    # For /checker route we let the frontend proxy decide how to cache it.
    if request.method == 'GET' and request.endpoint != 'checker':
        if response.status_code >= 400:
            response.headers.set('Cache-Control', CACHE_CONTROL_4XX)
        else:
            response.headers.set('Cache-Control', CACHE_CONTROL)
            if 'no-cache' in CACHE_CONTROL:
                response.headers.set('Expire', 0)
    return response


# Reject request from non allowed origins
@app.before_request
def validate_origin():
    if 'Origin' not in request.headers:
        logger.error('Origin header is not set')
        abort(403, 'Permission denied')
    if not re.match(ALLOWED_DOMAINS_PATTERN, request.headers['Origin']):
        logger.error('Origin=%s is not allowed', request.headers['Origin'])
        abort(403, 'Permission denied')


@app.after_request
def log_response(response):
    logger.info(
        "%s %s - %s",
        request.method,
        request.path,
        response.status,
        extra={
            'response':
                {
                    "status_code": response.status_code,
                    "headers": dict(response.headers.items()),
                    "json": response.json
                },
            "duration": time.time() - g.get('request_started', time.time())
        }
    )
    return response


# Register error handler to make sure that every error returns a json answer
@app.errorhandler(Exception)
def handle_exception(err):
    """Return JSON instead of HTML for HTTP errors."""
    if isinstance(err, HTTPException):
        logger.error(err)
        return make_error_msg(err.code, err.description)

    logger.exception('Unexpected exception: %s', err)
    return make_error_msg(500, "Internal server error, please consult logs")


from app import routes  # pylint: disable=wrong-import-position
