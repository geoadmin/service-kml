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

MB = 1024 * 1024
KML_MAX_SIZE = int(os.getenv('KML_MAX_SIZE', str(2 * MB)))

KML_FILE_CONTENT_TYPE = 'application/vnd.google-earth.kml+xml'
KML_FILE_CONTENT_ENCODING = 'gzip'
# No cache behavior taken from
# https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Cache-Control#preventing_caching
NO_CACHE = 'no-store, max-age=0'
KML_FILE_CACHE_CONTROL = os.getenv('KML_FILE_CACHE_CONTROL', NO_CACHE)

ALLOWED_DOMAINS = os.getenv('ALLOWED_DOMAINS', r'.*').split(',')
ALLOWED_DOMAINS_PATTERN = f"({'|'.join(ALLOWED_DOMAINS)})"

SCRIPT_NAME = os.getenv('SCRIPT_NAME', '')

CACHE_CONTROL = os.getenv('CACHE_CONTROL', 'no-cache, no-store, must-revalidate')
CACHE_CONTROL_4XX = os.getenv('CACHE_CONTROL_4XX', 'public, max-age=3600')

DEFAULT_AUTHOR_VERSION = '0.0.0'
