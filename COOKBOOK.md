# DataHub PostgreSQL Loader Cookbook

Practical recipes for discovering, downloading, and loading DataHub data into local PostgreSQL.

## 1. First-Time Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
export PGPASSWORD='postgres'
```

Confirm PostgreSQL is listening:

```bash
pg_isready -h localhost -p 5432
```

## 2. Guided Interactive Load

```bash
datahub-pg-load
```

The command presents live dataset statistics, asks for a dataset and record count, measures speed, estimates download time, checks PostgreSQL, prints the table schema, and waits for approval. No connection or database change occurs before approval.

Recommended first choices:

- Quick smoke test: `country-list`, `all` records.
- Medium relational dataset: `world-cities`, `10000` records.
- Wide CSV: `airport-codes`, `10000` records.
- Complex nested data: `geo-countries`, `10000` coordinates.

## 3. List Sources Without Loading

```bash
datahub-pg-load --list
```

`Status` and `Size` are checked live. `Records` is an estimate when known; the loader validates the requested count against the downloaded file before committing.

## 4. Load 10,000 Nested GeoJSON Coordinates

```bash
datahub-pg-load \
  --dataset geo-countries \
  --records 10000 \
  --database inventory \
  --table datahub_country_boundary_points
```

The GeoJSON parser distributes coordinate records across all country features in round-robin order. Each `payload` retains the country properties, geometry type, nested geometry path, and coordinate array.

## 5. Load All Airport Rows

```bash
datahub-pg-load \
  --dataset airport-codes \
  --records all \
  --database inventory \
  --table datahub_airports
```

## 6. Non-Interactive Automation

Provide every selection and use `--yes` only after reviewing the same plan interactively once:

```bash
PGPASSWORD='postgres' datahub-pg-load \
  --dataset world-cities \
  --records 10000 \
  --host localhost \
  --port 5432 \
  --user postgres \
  --database inventory \
  --table datahub_world_cities \
  --yes
```

The command still performs discovery, speed measurement, database checks, atomic loading, and row-count verification.

## 7. Force a Fresh Download

Downloaded files are cached under `.cache/datahub/<dataset>/`.

```bash
datahub-pg-load --dataset world-cities --records 10000 --refresh
```

Delete cached downloads with:

```bash
make clean
```

## 8. Query Loaded Data

Count records:

```sql
SELECT count(*) FROM public.datahub_country_boundary_points;
```

Inspect source information:

```sql
SELECT source_dataset, source_metadata, loaded_at
FROM public.datahub_country_boundary_points
LIMIT 1;
```

Query nested country fields:

```sql
SELECT
    payload->>'country_name' AS country,
    payload->'coordinate' AS coordinate,
    payload->'geometry_path' AS geometry_path
FROM public.datahub_country_boundary_points
ORDER BY id
LIMIT 10;
```

Filter with the JSONB GIN index:

```sql
SELECT count(*)
FROM public.datahub_country_boundary_points
WHERE payload @> '{"iso_alpha_3":"IRN"}';
```

Inspect a CSV payload:

```sql
SELECT payload
FROM public.datahub_world_cities
WHERE payload->>'country' = 'Iran'
LIMIT 10;
```

## 9. Use Another Local Port

```bash
datahub-pg-load --host 127.0.0.1 --port 55432
```

The package first checks TCP reachability. Authentication and database existence are checked only after approval.

## 10. Failure and Recovery

### PostgreSQL is not reachable

Start the local server and verify the host/port:

```bash
pg_isready -h localhost -p 5432
```

### Authentication fails

Check `--user`, `PGPASSWORD`, and `pg_hba.conf`. The package never stores the password.

### Requested count exceeds available records

The loader raises an error and rolls back the transaction. Retry with a lower count or `--records all`.

### Interrupted download

Partial files use a `.part` suffix and are deleted after failure. Retry normally.

### Existing table must remain untouched

Do not approve the displayed plan. The package exits before connecting. During an approved load, the table drop, recreation, and inserts happen in one transaction, so parser and insertion errors restore the prior table and data.
