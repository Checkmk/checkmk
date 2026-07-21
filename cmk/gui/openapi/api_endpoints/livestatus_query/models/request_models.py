#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from typing import Annotated, Final, Self

from annotated_types import Ge, Le, MinLen
from pydantic import AfterValidator, model_validator

from cmk.ccc.site import SiteId
from cmk.gui.openapi.framework.model import api_field, api_model
from cmk.gui.openapi.framework.model.common_fields import (
    parse_columns,
    parse_query_expression,
)
from cmk.gui.openapi.framework.model.converter import (
    RegistryConverter,
    SiteIdConverter,
    TypedPlainValidator,
)
from cmk.livestatus_client.expressions import QueryExpression
from cmk.livestatus_client.queries import Query
from cmk.livestatus_client.types import Column, Table

from .._tables import LIVESTATUS_TABLES, resolve_table

# tree_to_expr recurses once per enclosing and/or/not operator, so an attacker could nest a
# filter thousands deep and turn it into a RecursionError (a 500). We reject anything deeper
# than this before that recursion runs; the cap is far above any legitimate hand-written query.
_MAX_QUERY_DEPTH: Final = 32

# An unbounded query against a large table (e.g. `log`) would materialize every row in the
# site's memory at once. Every query therefore carries a row limit; this is its ceiling.
_MAX_ROW_LIMIT: Final = 10_000
_DEFAULT_ROW_LIMIT: Final = 1_000


def _no_duplicate_columns(columns: list[str]) -> list[str]:
    seen: set[str] = set()
    for column in columns:
        if column in seen:
            raise ValueError(f"Duplicate column {column!r} in the column list.")
        seen.add(column)
    return columns


def _check_query_depth(query: Mapping[str, object]) -> Mapping[str, object]:
    """Reject a filter nested deeper than `_MAX_QUERY_DEPTH` before `tree_to_expr` recurses.

    Walks the and/or/not structure iteratively (an explicit stack, never recursion of its own)
    so that a hostile deeply-nested body is rejected with a clean `ValueError` instead of the
    `RecursionError` that `tree_to_expr` would raise. Leaf operators carry no children and do
    not count toward the depth.

    Runs as the `query` field's validator, so the cap is enforced before the model validator
    compiles the filter -- there is no path on which `tree_to_expr` sees an uncapped body.
    """
    stack: list[tuple[object, int]] = [(query, 1)]
    while stack:
        node, depth = stack.pop()
        if not isinstance(node, Mapping) or node.get("op") not in ("and", "or", "not"):
            continue
        if depth > _MAX_QUERY_DEPTH:
            raise ValueError(
                f"Query filter nesting exceeds the maximum depth of {_MAX_QUERY_DEPTH}."
            )
        child = node.get("expr")
        if node["op"] == "not":
            stack.append((child, depth + 1))
        elif isinstance(child, list):
            stack.extend((item, depth + 1) for item in child)
    return query


def _parse_expressions(
    table: type[Table], columns: list[str], query: Mapping[str, object] | None
) -> tuple[list[Column], QueryExpression | None]:
    """Turn the raw user-supplied columns and filter into Livestatus expressions.

    This is the input-parsing boundary and the only place with a broad catch: the parse
    functions walk untrusted wire values, so besides `ValueError`/`KeyError` they can raise
    `TypeError` (non-string filter `left`) or `AttributeError` (dunder column names in a
    filter). All are normalized to `ValueError` so the framework reports malformed input as
    a self-describing 400. Code outside this function raises naturally, so a genuine
    programming defect still surfaces as a 500 instead of masquerading as bad input.
    """
    try:
        parsed_columns = parse_columns(table, columns)
        expression = parse_query_expression(table, query) if query is not None else None
    except (ValueError, KeyError, TypeError, AttributeError) as e:
        raise ValueError(str(e)) from e
    return parsed_columns, expression


@api_model
class LivestatusQueryBody:
    """Body of a generic Livestatus query.

    A deep module: the interface is the five wire fields below plus `to_query()`, and behind it
    hides table resolution, column validation, filter compilation, a nesting-depth cap, and
    exception normalization. No other module ever sees a table-name string or a raw filter dict.
    """

    table: Annotated[str, AfterValidator(RegistryConverter(LIVESTATUS_TABLES).validate)] = (
        api_field(
            description="The Livestatus table to query, given by its lowercase wire name "
            "(for example `hosts`, `services`, `log`).",
            example="hosts",
        )
    )
    columns: Annotated[list[str], MinLen(1), AfterValidator(_no_duplicate_columns)] = api_field(
        description="The columns to return, by name. Must be non-empty and free of duplicates; "
        "every name is validated against the chosen table.",
        example=["name", "alias"],
    )
    query: Annotated[Mapping[str, object], AfterValidator(_check_query_depth)] | None = api_field(
        description="An optional Livestatus filter expression, as a nested object "
        "(no JSON-string form). Column names are validated against the chosen table.",
        example={"op": "=", "left": "name", "right": "heute"},
        default=None,
    )
    sites: list[Annotated[SiteId, TypedPlainValidator(str, SiteIdConverter.should_exist)]] = (
        api_field(
            description="Restrict the query to these sites. Empty means all sites.",
            example=["heute"],
            default_factory=list,
        )
    )
    limit: Annotated[int, Ge(1), Le(_MAX_ROW_LIMIT)] = api_field(
        description=f"The maximum number of rows to return, at most {_MAX_ROW_LIMIT}. "
        "The limit is applied per site: a query spanning several sites may return up to "
        "this many rows from each site.",
        example=_DEFAULT_ROW_LIMIT,
        default=_DEFAULT_ROW_LIMIT,
    )

    def to_query(self) -> Query:
        """Resolve this body into a ready-to-run `Query`.

        The single derivation method: it resolves the table name, validates the columns and
        compiles the filter, and returns a `Query` with the filter applied. The handler never
        touches a table class, a column string, or `tree_to_expr` itself. The nesting cap is
        already enforced by the `query` field validator.

        Every column is labelled with the name the client asked for, so the result rows are
        keyed by exactly the names in the request. A `Table` attribute name need not equal the
        livestatus column name it wraps -- `Log.class_` wraps `class`, since `class` is a Python
        keyword -- and `iterate()` keys rows by the livestatus name unless a label overrides it.
        Without the label a request for `class_` would come back as a `class` row key, so the
        response would contradict the `columns` it echoes. `label()` returns a copy and leaves
        `Column.name` alone, so the emitted LQL still names the real livestatus column.
        """
        table = resolve_table(self.table)
        columns, expression = _parse_expressions(table, self.columns, self.query)
        q = Query([column.label(name) for name, column in zip(self.columns, columns, strict=True)])
        if expression is not None:
            q = q.filter(expression)
        return q

    @model_validator(mode="after")
    def _validate(self) -> Self:
        """Reject a malformed body at the model boundary by fully deriving the query and discarding it.

        Validate-only (the result is re-derived by the handler via `to_query()`) because the
        `@api_model` slots dataclass serializes every field, so a resolved `Query` must not be
        stashed. Malformed input surfaces from `to_query()` as `ValueError` (the parsing
        boundary normalizes it, see `_parse_expressions`), which pydantic turns into a
        self-describing 400; any other exception is a genuine code defect and propagates
        as a 500.
        """
        self.to_query()
        return self
