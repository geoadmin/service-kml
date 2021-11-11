import base64
import datetime
import logging
import uuid
from datetime import timedelta

from flask import url_for

from app.settings import AWS_DB_TABLE_NAME
from app.settings import KML_FILE_CONTENT_TYPE
from app.version import APP_VERSION
from tests.unit_tests.base import BaseRouteTestCase
from tests.unit_tests.base import prepare_kml_payload

logger = logging.getLogger(__name__)


class CheckerTests(BaseRouteTestCase):

    def test_checker(self):
        response = self.app.get(url_for('checker'), headers=self.origin_headers["allowed"])
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('Cache-Control', response.headers)
        self.assertEqual(response.content_type, "application/json")
        self.assertEqual(response.json, {"message": "OK", "success": True, "version": APP_VERSION})

    def test_checker_non_allowed_origin(self):
        response = self.app.get(url_for('checker'), headers=self.origin_headers["bad"])
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.content_type, "application/json")
        self.assertEqual(response.json["error"]["message"], "Permission denied")


class TestPostEndpoint(BaseRouteTestCase):

    def test_valid_kml_post(self):
        response = self.create_test_kml()
        self.assertEqual(response.status_code, 201)
        self.assertCors(response, ['POST', 'OPTIONS'])
        self.assertEqual(response.content_type, "application/json")  # pylint: disable=no-member
        self.compare_kml_contents(response, self.kml_dict["valid"])

    def test_invalid_kml_post(self):
        response = self.app.post(
            url_for('create_kml'),
            data=prepare_kml_payload(self.kml_dict["invalid"]),
            content_type="multipart/form-data",
            headers=self.origin_headers["allowed"]
        )
        self.assertEqual(response.status_code, 400)
        self.assertCors(response, ['POST', 'OPTIONS'])
        self.assertEqual(response.json['error']['message'], 'Invalid kml file')
        self.assertEqual(response.content_type, "application/json")

    def test_valid_kml_post_non_allowed_origin(self):
        response = self.app.post(
            url_for('create_kml'),
            data=prepare_kml_payload(self.kml_dict["valid"]),
            content_type="multipart/form-data",
            headers=self.origin_headers["bad"]
        )
        self.assertEqual(response.status_code, 403)
        self.assertCors(response, ['POST', 'OPTIONS'], check_origin=False)
        self.assertEqual(response.content_type, "application/json")
        self.assertEqual(response.json["error"]["message"], "Permission denied")

    def test_kml_post_invalid_content_type(self):
        response = self.app.post(
            url_for('create_kml'),
            data=prepare_kml_payload(self.kml_dict["valid"]),
            content_type=KML_FILE_CONTENT_TYPE,
            headers=self.origin_headers["allowed"]
        )
        self.assertEqual(response.status_code, 415)
        self.assertCors(response, ['POST', 'OPTIONS'])
        self.assertEqual(response.content_type, "application/json")
        self.assertEqual(response.json["error"]["message"], "Unsupported Media Type")

        response = self.app.post(
            url_for('create_kml'),
            data=prepare_kml_payload(self.kml_dict["valid"], content_type='application/json'),
            content_type="multipart/form-data",
            headers=self.origin_headers["allowed"]
        )
        self.assertEqual(response.status_code, 415)
        self.assertCors(response, ['POST', 'OPTIONS'])
        self.assertEqual(response.content_type, "application/json")
        self.assertEqual(response.json["error"]["message"], "Unsupported KML media type")


class TestGetEndpoint(BaseRouteTestCase):

    def test_get_metadata(self):
        id_to_fetch = self.sample_kml['id']
        stored_geoadmin_link = self.sample_kml['links']['kml']
        stored_kml_admin_link = self.sample_kml['links']['self']
        response = self.app.get(
            url_for('get_kml_metadata', kml_id=id_to_fetch), headers=self.origin_headers["allowed"]
        )
        self.assertEqual(response.status_code, 200)
        self.assertCors(response, ['GET', 'HEAD', 'OPTIONS'])
        self.assertIn('Cache-Control', response.headers)
        self.assertIn('no-cache', response.headers['Cache-Control'])
        self.assertIn('Expire', response.headers)
        self.assertEqual(response.headers['Expire'], '0')
        self.assertEqual(response.content_type, "application/json")
        self.assertEqual(stored_geoadmin_link, response.json['links']['kml'])
        self.assertEqual(stored_kml_admin_link, response.json['links']['self'])
        self.compare_kml_contents(response, self.kml_dict["valid"])

    def test_get_metadata_by_admin_id(self):
        admin_id = self.sample_kml['admin_id']
        stored_geoadmin_link = self.sample_kml['links']['kml']
        stored_kml_admin_link = self.sample_kml['links']['self']
        response = self.app.get(
            url_for('get_kml_metadata_by_admin_id', admin_id=admin_id),
            headers=self.origin_headers["allowed"]
        )
        self.assertEqual(response.status_code, 200, msg=f'Request failed: {response.json}')
        self.assertCors(response, ['GET', 'HEAD', 'OPTIONS'])
        self.assertIn('Cache-Control', response.headers)
        self.assertIn('no-cache', response.headers['Cache-Control'])
        self.assertIn('Expire', response.headers)
        self.assertEqual(response.headers['Expire'], '0')
        self.assertEqual(response.content_type, "application/json")
        self.assertEqual(stored_geoadmin_link, response.json['links']['kml'])
        self.assertEqual(stored_kml_admin_link, response.json['links']['self'])
        self.compare_kml_contents(response, self.kml_dict["valid"])

    def test_get_metadata_by_admin_id_invalid(self):
        response = self.app.get(
            url_for('get_kml_metadata_by_admin_id'), headers=self.origin_headers["allowed"]
        )
        self.assertEqual(response.status_code, 400)
        self.assertCors(response, ['GET', 'HEAD', 'OPTIONS'])
        self.assertIn('Cache-Control', response.headers)
        self.assertIn('max-age=3600', response.headers['Cache-Control'])
        self.assertNotIn('Expire', response.headers)
        self.assertEqual(response.content_type, 'application/json')
        self.assertIn('error', response.json, msg=f'error not found in answer: {response.json}')
        self.assertIn(
            'message',
            response.json['error'],
            msg=f'"message" not found in answer: {response.json}'
        )
        self.assertEqual(response.json['error']['message'], 'Query parameter admin_id is required')

        id_to_fetch = 'non-existent'
        response = self.app.get(
            url_for('get_kml_metadata_by_admin_id', admin_id=id_to_fetch),
            headers=self.origin_headers["allowed"]
        )
        self.assertEqual(response.status_code, 404)
        self.assertCors(response, ['GET', 'HEAD', 'OPTIONS'])
        self.assertIn('Cache-Control', response.headers)
        self.assertIn('max-age=3600', response.headers['Cache-Control'])
        self.assertNotIn('Expire', response.headers)
        self.assertEqual(response.content_type, 'application/json')
        self.assertEqual(response.content_type, "application/json")
        self.assertEqual(
            response.json['error']['message'], f'Could not find {id_to_fetch} within the database.'
        )

    def test_get_metadata_nonexistent(self):
        id_to_fetch = 'nonExistentId'
        response = self.app.get(
            url_for('get_kml_metadata', kml_id=id_to_fetch), headers=self.origin_headers["allowed"]
        )
        self.assertEqual(response.status_code, 404)
        self.assertCors(response, ['GET', 'HEAD', 'OPTIONS'])
        self.assertIn('Cache-Control', response.headers)
        self.assertIn('max-age=3600', response.headers['Cache-Control'])
        self.assertNotIn('Expire', response.headers)
        self.assertEqual(response.content_type, "application/json")
        self.assertEqual(
            response.json['error']['message'], f'Could not find {id_to_fetch} within the database.'
        )

    def test_get_metadata_non_allowed_origin(self):
        id_to_fetch = self.sample_kml['id']
        response = self.app.get(
            url_for('get_kml_metadata', kml_id=id_to_fetch), headers=self.origin_headers["bad"]
        )
        self.assertEqual(response.status_code, 403)
        self.assertCors(response, ['GET', 'HEAD', 'OPTIONS'], check_origin=False)
        self.assertIn('Cache-Control', response.headers)
        self.assertIn('max-age=3600', response.headers['Cache-Control'])
        self.assertNotIn('Expire', response.headers)
        self.assertEqual(response.content_type, "application/json")
        self.assertEqual(response.json["error"]["message"], "Permission denied")


class TestPutEndpoint(BaseRouteTestCase):

    def test_valid_kml_put(self):
        id_to_put = self.sample_kml['id']
        response = self.app.put(
            url_for('update_kml', kml_id=id_to_put),
            data=prepare_kml_payload(
                self.kml_dict["updated"], admin_id=self.sample_kml['admin_id']
            ),
            content_type="multipart/form-data",
            headers=self.origin_headers["allowed"]
        )
        self.assertEqual(response.status_code, 200)
        self.assertCors(response, ['PUT', 'OPTIONS'])
        self.assertEqual(response.content_type, "application/json")
        for key in self.sample_kml:
            # values for "updated" should and may differ, so ignore them in
            # this assertion
            if key != "updated":
                self.assertEqual(self.sample_kml[key], response.json[key])

        updated_item = self.dynamodb.Table(AWS_DB_TABLE_NAME).get_item(Key={
            'kml_id': id_to_put
        }).get('Item', None)
        self.assertAlmostEqual(
            datetime.datetime.fromisoformat(updated_item["updated"]).replace(tzinfo=None),
            datetime.datetime.utcnow(),
            delta=timedelta(seconds=0.3)
        )
        self.compare_kml_contents(response, self.kml_dict["updated"])

    def test_invalid_kml_put(self):
        id_to_put = self.sample_kml['id']

        response = self.app.put(
            url_for('update_kml', kml_id=id_to_put),
            data=prepare_kml_payload(
                self.kml_dict["invalid"], admin_id=self.sample_kml['admin_id']
            ),
            content_type="multipart/form-data",
            headers=self.origin_headers["allowed"]
        )
        self.assertEqual(response.status_code, 400)
        self.assertCors(response, ['PUT', 'OPTIONS'])
        self.assertEqual(response.json['error']['message'], 'Invalid kml file')
        self.assertEqual(response.content_type, "application/json")

    def test_update_non_existing_kml(self):

        id_to_update = base64.urlsafe_b64encode(uuid.uuid4().bytes).decode('utf8').replace('=', '')

        response = self.app.put(
            url_for('update_kml', kml_id=id_to_update),
            data=prepare_kml_payload(
                self.kml_dict["updated"], admin_id=self.sample_kml['admin_id']
            ),
            content_type="multipart/form-data",
            headers=self.origin_headers["allowed"]
        )
        self.assertEqual(response.status_code, 404)
        self.assertCors(response, ['PUT', 'OPTIONS'])
        self.assertEqual(
            response.json['error']['message'],
            f'Could not find {id_to_update} within the database.'
        )
        self.assertEqual(response.content_type, "application/json")

    def test_valid_kml_put_non_allowed_origin(self):
        id_to_put = self.sample_kml['id']
        response = self.app.put(
            url_for('update_kml', kml_id=id_to_put),
            data=prepare_kml_payload(
                self.kml_dict["updated"], admin_id=self.sample_kml['admin_id']
            ),
            content_type="multipart/form-data",
            headers=self.origin_headers["bad"]
        )
        self.assertEqual(response.status_code, 403)
        self.assertCors(response, ['PUT', 'OPTIONS'], check_origin=False)
        self.assertEqual(response.content_type, "application/json")
        self.assertEqual(response.json["error"]["message"], "Permission denied")

    def test_valid_kml_put_non_allowed_admin_id(self):
        id_to_put = self.sample_kml['id']
        response = self.app.put(
            url_for('update_kml', kml_id=id_to_put),
            data=prepare_kml_payload(self.kml_dict["updated"], admin_id='invalid-id'),
            content_type="multipart/form-data",
            headers=self.origin_headers["bad"]
        )
        self.assertEqual(response.status_code, 403)
        self.assertCors(response, ['PUT', 'OPTIONS'], check_origin=False)
        self.assertEqual(response.content_type, "application/json")
        self.assertEqual(response.json["error"]["message"], "Permission denied")

    def test_valid_kml_put_missing_admin_id(self):
        id_to_put = self.sample_kml['id']
        response = self.app.put(
            url_for('update_kml', kml_id=id_to_put),
            data=prepare_kml_payload(self.kml_dict["updated"]),
            content_type="multipart/form-data",
            headers=self.origin_headers["bad"]
        )
        self.assertEqual(response.status_code, 403)
        self.assertCors(response, ['PUT', 'OPTIONS'], check_origin=False)
        self.assertEqual(response.content_type, "application/json")
        self.assertEqual(response.json["error"]["message"], "Permission denied")


class TestDeleteEndpoint(BaseRouteTestCase):

    def test_kml_delete(self):
        id_to_delete = self.sample_kml['id']

        # retrieve the file_key for later check
        item = self.dynamodb.Table(AWS_DB_TABLE_NAME).get_item(Key={'kml_id': id_to_delete})['Item']

        response = self.app.delete(
            url_for('delete_kml', kml_id=id_to_delete),
            content_type='multipart/form-data',
            data=dict(admin_id=self.sample_kml['admin_id']),
            headers=self.origin_headers["allowed"]
        )
        self.assertEqual(response.status_code, 200)
        self.assertCors(response, ['DELETE', 'OPTIONS'])
        self.assertEqual(response.content_type, "application/json")

        response = self.app.get(
            f"/kml/admin/{id_to_delete}", headers=self.origin_headers["allowed"]
        )
        self.assertEqual(response.status_code, 404)

        # Make sure the file is deleted on S3
        file = self.get_s3_object(item['file_key'])
        self.assertIsNone(file, msg='kml file not deleted on S3')

    def test_kml_delete_id_nonexistent(self):
        id_to_delete = 'nonExistentId'
        response = self.app.delete(
            url_for('delete_kml', kml_id=id_to_delete),
            content_type='multipart/form-data',
            headers=self.origin_headers["allowed"]
        )

        self.assertEqual(response.status_code, 404)
        self.assertCors(response, ['DELETE', 'OPTIONS'])
        self.assertEqual(response.content_type, "application/json")
        self.assertEqual(
            response.json['error']['message'],
            f'Could not find {id_to_delete} within the database.'
        )

    def test_kml_delete_non_allowed_origin(self):
        id_to_delete = self.sample_kml['id']

        response = self.app.delete(
            url_for('delete_kml', kml_id=id_to_delete),
            data=dict(admin_id=self.sample_kml['admin_id']),
            content_type='multipart/form-data',
            headers=self.origin_headers["bad"]
        )
        self.assertEqual(response.status_code, 403)
        self.assertCors(response, ['DELETE', 'OPTIONS'], check_origin=False)
        self.assertEqual(response.content_type, "application/json")
        self.assertEqual(response.json["error"]["message"], "Permission denied")

    def test_kml_delete_non_allowed_admin_id(self):
        id_to_delete = self.sample_kml['id']

        response = self.app.delete(
            url_for('delete_kml', kml_id=id_to_delete),
            content_type='multipart/form-data',
            data=dict(admin_id='invalid-id'),
            headers=self.origin_headers["allowed"]
        )
        self.assertEqual(response.status_code, 403)
        self.assertCors(response, ['DELETE', 'OPTIONS'], check_origin=False)
        self.assertEqual(response.content_type, "application/json")
        self.assertEqual(response.json["error"]["message"], "Permission denied")

    def test_kml_delete_missing_admin_id(self):
        id_to_delete = self.sample_kml['id']

        response = self.app.delete(
            url_for('delete_kml', kml_id=id_to_delete),
            content_type='multipart/form-data',
            headers=self.origin_headers["allowed"]
        )
        self.assertEqual(response.status_code, 403)
        self.assertCors(response, ['DELETE', 'OPTIONS'], check_origin=False)
        self.assertEqual(response.content_type, "application/json")
        self.assertEqual(response.json["error"]["message"], "Permission denied")

    def test_kml_delete_wrong_content_type(self):
        id_to_delete = self.sample_kml['id']

        response = self.app.delete(
            url_for('delete_kml', kml_id=id_to_delete),
            content_type='application/json',
            data=dict(admin_id=self.sample_kml['admin_id']),
            headers=self.origin_headers["allowed"]
        )
        self.assertEqual(response.status_code, 415)
        self.assertCors(response, ['DELETE', 'OPTIONS'])
        self.assertEqual(response.content_type, "application/json")
        self.assertEqual(response.json["error"]["message"], "Unsupported Media Type")
