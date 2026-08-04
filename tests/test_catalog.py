import unittest

from datahub_pg_loader.catalog import DATASETS, get_dataset


class CatalogTests(unittest.TestCase):
    def test_dataset_keys_and_tables_are_unique(self):
        self.assertEqual(len({dataset.key for dataset in DATASETS}), len(DATASETS))
        self.assertEqual(len({dataset.default_table for dataset in DATASETS}), len(DATASETS))

    def test_complexity_ranks_are_bounded(self):
        self.assertTrue(all(1 <= dataset.complexity_rank <= 5 for dataset in DATASETS))

    def test_nested_geojson_is_highest_complexity(self):
        dataset = get_dataset("geo-countries")
        self.assertEqual(dataset.file_format, "GeoJSON")
        self.assertEqual(dataset.complexity_rank, 5)
        self.assertEqual(dataset.record_mode, "coordinates")
