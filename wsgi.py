"""
The gevent monkey import and patch suppress a warning, and a potential problem.
Gunicorn would call it anyway, but if it tries to call it after the ssl module
has been initialized in another module (like, in our code, by the botocore
library), then it could lead to inconsistencies in how the ssl module is used.
Thus we patch the ssl module through gevent.monkey.patch_all before any other
import, especially the app import, which would cause the boto module to be
loaded, which would in turn load the ssl module.
"""
# pylint: disable=wrong-import-position,wrong-import-order
import gevent.monkey

gevent.monkey.patch_all()

import os

from gunicorn.app.base import BaseApplication

from app import app as application
from app.helpers.utils import get_logging_cfg


class StandaloneApplication(BaseApplication):  # pylint: disable=abstract-method

    def __init__(self, app, options=None):  # pylint: disable=redefined-outer-name
        self.options = options or {}
        self.application = app
        super().__init__()

    def load_config(self):
        config = {
            key: value for key,
            value in self.options.items() if key in self.cfg.settings and value is not None
        }
        for key, value in config.items():
            self.cfg.set(key.lower(), value)

    def load(self):
        return self.application


# We use the port 5000 as default, otherwise we set the HTTP_PORT env variable within the container.
if __name__ == '__main__':
    HTTP_PORT = str(os.environ.get('HTTP_PORT', "5000"))
    worker_tmp_dir = os.getenv("GUNICORN_WORKER_TMP_DIR", "/tmp/gunicorn_workers")
    # Bind to 0.0.0.0 to let your app listen to all network interfaces.
    options = {
        'bind': f"0.0.0.0:{HTTP_PORT}",
        'worker_class': 'gevent',
        'workers': 2,  # scaling horizontally is left to Kubernetes
        'timeout': 60,
        'logconfig_dict': get_logging_cfg(),
        'forwarded_allow_ips': os.getenv('FORWARED_ALLOW_IPS', '*'),
        'worker_tmp_dir': worker_tmp_dir if worker_tmp_dir != '' else None,
        'secure_scheme_headers':
            {
                os.getenv('FORWARDED_PROTO_HEADER_NAME', 'X-Forwarded-Proto').upper(): 'https'
            }
    }
    StandaloneApplication(application, options).run()
