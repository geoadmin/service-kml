import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve(strict=True).parent.parent
ENV_FILE = os.getenv('ENV_FILE', None)
if ENV_FILE:
    from dotenv import load_dotenv

    print(f"Running locally hence injecting env vars from {ENV_FILE}")
    load_dotenv(ENV_FILE, override=True, verbose=True)

AWS_S3_BUCKET_NAME = os.environ['AWS_S3_BUCKET_NAME']
AWS_S3_REGION_NAME = os.environ['AWS_S3_REGION_NAME']
AWS_S3_ENDPOINT_URL = os.getenv('AWS_S3_ENDPOINT_URL', None)
AWS_DB_REGION_NAME = os.environ['AWS_DB_REGION_NAME']
AWS_DB_TABLE_NAME = os.environ['AWS_DB_TABLE_NAME']
AWS_DB_ENDPOINT_URL = os.getenv('AWS_DB_ENDPOINT_URL', None)
KML_STORAGE_HOST_URL = os.getenv('KML_STORAGE_HOST_URL', None)

ROUTE_BASE_PREFIX = 'api/kml'
ROUTE_ADMIN_PREFIX = f'{ROUTE_BASE_PREFIX}/admin'
ROUTE_FILES_PREFIX = f'{ROUTE_BASE_PREFIX}/files'

MB = 1024 * 1024
KML_MAX_SIZE = int(os.getenv('KML_MAX_SIZE', str(2 * MB)))

KML_FILE_CONTENT_TYPE = 'application/vnd.google-earth.kml+xml'

ALLOWED_DOMAINS = os.getenv(
    'ALLOWED_DOMAINS', r'.*\.geo\.admin\.ch,.*bgdi\.ch,.*\.swisstopo\.cloud'
).split(',')
ALLOWED_DOMAINS_PATTERN = '({})'.format('|'.join(ALLOWED_DOMAINS))
