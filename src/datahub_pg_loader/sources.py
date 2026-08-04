from __future__ import annotations

import csv
import json
from collections import deque
from collections.abc import Iterator
from pathlib import Path

from .models import Dataset


def _csv_records(path: Path) -> Iterator[dict]:
    with path.open(encoding="utf-8-sig", newline="") as source:
        reader = csv.DictReader(source)
        if not reader.fieldnames:
            raise ValueError("CSV source has no header")
        for row in reader:
            yield dict(row)


def _geometry_points(geometry: dict) -> Iterator[tuple[int, int, int, list]]:
    geometry_type = geometry.get("type")
    coordinates = geometry.get("coordinates")
    if geometry_type == "Polygon":
        polygons = [coordinates]
    elif geometry_type == "MultiPolygon":
        polygons = coordinates
    else:
        raise ValueError(f"Unsupported GeoJSON geometry: {geometry_type}")

    for polygon_index, polygon in enumerate(polygons):
        for ring_index, ring in enumerate(polygon):
            for coordinate_index, coordinate in enumerate(ring):
                yield polygon_index, ring_index, coordinate_index, coordinate


def _feature_key(properties: dict, feature_index: int) -> str:
    iso_alpha_3 = properties.get("ISO3166-1-Alpha-3")
    if iso_alpha_3 and iso_alpha_3 != "-99":
        return iso_alpha_3
    return f"feature-{feature_index:03d}"


def _geojson_records(path: Path) -> Iterator[dict]:
    with path.open(encoding="utf-8") as source:
        dataset = json.load(source)
    features = dataset.get("features", [])
    if dataset.get("type") != "FeatureCollection" or not features:
        raise ValueError("Expected a non-empty GeoJSON FeatureCollection")

    queues = deque()
    for feature_index, feature in enumerate(features):
        properties = feature.get("properties") or {}
        geometry = feature.get("geometry") or {}
        queues.append(
            (
                _feature_key(properties, feature_index),
                properties,
                geometry.get("type"),
                iter(_geometry_points(geometry)),
            )
        )

    while queues:
        feature_key, properties, geometry_type, points = queues.popleft()
        try:
            polygon_index, ring_index, coordinate_index, coordinate = next(points)
        except StopIteration:
            continue
        yield {
            "feature_key": feature_key,
            "country_name": properties.get("name") or feature_key,
            "iso_alpha_2": properties.get("ISO3166-1-Alpha-2"),
            "iso_alpha_3": properties.get("ISO3166-1-Alpha-3"),
            "geometry_type": geometry_type,
            "geometry_path": [polygon_index, ring_index, coordinate_index],
            "coordinate": coordinate,
            "properties": properties,
        }
        queues.append((feature_key, properties, geometry_type, points))


def iter_records(dataset: Dataset, path: Path, limit: int | None) -> Iterator[dict]:
    records = _geojson_records(path) if dataset.file_format == "GeoJSON" else _csv_records(path)
    for index, record in enumerate(records, start=1):
        if limit is not None and index > limit:
            return
        yield record
