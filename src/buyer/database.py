"""Validated PostgreSQL connection settings for Immowbot."""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Mapping

from psycopg.conninfo import conninfo_to_dict, make_conninfo


DATABASE_NAME = "immotool"
DATABASE_USER = "immotool"
LOCAL_SOCKET_DIR = "/var/run/postgresql"


@dataclass(frozen=True)
class DatabaseSettings:
    mode: Literal["local", "remote"]
    dsn: str


def _required_mode(environ: Mapping[str, str]) -> Literal["local", "remote"]:
    mode = environ.get("DATABASE_MODE")
    if mode not in {"local", "remote"}:
        raise ValueError("DATABASE_MODE must be 'local' or 'remote'")
    return mode


def _local_settings(environ: Mapping[str, str]) -> DatabaseSettings:
    socket_dir = environ.get("DATABASE_SOCKET_DIR", LOCAL_SOCKET_DIR)
    socket_path = Path(socket_dir)
    if not socket_path.is_absolute() or socket_path.is_symlink():
        raise ValueError("DATABASE_SOCKET_DIR must be an absolute non-symlink path")
    kwargs = {
        "host": str(socket_path),
        "dbname": DATABASE_NAME,
        "user": DATABASE_USER,
    }
    if password := environ.get("DATABASE_PASSWORD"):
        kwargs["password"] = password
    return DatabaseSettings("local", make_conninfo(**kwargs))


def _remote_settings(environ: Mapping[str, str]) -> DatabaseSettings:
    raw_dsn = environ.get("DATABASE_DSN")
    if not raw_dsn:
        raise ValueError("DATABASE_DSN is required when DATABASE_MODE=remote")
    try:
        params = conninfo_to_dict(raw_dsn)
    except Exception as exc:
        raise ValueError("DATABASE_DSN is not a valid PostgreSQL connection string") from exc
    if params.get("host") != "kodisrv":
        raise ValueError("remote database host must be kodisrv")
    if params.get("dbname") != DATABASE_NAME or params.get("user") != DATABASE_USER:
        raise ValueError("remote database must use immotool database and user")
    if params.get("sslmode") != "verify-full":
        raise ValueError("remote database requires sslmode=verify-full")
    ca_path = Path(params.get("sslrootcert", ""))
    if not ca_path.is_absolute() or not ca_path.is_file() or ca_path.is_symlink():
        raise ValueError("remote database requires an absolute regular sslrootcert file")
    return DatabaseSettings("remote", make_conninfo(**params))


def load_database_settings(environ: Mapping[str, str] | None = None) -> DatabaseSettings:
    """Return validated PostgreSQL settings without logging credential material."""
    values = os.environ if environ is None else environ
    mode = _required_mode(values)
    return _local_settings(values) if mode == "local" else _remote_settings(values)
