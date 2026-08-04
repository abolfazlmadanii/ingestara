from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Dataset:
    key: str
    name: str
    url: str
    file_name: str
    file_format: str
    description: str
    license_name: str
    estimated_records: int | None
    field_count: int
    nesting_depth: int
    complexity_rank: int
    record_mode: str
    default_table: str

    def cache_path(self, cache_directory: Path) -> Path:
        return cache_directory / self.key / self.file_name


@dataclass(frozen=True)
class RemoteStats:
    available: bool
    size_bytes: int | None
    error: str | None = None


@dataclass(frozen=True)
class SpeedStats:
    bytes_per_second: float
    sampled_bytes: int
    elapsed_seconds: float


@dataclass(frozen=True)
class PostgresConfig:
    host: str
    port: int
    user: str
    password: str
    database: str
