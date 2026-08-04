from __future__ import annotations

import re
from collections.abc import Iterable

from .models import Dataset, PostgresConfig


IDENTIFIER_PATTERN = re.compile(r"^[a-z_][a-z0-9_]{0,62}$")


def validate_identifier(value: str) -> str:
    if not IDENTIFIER_PATTERN.fullmatch(value):
        raise ValueError(
            "PostgreSQL names must start with a lowercase letter or underscore and contain only "
            "lowercase letters, numbers, and underscores (maximum 63 characters)."
        )
    return value


def table_plan(table_name: str) -> str:
    validate_identifier(table_name)
    return f"""CREATE TABLE public.{table_name} (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    source_dataset TEXT NOT NULL,
    source_record_number BIGINT NOT NULL,
    payload JSONB NOT NULL,
    source_metadata JSONB NOT NULL,
    loaded_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (source_dataset, source_record_number)
);
CREATE INDEX {table_name}_payload_gin ON public.{table_name} USING GIN (payload);"""


def _imports():
    try:
        import psycopg
        from psycopg import sql
        from psycopg.types.json import Jsonb
    except ImportError as error:
        raise RuntimeError(
            "PostgreSQL support is not installed. Run: python -m pip install -e ."
        ) from error
    return psycopg, sql, Jsonb


def _connect(config: PostgresConfig, database: str | None = None, autocommit: bool = False):
    psycopg, _, _ = _imports()
    return psycopg.connect(
        host=config.host,
        port=config.port,
        user=config.user,
        password=config.password,
        dbname=database or config.database,
        connect_timeout=5,
        autocommit=autocommit,
    )


def database_exists(config: PostgresConfig) -> bool:
    with _connect(config, database="postgres") as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1 FROM pg_database WHERE datname = %s", (config.database,))
            return cursor.fetchone() is not None


def create_database(config: PostgresConfig) -> None:
    _, sql, _ = _imports()
    with _connect(config, database="postgres", autocommit=True) as connection:
        connection.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(config.database)))


def table_exists(config: PostgresConfig, table_name: str) -> bool:
    validate_identifier(table_name)
    with _connect(config) as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT to_regclass(%s)", (f"public.{table_name}",))
            return cursor.fetchone()[0] is not None


def load_records(
    config: PostgresConfig,
    table_name: str,
    dataset: Dataset,
    records: Iterable[dict],
    requested_records: int | None,
) -> int:
    _, sql, Jsonb = _imports()
    validate_identifier(table_name)
    metadata = Jsonb(
        {
            "provider": "DataHub",
            "dataset": dataset.key,
            "source_url": dataset.url,
            "format": dataset.file_format,
            "license": dataset.license_name,
            "record_mode": dataset.record_mode,
        }
    )
    table_identifier = sql.Identifier("public", table_name)
    index_identifier = sql.Identifier(f"{table_name}_payload_gin")

    with _connect(config) as connection:
        with connection.transaction():
            connection.execute(sql.SQL("DROP TABLE IF EXISTS {}").format(table_identifier))
            connection.execute(
                sql.SQL(
                    """CREATE TABLE {} (
                        id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                        source_dataset TEXT NOT NULL,
                        source_record_number BIGINT NOT NULL,
                        payload JSONB NOT NULL,
                        source_metadata JSONB NOT NULL,
                        loaded_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE (source_dataset, source_record_number)
                    )"""
                ).format(table_identifier)
            )
            connection.execute(
                sql.SQL("CREATE INDEX {} ON {} USING GIN (payload)").format(
                    index_identifier, table_identifier
                )
            )

            copy_sql = sql.SQL(
                "COPY {} (source_dataset, source_record_number, payload, source_metadata) FROM STDIN"
            ).format(table_identifier)
            count = 0
            with connection.cursor().copy(copy_sql) as copy:
                for count, record in enumerate(records, start=1):
                    copy.write_row((dataset.key, count, Jsonb(record), metadata))

            if requested_records is not None and count < requested_records:
                raise ValueError(
                    f"The source contains only {count:,} {dataset.record_mode}; "
                    f"{requested_records:,} were requested. No database changes were committed."
                )
    return count


def loaded_count(config: PostgresConfig, table_name: str) -> int:
    _, sql, _ = _imports()
    validate_identifier(table_name)
    with _connect(config) as connection:
        return connection.execute(
            sql.SQL("SELECT count(*) FROM {}").format(sql.Identifier("public", table_name))
        ).fetchone()[0]
