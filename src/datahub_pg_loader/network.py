from __future__ import annotations

import socket
import time
import urllib.request
from pathlib import Path
from typing import Callable

from .models import RemoteStats, SpeedStats


USER_AGENT = "datahub-postgres-loader/1.0"


def _request(url: str, method: str = "GET", headers: dict[str, str] | None = None):
    request_headers = {"User-Agent": USER_AGENT}
    request_headers.update(headers or {})
    return urllib.request.Request(url, method=method, headers=request_headers)


def inspect_remote(url: str, timeout: float = 15) -> RemoteStats:
    try:
        with urllib.request.urlopen(_request(url, method="HEAD"), timeout=timeout) as response:
            size = response.headers.get("Content-Length")
            return RemoteStats(True, int(size) if size else None)
    except Exception as head_error:
        try:
            with urllib.request.urlopen(
                _request(url, headers={"Range": "bytes=0-0"}), timeout=timeout
            ) as response:
                content_range = response.headers.get("Content-Range", "")
                size_text = content_range.rsplit("/", 1)[-1]
                size = int(size_text) if size_text.isdigit() else None
                return RemoteStats(True, size)
        except Exception as range_error:
            return RemoteStats(False, None, f"{head_error}; {range_error}")


def measure_speed(url: str, sample_bytes: int = 1_048_576, timeout: float = 30) -> SpeedStats:
    started = time.monotonic()
    bytes_read = 0
    with urllib.request.urlopen(
        _request(url, headers={"Range": f"bytes=0-{sample_bytes - 1}"}), timeout=timeout
    ) as response:
        while bytes_read < sample_bytes:
            chunk = response.read(min(65_536, sample_bytes - bytes_read))
            if not chunk:
                break
            bytes_read += len(chunk)
    elapsed = max(time.monotonic() - started, 0.001)
    return SpeedStats(bytes_read / elapsed, bytes_read, elapsed)


def estimate_seconds(size_bytes: int | None, bytes_per_second: float) -> float | None:
    if size_bytes is None or bytes_per_second <= 0:
        return None
    return size_bytes / bytes_per_second


def tcp_available(host: str, port: int, timeout: float = 2) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def download(
    url: str,
    destination: Path,
    progress: Callable[[int], None] | None = None,
    timeout: float = 120,
) -> int:
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".part")
    downloaded = 0
    try:
        with urllib.request.urlopen(_request(url), timeout=timeout) as response, temporary.open("wb") as output:
            while True:
                chunk = response.read(1_048_576)
                if not chunk:
                    break
                output.write(chunk)
                downloaded += len(chunk)
                if progress:
                    progress(downloaded)
        temporary.replace(destination)
        return downloaded
    except Exception:
        temporary.unlink(missing_ok=True)
        raise


def format_bytes(value: int | float | None) -> str:
    if value is None:
        return "unknown"
    size = float(value)
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024 or unit == "GB":
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} GB"


def format_duration(seconds: float | None) -> str:
    if seconds is None:
        return "unknown"
    if seconds < 1:
        return "<1 second"
    if seconds < 60:
        return f"{seconds:.1f} seconds"
    minutes, remainder = divmod(seconds, 60)
    return f"{int(minutes)}m {int(remainder)}s"
