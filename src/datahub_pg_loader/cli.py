from __future__ import annotations

import argparse
import getpass
import os
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from .catalog import DATASETS, get_dataset
from .database import (
    create_database,
    database_exists,
    load_records,
    loaded_count,
    table_exists,
    table_plan,
    validate_identifier,
)
from .models import PostgresConfig
from .network import (
    download,
    estimate_seconds,
    format_bytes,
    format_duration,
    inspect_remote,
    measure_speed,
    tcp_available,
)
from .sources import iter_records


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Discover DataHub datasets, estimate transfer time, and load JSONB records into PostgreSQL."
    )
    parser.add_argument("--list", action="store_true", help="List remote datasets and exit")
    parser.add_argument("--dataset", choices=[dataset.key for dataset in DATASETS])
    parser.add_argument("--records", help="Number of records to load, or 'all'")
    parser.add_argument("--host", default="localhost")
    parser.add_argument("--port", type=int, default=5432)
    parser.add_argument("--user", default="postgres")
    parser.add_argument("--database")
    parser.add_argument("--table")
    parser.add_argument("--cache-dir", type=Path, default=Path(".cache/datahub"))
    parser.add_argument("--refresh", action="store_true", help="Download even when a cached file exists")
    parser.add_argument("--yes", action="store_true", help="Approve the displayed plan without prompting")
    return parser.parse_args(argv)


def prompt(text: str, default: str | None = None) -> str:
    suffix = f" [{default}]" if default is not None else ""
    answer = input(f"{text}{suffix}: ").strip()
    return answer or (default or "")


def confirm(text: str, assume_yes: bool = False) -> bool:
    if assume_yes:
        print(f"{text} yes (--yes)")
        return True
    return input(f"{text} [y/N]: ").strip().lower() in {"y", "yes"}


def discover():
    print("\nAvailable DataHub datasets")
    print("=" * 112)
    with ThreadPoolExecutor(max_workers=len(DATASETS)) as executor:
        stats = list(executor.map(lambda dataset: inspect_remote(dataset.url), DATASETS))
    print(
        f"{'#':<3} {'Key':<16} {'Dataset':<29} {'Status':<10} {'Size':<11} "
        f"{'Records':<12} {'Fields':<7} {'Depth':<7} {'Rank'}"
    )
    for index, (dataset, remote) in enumerate(zip(DATASETS, stats), start=1):
        records = f"~{dataset.estimated_records:,}" if dataset.estimated_records else "on download"
        status = "available" if remote.available else "offline"
        print(
            f"{index:<3} {dataset.key:<16} {dataset.name:<29} {status:<10} "
            f"{format_bytes(remote.size_bytes):<11} {records:<12} {dataset.field_count:<7} "
            f"{dataset.nesting_depth:<7} {dataset.complexity_rank}/5"
        )
    print("\nComplexity rank combines field count, nesting depth, geometry, and parsing work (1=low, 5=high).")
    return {dataset.key: remote for dataset, remote in zip(DATASETS, stats)}


def choose_dataset(argument: str | None):
    if argument:
        return get_dataset(argument)
    choice = prompt("Choose a dataset by number or key")
    if choice.isdigit() and 1 <= int(choice) <= len(DATASETS):
        return DATASETS[int(choice) - 1]
    return get_dataset(choice)


def choose_record_limit(value: str | None, record_mode: str) -> int | None:
    answer = value or prompt(f"How many {record_mode} should be loaded? Enter a number or 'all'", "10000")
    if answer.lower() == "all":
        return None
    count = int(answer)
    if count <= 0:
        raise ValueError("Record count must be greater than zero")
    return count


def print_transfer_stats(dataset, remote):
    print(f"\nTesting download speed against {dataset.name}...")
    speed = measure_speed(dataset.url)
    megabits = speed.bytes_per_second * 8 / 1_000_000
    eta = estimate_seconds(remote.size_bytes, speed.bytes_per_second)
    print(f"Measured speed: {megabits:.2f} Mbps ({format_bytes(speed.bytes_per_second)}/s)")
    print(f"Source size:    {format_bytes(remote.size_bytes)}")
    print(f"Estimated time: {format_duration(eta)} (network transfer only)")


def password_for_user() -> str:
    environment_password = os.environ.get("PGPASSWORD")
    if environment_password is not None:
        return environment_password
    return getpass.getpass("PostgreSQL password: ")


def execute(args) -> int:
    print("DataHub PostgreSQL Loader")
    remote_by_key = discover()
    if args.list:
        return 0

    dataset = choose_dataset(args.dataset)
    remote = remote_by_key[dataset.key]
    if not remote.available:
        raise RuntimeError(f"Dataset is unavailable: {remote.error}")
    record_limit = choose_record_limit(args.records, dataset.record_mode)
    print_transfer_stats(dataset, remote)

    print(f"\nChecking PostgreSQL at {args.host}:{args.port}...")
    if not tcp_available(args.host, args.port):
        raise RuntimeError(
            f"No PostgreSQL server is reachable at {args.host}:{args.port}. Start PostgreSQL and retry."
        )
    print("Local PostgreSQL port is reachable.")

    database_name = args.database or prompt("PostgreSQL database name", "inventory")
    table_name = validate_identifier(args.table or prompt("Target table name", dataset.default_table))
    validate_identifier(database_name)
    requested_text = "all available" if record_limit is None else f"{record_limit:,}"
    print("\nLoad plan")
    print("=" * 72)
    print(f"Dataset:  {dataset.name} ({dataset.file_format}, complexity {dataset.complexity_rank}/5)")
    print(f"Records:  {requested_text} {dataset.record_mode}")
    print(f"Database: {args.user}@{args.host}:{args.port}/{database_name}")
    print(f"Table:    public.{table_name} (created or replaced atomically)")
    print("\nPlanned table schema:\n")
    print(table_plan(table_name))
    if not confirm("Approve database connection, table replacement, download, and load?", args.yes):
        print("Cancelled before connecting or changing PostgreSQL.")
        return 1

    config = PostgresConfig(
        host=args.host,
        port=args.port,
        user=args.user,
        password=password_for_user(),
        database=database_name,
    )
    if not database_exists(config):
        print(f"Database {database_name!r} does not exist; creating it under the approved plan.")
        create_database(config)
    else:
        print(f"Database {database_name!r} exists.")

    cached_file = dataset.cache_path(args.cache_dir)
    if args.refresh or not cached_file.exists():
        print(f"Downloading {dataset.url}")
        downloaded = download(
            dataset.url,
            cached_file,
            progress=lambda byte_count: print(
                f"\rDownloaded {format_bytes(byte_count)}", end="", flush=True
            ),
        )
        print(f"\rDownloaded {format_bytes(downloaded)} to {cached_file}")
    else:
        print(f"Using cached source file: {cached_file}")

    replacement = "existing" if table_exists(config, table_name) else "new"
    print(f"Loading into {replacement} table public.{table_name}...")
    inserted = load_records(
        config,
        table_name,
        dataset,
        iter_records(dataset, cached_file, record_limit),
        record_limit,
    )
    verified = loaded_count(config, table_name)
    if inserted != verified:
        raise RuntimeError(f"Verification failed: inserted {inserted:,}, table contains {verified:,}")

    print("\nSYSTEM COMPLETE")
    print(f"Loaded and verified {verified:,} records in {database_name}.public.{table_name}.")
    return 0


def main(argv=None):
    try:
        raise SystemExit(execute(parse_args(argv)))
    except (EOFError, KeyboardInterrupt):
        print("\nCancelled.", file=sys.stderr)
        raise SystemExit(130)
    except Exception as error:
        print(f"\nERROR: {error}", file=sys.stderr)
        raise SystemExit(1)
