#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Generic UPSERT helper shared by the qa_metrics pipelines."""

import logging
from collections.abc import Mapping
from typing import Any

from psycopg import sql
from psycopg.errors import Error as PsycopgError

from .connection import MetabasePostgres

logger = logging.getLogger(__name__)


def upsert_record(
    db: MetabasePostgres,
    table: str,
    conflict_columns: list[str],
    insert_values: Mapping[str, Any],
    update_values: Mapping[str, Any] | None = None,
) -> None:
    """``INSERT ... ON CONFLICT (conflict_columns) DO UPDATE``.

    ``update_values`` defaults to ``insert_values`` (full overwrite on conflict).
    """
    update_values = update_values if update_values is not None else insert_values

    with db.cursor() as cursor:
        columns = sql.SQL(", ").join(sql.Identifier(k) for k in insert_values)
        placeholders = sql.SQL(", ").join([sql.Placeholder()] * len(insert_values))
        conflict_clause = sql.SQL(", ").join(sql.Identifier(c) for c in conflict_columns)
        update_clause = sql.SQL(", ").join(
            sql.SQL("{c} = EXCLUDED.{c}").format(c=sql.Identifier(k)) for k in update_values
        )
        query = sql.SQL(
            "INSERT INTO {table} ({columns}) VALUES ({placeholders}) "
            "ON CONFLICT ({conflict}) DO UPDATE SET {update}"
        ).format(
            table=sql.Identifier(table),
            columns=columns,
            placeholders=placeholders,
            conflict=conflict_clause,
            update=update_clause,
        )
        try:
            cursor.execute(query, list(insert_values.values()))
        except PsycopgError:
            logger.exception("UPSERT on %s failed", table)
            raise
