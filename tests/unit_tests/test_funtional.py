import unittest

from app.helpers.utils import prevent_erroneous_kml


class TestValidateKmlString(unittest.TestCase):

    def test_kml_string_false(self):

        kml_string = """<script asdf="sadf">
        </script>"""
        kml = prevent_erroneous_kml(kml_string)
        self.assertEqual(kml, ' ')

    def test_kml_string_wrong(self):

        kml_string_w = """<root xmlns    = "https://www.exampel.ch/"</root>"""
        kml = prevent_erroneous_kml(kml_string_w)
        self.assertEqual(kml, """<root xmlns    = "https://www.exampel.ch/"</root>""")

        kml_string_w = """<script asdf="sadf">
        </script> <root xmlns    = "https://www.exampel.ch/"</root>"""
        kml = prevent_erroneous_kml(kml_string_w)
        self.assertEqual(kml, '  <root xmlns    = "https://www.exampel.ch/"</root>')
