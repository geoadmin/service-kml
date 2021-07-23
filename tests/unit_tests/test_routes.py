import base64
import logging
import unittest
import uuid

from app import app
from app.version import APP_VERSION
from tests.unit_tests.base import BaseRouteTestCase

logger = logging.getLogger(__name__)


class CheckerTests(unittest.TestCase):

    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True

    def test_checker(self):
        response = self.app.get("/checker")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content_type, "application/json")
        self.assertEqual(response.json, {"message": "OK", "success": True, "version": APP_VERSION})


class TestPostEndpoint(BaseRouteTestCase):

    def test_valid_kml_post(self):
        response = self.app.post(
            "/kml", data=self.kml_string, content_type="application/vnd.google-earth.kml+xml"
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.content_type, "application/json")

    def test_invalid_kml_post(self):
        response = self.app.post(
            "/kml",
            data=self.kml_invalid_string,
            content_type="application/vnd.google-earth.kml+xml"
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json['error']['message'], 'Invalid kml file')
        self.assertEqual(response.content_type, "application/json")


class TestGetEndpoint(BaseRouteTestCase):

    def test_get_id(self):
        # first step: create a kml file to retrieve
        response = self.app.post(
            "/kml", data=self.kml_string, content_type="application/vnd.google-earth.kml+xml"
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.content_type, "application/json")

        # second step : fetch the id

        id_to_fetch = response.json['id']
        stored_geoadmin_link = response.json['links']['kml']
        stored_kml_admin_link = response.json['links']['self']

        # third step : test the get id endpoint

        response = self.app.get(f"/kml/{id_to_fetch}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content_type, "application/json")

        self.assertEqual(stored_geoadmin_link, response.json['links']['kml'])
        self.assertEqual(stored_kml_admin_link, response.json['links']['self'])

    def test_get_id_nonexistent(self):
        id_to_fetch = 'nonExistentId'
        response = self.app.get(f"kml/{id_to_fetch}")

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.content_type, "application/json")
        self.assertEqual(
            response.json['error']['message'], f'Could not find {id_to_fetch} within the database.'
        )


class TestPutEndpoint(BaseRouteTestCase):

    def test_valid_kml_put(self):

        response_post = self.app.post(
            "/kml", data=self.kml_string, content_type="application/vnd.google-earth.kml+xml"
        )
        self.assertEqual(response_post.status_code, 201)
        self.assertEqual(response_post.content_type, "application/json")

        id_to_put = response_post.json['id']

        response = self.app.put(
            f'/kml/{id_to_put}',
            data=self.new_kml_string,
            content_type="application/vnd.google-earth.kml+xml"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content_type, "application/json")
        for key in response_post.json:
            # values for "updated" should and may differ, so ignore them in
            # this assertion
            if key != "updated":
                self.assertEqual(response_post.json[key], response.json[key])

    def test_invalid_kml_put(self):

        response = self.app.post(
            "/kml", data=self.kml_string, content_type="application/vnd.google-earth.kml+xml"
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.content_type, "application/json")

        id_to_put = response.json['id']

        response = self.app.put(
            f'/kml/{id_to_put}',
            data=self.kml_invalid_string,
            content_type="application/vnd.google-earth.kml+xml"
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json['error']['message'], 'Invalid kml file')
        self.assertEqual(response.content_type, "application/json")

    def test_update_non_existing_kml(self):

        id_to_update = base64.urlsafe_b64encode(uuid.uuid4().bytes).decode('utf8').replace('=', '')

        response = self.app.put(
            f'/kml/{id_to_update}',
            data=self.new_kml_string,
            content_type="application/vnd.google-earth.kml+xml"
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
            "/kml", data=self.kml_string, content_type="application/vnd.google-earth.kml+xml"
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.content_type, "application/json")

        id_to_delete = response.json['id']

        response = self.app.delete(f"/kml/{id_to_delete}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content_type, "application/json")

        response = self.app.get(f"/kml/{id_to_delete}")
        self.assertEqual(response.status_code, 404)

    def test_delete_id_nonexistent(self):
        id_to_delete = 'nonExistentId'
        response = self.app.delete(f"kml/{id_to_delete}")

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.content_type, "application/json")
        self.assertEqual(
            response.json['error']['message'],
            f'Could not find {id_to_delete} within the database.'
        )
