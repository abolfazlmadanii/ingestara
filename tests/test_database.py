import unittest

from datahub_pg_loader.database import table_plan, validate_identifier


class DatabaseTests(unittest.TestCase):
    def test_accepts_safe_identifier(self):
        self.assertEqual(validate_identifier("datahub_world_cities"), "datahub_world_cities")

    def test_rejects_unsafe_identifier(self):
        for value in ("Public.Table", "bad-name", "table;drop", "9table"):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    validate_identifier(value)

    def test_table_plan_includes_jsonb_and_gin(self):
        plan = table_plan("datahub_records")
        self.assertIn("payload JSONB", plan)
        self.assertIn("USING GIN", plan)
