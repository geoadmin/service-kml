from flask import jsonify
from flask import make_response


def make_error_msg(code, msg):
    response = make_response(
        jsonify({
            'success': False, 'error': {
                'code': code, 'message': msg
            }
        }),
        code,
        {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methogs': 'POST',
            'Access-Control-Allow-Headers': 'Content-Type'
        }
    )
    return response
