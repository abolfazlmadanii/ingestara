import unittest

from datahub_pg_loader.network import estimate_seconds, format_bytes, format_duration


class NetworkTests(unittest.TestCase):
    def test_estimate_seconds(self):
        self.assertEqual(estimate_seconds(10_000, 2_000), 5)
        self.assertIsNone(estimate_seconds(None, 2_000))

    def test_human_readable_formatting(self):
        self.assertEqual(format_bytes(1024), "1.0 KB")
        self.assertEqual(format_duration(90), "1m 30s")
