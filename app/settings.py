import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve(strict=True).parent.parent
ENV_FILE = os.getenv('ENV_FILE', f'{BASE_DIR}/.env.default')
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
KML_STORAGE_URL = os.getenv('KML_STORAGE_URL')
