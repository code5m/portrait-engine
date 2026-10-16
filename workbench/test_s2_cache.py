"""Synthetic cache-corruption tests, not new S2 visual evidence."""
import copy
import math
import unittest
from check_s2_cache import assert_signature


class CacheSignatureTests(unittest.TestCase):
    def setUp(self):
        self.record = {'geometryHash': 'a' * 64, 'weights': [.1, .2, 0., 0., 0., 0.],
                       'camera': {'center': [0., -1.2171], 'span': 36.16014},
                       'nonAffineRMS': .0017347984872785468, 'surfaceOnly': True}

    def test_identity_and_last_bit_diagnostic_variation(self):
        self.assertEqual(assert_signature(self.record, self.record), 0)
        other = copy.deepcopy(self.record)
        other['nonAffineRMS'] = math.nextafter(other['nonAffineRMS'], math.inf)
        self.assertGreater(assert_signature(other, self.record), 0)

    def test_every_actual_geometry_field_remains_exact(self):
        for field, value in [('geometryHash', 'b' * 64), ('weights', [.11, .2, 0., 0., 0., 0.]),
                             ('camera', {'center': [0., -1.2171], 'span': 36.16015}), ('surfaceOnly', False)]:
            with self.subTest(field=field):
                other = {**self.record, field: value}
                with self.assertRaisesRegex(AssertionError, 'exact geometry field'):
                    assert_signature(other, self.record)

    def test_substantive_invalid_or_missing_diagnostics_fail(self):
        for value in [.0018, float('nan'), float('inf'), -.001, True, '0.001']:
            with self.subTest(value=value):
                with self.assertRaises(AssertionError):
                    assert_signature({**self.record, 'nonAffineRMS': value}, self.record)
        for other in [{k: v for k, v in self.record.items() if k != 'geometryHash'}, {**self.record, 'extra': 1}]:
            with self.assertRaises(AssertionError):
                assert_signature(other, self.record)


if __name__ == '__main__':
    unittest.main()
