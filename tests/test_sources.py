import json
import tempfile
import unittest
from pathlib import Path

from datahub_pg_loader.catalog import get_dataset
from datahub_pg_loader.sources import iter_records


class SourceTests(unittest.TestCase):
    def test_csv_limit(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "cities.csv"
            path.write_text("name,country\nTehran,Iran\nShiraz,Iran\n", encoding="utf-8")
            records = list(iter_records(get_dataset("world-cities"), path, 1))
        self.assertEqual(records, [{"name": "Tehran", "country": "Iran"}])

    def test_geojson_round_robin_and_nested_path(self):
        feature_collection = {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "properties": {
                        "name": "Alpha",
                        "ISO3166-1-Alpha-2": "AA",
                        "ISO3166-1-Alpha-3": "AAA",
                    },
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [[[1, 2], [3, 4], [1, 2]]],
                    },
                },
                {
                    "type": "Feature",
                    "properties": {
                        "name": "Beta",
                        "ISO3166-1-Alpha-2": "BB",
                        "ISO3166-1-Alpha-3": "BBB",
                    },
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [[[5, 6], [7, 8], [5, 6]]],
                    },
                },
            ],
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "countries.geojson"
            path.write_text(json.dumps(feature_collection), encoding="utf-8")
            records = list(iter_records(get_dataset("geo-countries"), path, 4))
        self.assertEqual([record["feature_key"] for record in records], ["AAA", "BBB", "AAA", "BBB"])
        self.assertEqual(records[0]["geometry_path"], [0, 0, 0])
        self.assertEqual(records[0]["coordinate"], [1, 2])
