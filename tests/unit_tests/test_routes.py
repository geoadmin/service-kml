import base64
import datetime
import logging
import uuid
from datetime import timedelta

from app.settings import AWS_DB_TABLE_NAME
from app.version import APP_VERSION
from tests.unit_tests.base import BaseRouteTestCase

logger = logging.getLogger(__name__)


class CheckerTests(BaseRouteTestCase):

    def test_checker(self):
        response = self.app.get("/checker", headers=self.origin_headers["allowed"])
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content_type, "application/json")
        self.assertEqual(response.json, {"message": "OK", "success": True, "version": APP_VERSION})

    def test_checker_non_allowed_origin(self):
        response = self.app.get("/checker", headers=self.origin_headers["bad"])
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.content_type, "application/json")
        self.assertEqual(response.json["error"]["message"], "Not allowed")


class TestPostEndpoint(BaseRouteTestCase):

    def test_valid_kml_post(self):
        response = self.app.post(
            "/kml",
            data=self.kml_dict["valid"],
            content_type="application/vnd.google-earth.kml+xml",
            headers=self.origin_headers["allowed"]
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.content_type, "application/json")
        self.compare_kml_contents(response, self.kml_dict["valid"])

    def test_invalid_kml_post(self):
        response = self.app.post(
            "/kml",
            data=self.kml_dict["invalid"],
            content_type="application/vnd.google-earth.kml+xml",
            headers=self.origin_headers["allowed"]
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json['error']['message'], 'Invalid kml file')
        self.assertEqual(response.content_type, "application/json")

    def test_valid_kml_post_non_allowed_origin(self):
        response = self.app.post(
            "/kml",
            data=self.kml_dict["valid"],
            content_type="application/vnd.google-earth.kml+xml",
            headers=self.origin_headers["bad"]
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.content_type, "application/json")
        self.assertEqual(response.json["error"]["message"], "Not allowed")


class TestGetEndpoint(BaseRouteTestCase):

    def test_get_id(self):
        id_to_fetch = self.sample_kml['id']
        stored_geoadmin_link = self.sample_kml['links']['kml']
        stored_kml_admin_link = self.sample_kml['links']['self']
        response = self.app.get(f"/kml/{id_to_fetch}", headers=self.origin_headers["allowed"])
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content_type, "application/json")
        self.assertEqual(stored_geoadmin_link, response.json['links']['kml'])
        self.assertEqual(stored_kml_admin_link, response.json['links']['self'])

    def test_get_id_nonexistent(self):
        id_to_fetch = 'nonExistentId'
        response = self.app.get(f"kml/{id_to_fetch}", headers=self.origin_headers["allowed"])
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.content_type, "application/json")
        self.assertEqual(
            response.json['error']['message'], f'Could not find {id_to_fetch} within the database.'
        )


class TestPutEndpoint(BaseRouteTestCase):

    def test_valid_kml_put(self):
        id_to_put = self.sample_kml['id']
        response = self.app.put(
            f'/kml/{id_to_put}',
            data=self.kml_dict["updated"],
            content_type="application/vnd.google-earth.kml+xml",
            headers=self.origin_headers["allowed"]
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content_type, "application/json")
        for key in self.sample_kml:
            # values for "updated" should and may differ, so ignore them in
            # this assertion
            if key != "updated":
                self.assertEqual(self.sample_kml[key], response.json[key])

        updated_item = self.dynamodb.Table(AWS_DB_TABLE_NAME).get_item(Key={
            'admin_id': id_to_put
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
            f'/kml/{id_to_put}',
            data=self.kml_dict["invalid"],
            content_type="application/vnd.google-earth.kml+xml",
            headers=self.origin_headers["allowed"]
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json['error']['message'], 'Invalid kml file')
        self.assertEqual(response.content_type, "application/json")

    def test_update_non_existing_kml(self):

        id_to_update = base64.urlsafe_b64encode(uuid.uuid4().bytes).decode('utf8').replace('=', '')

        response = self.app.put(
            f'/kml/{id_to_update}',
            data=self.kml_dict["updated"],
            content_type="application/vnd.google-earth.kml+xml",
            headers=self.origin_headers["allowed"]
        )
        self.assertEqual(response.status_code, 404)
        self.assertEqual(
            response.json['error']['message'],
            f'Could not find {id_to_update} within the database.'
        )
        self.assertEqual(response.content_type, "application/json")


class TestDeleteEndpoint(BaseRouteTestCase):

    def test_delete_endpoint(self):
        response = self.app.post(
            "/kml",
            data=self.kml_dict["valid"],
            content_type="application/vnd.google-earth.kml+xml",
            headers=self.origin_headers["allowed"]
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.content_type, "application/json")
        self.compare_kml_contents(response, self.kml_dict["valid"])

        id_to_delete = response.json['id']

        response = self.app.delete(f"/kml/{id_to_delete}", headers=self.origin_headers["allowed"])
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content_type, "application/json")

        response = self.app.get(f"/kml/{id_to_delete}", headers=self.origin_headers["allowed"])
        self.assertEqual(response.status_code, 404)

    def test_delete_id_nonexistent(self):
        id_to_delete = 'nonExistentId'
        response = self.app.delete(f"kml/{id_to_delete}", headers=self.origin_headers["allowed"])

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.content_type, "application/json")
        self.assertEqual(
            response.json['error']['message'],
            f'Could not find {id_to_delete} within the database.'
        )
