import unittest

from app.helpers.utils import prevent_erroneous_kml
from app.helpers.utils import validate_kml_string


class TestValidateKmlString(unittest.TestCase):

    def test_kml_string_false(self):

        kml_string = """<script asdf="sadf">
        </script>"""
        kml = prevent_erroneous_kml(kml_string)
        self.assertEqual(kml, ' ')

    def test_kml_string_wrong(self):

        kml_string_w = """<root xmlns    = "https://www.example.ch/"</root>"""
        kml = prevent_erroneous_kml(kml_string_w)
        self.assertEqual(kml, """<root xmlns    = "https://www.example.ch/"</root>""")

        kml_string_w = """<script asdf="sadf">
        </script> <root xmlns    = "https://www.example.ch/"</root>"""
        kml = prevent_erroneous_kml(kml_string_w)
        self.assertEqual(kml, '  <root xmlns    = "https://www.example.ch/"</root>')

    def test_empty_kml(self):
        for kml_string in ['<kml></kml>', '<kml/>', ' <kml >  </kml > ', r' <kml > \n\n</kml  > ']:
            with self.subTest(kml_string=kml_string):
                kml, empty = validate_kml_string(kml_string)
                self.assertTrue(empty, msg=f'{kml_string} is not marked as empty')

    def test_non_empty_kml(self):
        for kml_string in [
            '<kml>test</kml>',
            '<kml attribute="value"/>',
            '<kml><sub-element/></kml>',
            r'<kml>\n<sub-element></sub-element>\n</kml>',
            r'<kml>\n<sub-element>Test</sub-element>\n</kml>',
            r'<kml>\n<sub-element><sub-sub/>Test</sub-element>\n</kml>'
        ]:
            with self.subTest(kml_string=kml_string):
                kml, empty = validate_kml_string(kml_string)
                self.assertFalse(empty, msg=f'{kml_string} is marked as empty')
