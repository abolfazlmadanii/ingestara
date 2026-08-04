from .models import Dataset


DATASETS = (
    Dataset(
        key="country-list",
        name="Country List",
        url="https://datahub.io/core/country-list/_r/-/data.csv",
        file_name="country-list.csv",
        file_format="CSV",
        description="ISO country names and two-letter codes",
        license_name="ODC-PDDL-1.0",
        estimated_records=249,
        field_count=2,
        nesting_depth=1,
        complexity_rank=1,
        record_mode="rows",
        default_table="datahub_country_list",
    ),
    Dataset(
        key="world-cities",
        name="World Cities",
        url="https://datahub.io/core/world-cities/_r/-/data/world-cities.csv",
        file_name="world-cities.csv",
        file_format="CSV",
        description="Major world cities with country and administrative area",
        license_name="CC-BY-4.0",
        estimated_records=None,
        field_count=4,
        nesting_depth=1,
        complexity_rank=2,
        record_mode="rows",
        default_table="datahub_world_cities",
    ),
    Dataset(
        key="airport-codes",
        name="Airport Codes",
        url="https://datahub.io/core/airport-codes/_r/-/data/airport-codes.csv",
        file_name="airport-codes.csv",
        file_format="CSV",
        description="Worldwide airports, facility types, codes, and coordinates",
        license_name="ODC-PDDL-1.0",
        estimated_records=None,
        field_count=12,
        nesting_depth=1,
        complexity_rank=3,
        record_mode="rows",
        default_table="datahub_airport_codes",
    ),
    Dataset(
        key="country-codes",
        name="Comprehensive Country Codes",
        url="https://datahub.io/core/country-codes/_r/-/data/country-codes.csv",
        file_name="country-codes.csv",
        file_format="CSV",
        description="Country identifiers from many international standards",
        license_name="ODC-PDDL-1.0",
        estimated_records=249,
        field_count=50,
        nesting_depth=1,
        complexity_rank=4,
        record_mode="rows",
        default_table="datahub_country_codes",
    ),
    Dataset(
        key="geo-countries",
        name="Country Polygons",
        url="https://datahub.io/core/geo-countries/_r/-/data/countries.geojson",
        file_name="countries.geojson",
        file_format="GeoJSON",
        description="Nested Polygon and MultiPolygon country boundaries",
        license_name="ODC-PDDL-1.0",
        estimated_records=548_472,
        field_count=9,
        nesting_depth=5,
        complexity_rank=5,
        record_mode="coordinates",
        default_table="datahub_country_boundary_points",
    ),
)


def get_dataset(key: str) -> Dataset:
    for dataset in DATASETS:
        if dataset.key == key:
            return dataset
    raise KeyError(f"Unknown dataset: {key}")
