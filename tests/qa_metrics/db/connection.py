#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""psycopg connection wrapper for the QA Metabase postgres."""

import logging
import os
from pathlib import Path
from typing import Any, Literal, Self

import psycopg

logger = logging.getLogger(__name__)

type SslMode = Literal["disable", "allow", "prefer", "require", "verify-ca", "verify-full"]


class MetabasePostgres:
    """psycopg connection wrapper.

    The constructor is a pure passthrough — no environment is consulted. Use
    :meth:`from_env` for the conventional env-driven entry point.

    Auth precedence: an explicit ``password`` wins; otherwise the SSL
    client-cert trio is used.
    """

    def __init__(
        self,
        host: str,
        port: int,
        dbname: str,
        user: str,
        sslrootcert: Path | None = None,
        sslcert: Path | None = None,
        sslkey: Path | None = None,
        sslmode: SslMode = "allow",
        password: str | None = None,
    ) -> None:
        self.host = host
        self.port = port
        self.dbname = dbname
        self.user = user
        self._password = password
        self.sslmode: SslMode = sslmode
        self.sslrootcert = sslrootcert
        self.sslcert = sslcert
        self.sslkey = sslkey

        self.connection = psycopg.connect(autocommit=True, **self._connect_kwargs())
        logger.info("Connected to database %s@%s:%s", self.dbname, self.host, self.port)

    @classmethod
    def from_env(cls) -> Self:
        """Build a MetabasePostgres from the conventional env vars.

        Required: ``POSTGRES_HOST``, ``POSTGRES_DB``, ``QA_POSTGRES_USER``.
        ``POSTGRES_PORT`` defaults to 5432.
        Auth: ``QA_POSTGRES_PASSWORD`` or
        ``QA_POSTGRES_SSL{ROOT,}CERT`` + ``QA_POSTGRES_SSLKEY``.
        """
        required = ("POSTGRES_HOST", "POSTGRES_DB", "QA_POSTGRES_USER")
        missing = [name for name in required if not os.getenv(name)]
        if missing:
            raise OSError(f"Required env vars missing: {', '.join(missing)}")
        return cls(
            host=os.environ["POSTGRES_HOST"],
            port=int(os.environ.get("POSTGRES_PORT", "5432")),
            dbname=os.environ["POSTGRES_DB"],
            user=os.environ["QA_POSTGRES_USER"],
            password=os.getenv("QA_POSTGRES_PASSWORD"),
            sslrootcert=_optional_path("QA_POSTGRES_SSLROOTCERT"),
            sslcert=_optional_path("QA_POSTGRES_SSLCERT"),
            sslkey=_optional_path("QA_POSTGRES_SSLKEY"),
            sslmode=_ssl_mode_from_env(),
        )

    def _connect_kwargs(self) -> dict[str, Any]:
        base: dict[str, Any] = {
            "host": self.host,
            "port": self.port,
            "dbname": self.dbname,
            "user": self.user,
        }
        if self._password:
            return {**base, "password": self._password}
        if self.sslcert and self.sslkey and self.sslrootcert:
            return {
                **base,
                "sslmode": self.sslmode,
                "sslrootcert": str(self.sslrootcert),
                "sslcert": str(self.sslcert),
                "sslkey": str(self.sslkey),
            }
        raise ValueError("Database password or SSL certificates must be provided")

    def cursor(self) -> psycopg.Cursor[Any]:
        """Return a new cursor; use as ``with db.cursor() as cur: ...``.

        ``psycopg.Cursor`` is itself a context manager — entering returns the
        cursor and exiting closes it.
        """
        return self.connection.cursor()

    def close(self) -> None:
        if not self.connection.closed:
            self.connection.close()

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()


def _optional_path(env_var: str) -> Path | None:
    value = os.getenv(env_var)
    return Path(value) if value else None


def _ssl_mode_from_env() -> SslMode:
    raw = os.getenv("QA_POSTGRES_SSLMODE", "allow")
    valid: tuple[SslMode, ...] = (
        "disable",
        "allow",
        "prefer",
        "require",
        "verify-ca",
        "verify-full",
    )
    if raw not in valid:
        raise ValueError(f"Invalid QA_POSTGRES_SSLMODE={raw!r}; valid: {valid}")
    return raw  # type: ignore[return-value]
