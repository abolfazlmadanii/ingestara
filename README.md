# DataHub PostgreSQL Loader

An interactive Python package that discovers public DataHub datasets, reports their availability and complexity, measures current download speed, estimates transfer time, checks local PostgreSQL, asks for one explicit approval, and atomically loads the selected records as queryable `JSONB`.

## Workflow

The CLI always follows this order:

1. Checks which configured DataHub files are currently downloadable.
2. Displays format, live size, estimated records, fields, nesting depth, and complexity rank.
3. Asks which dataset and how many records to load (`all` is supported).
4. Measures download speed against that source and estimates transfer time.
5. Checks whether PostgreSQL is reachable locally.
6. Asks for database and table names and displays the exact table plan.
7. Requests approval before connecting, creating/replacing a table, downloading, or loading.
8. Checks whether the database exists and creates it when necessary under the approved plan.
9. Downloads or reuses the cached source and loads it in one PostgreSQL transaction.
10. Verifies the row count and prints `SYSTEM COMPLETE`.

If parsing, record validation, or insertion fails, the transaction rolls back and the existing table and its data remain unchanged. An approved successful run replaces the target table so incompatible older schemas cannot corrupt the load.

## Requirements

- Python 3.9 or newer
- A reachable PostgreSQL server
- A PostgreSQL role allowed to connect, create a database when needed, and create tables
- Internet access to DataHub

## Installation

Create an isolated environment and install the package:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .
```

Set the password without placing it in command history:

```bash
export PGPASSWORD='your-local-password'
```

If `PGPASSWORD` is not set, the CLI asks securely after approval.

## Run

Start the complete interactive workflow:

```bash
datahub-pg-load
```

From a source checkout, the compatibility script runs the same package:

```bash
python3 scripts/load-datahub.py
```

Only inspect currently available data:

```bash
datahub-pg-load --list
```

## Included Datasets

| Key | Dataset | Format | Record unit | Complexity |
| --- | --- | --- | --- | --- |
| `country-list` | ISO country list | CSV | row | 1/5 |
| `world-cities` | Major world cities | CSV | row | 2/5 |
| `airport-codes` | Worldwide airport codes | CSV | row | 3/5 |
| `country-codes` | Comprehensive country identifiers | CSV | row | 4/5 |
| `geo-countries` | Country Polygon/MultiPolygon boundaries | GeoJSON | coordinate | 5/5 |

The source catalog uses stable DataHub raw-file links. Complexity combines field count, nesting depth, geometry, and parsing work; it is not a data-quality score.

## PostgreSQL Model

Each selected dataset gets one table:

```sql
CREATE TABLE public.<selected_table> (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    source_dataset TEXT NOT NULL,
    source_record_number BIGINT NOT NULL,
    payload JSONB NOT NULL,
    source_metadata JSONB NOT NULL,
    loaded_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (source_dataset, source_record_number)
);
```

A GIN index on `payload` supports nested JSON queries. The loader validates PostgreSQL identifiers and uses Psycopg SQL identifiers rather than interpolating untrusted names.

## Development

```bash
make install
make list
make test
```

See [COOKBOOK.md](COOKBOOK.md) for interactive and automated recipes, PostgreSQL queries, caching behavior, and troubleshooting.

## Data Sources

- [Country list](https://datahub.io/core/country-list)
- [World cities](https://datahub.io/core/world-cities)
- [Airport codes](https://datahub.io/core/airport-codes)
- [Comprehensive country codes](https://datahub.io/core/country-codes)
- [Country polygons](https://datahub.io/core/geo-countries)

Review each linked dataset page for its current source, attribution, and license details before redistribution.
