import unittest

from app import app
from app.version import APP_VERSION


class CheckerTests(unittest.TestCase):

    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True

    def test_checker(self):
        response = self.app.get("/checker")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content_type, "application/json")
        self.assertEqual(response.json, {"message": "OK", "success": True, "version": APP_VERSION})


class PostTests(unittest.TestCase):

    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True

    def test_post(self):
        xml_file = """<root xmlns    = "https://www.exampel.ch/"
        xmlns:py = "https://www.exampel.ch/">
        <py:elem1 />
        <elem2 xmlns="" />
        </root>"""
        response = self.app.post(
            "/kml", data=xml_file, content_type="application/vnd.google-earth.kml+xml"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content_type, "application/json")
        self.assertEqual(response.json, {"message": "OK", "success": True, "version": APP_VERSION})

        xml_file_false = """Hi <root xmlns    = "https://www.exampel.ch/"
        xmlns:py = "https://www.exampel.ch/">
        <py:elem1 />
        <elem2 xmlns="" />
        </root>"""
        response = self.app.post(
            "/kml", data=xml_file_false, content_type="application/vnd.google-earth.kml+xml"
        )
        self.assertEqual(response.status_code, 400)
