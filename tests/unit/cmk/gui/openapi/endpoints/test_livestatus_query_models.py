#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest
from pydantic import TypeAdapter, ValidationError

from cmk.gui.openapi.api_endpoints.livestatus_query.models.request_models import (
    _DEFAULT_ROW_LIMIT,
    _MAX_QUERY_DEPTH,
    _MAX_ROW_LIMIT,
    LivestatusQueryBody,
)
from cmk.gui.openapi.api_endpoints.livestatus_query.models.response_models import (
    LivestatusQueryResponse,
)
from cmk.gui.openapi.framework.model.common_fields import BinaryBase64
from cmk.livestatus_client.queries import ResultRow


def test_valid_body_compiles_expected_lql() -> None:
    adapter = TypeAdapter(LivestatusQueryBody)  # astrein: disable=pydantic-type-adapter
    body = adapter.validate_python(
        {
            "table": "hosts",
            "columns": ["name", "alias"],
            "query": {"op": "=", "left": "name", "right": "heute"},
        }
    )
    compiled = body.to_query().compile()
    assert "GET hosts" in compiled, compiled
    assert "Columns: name alias" in compiled, compiled
    assert "Filter: name = heute" in compiled, compiled


def test_to_query_keys_result_rows_by_the_requested_column_names() -> None:
    """A `Table` attribute name may differ from the livestatus column it wraps.

    `Log.class_` wraps the livestatus column `class` (a Python keyword), and `columns` is
    validated against the attribute names. Livestatus must still be asked for `class`, while the
    rows have to come back keyed by `class_` -- the name the client sent and the response echoes.
    """
    adapter = TypeAdapter(LivestatusQueryBody)  # astrein: disable=pydantic-type-adapter
    body = adapter.validate_python({"table": "log", "columns": ["class_", "message"]})
    q = body.to_query()
    compiled = q.compile()
    assert "Columns: class message" in compiled, compiled
    # These are the names `iterate()` keys each result row with.
    assert q.column_names == ["class_", "message"]


@pytest.mark.parametrize(
    "body, match",
    [
        # "downtimes" is a supported table absent from the input, so matching on it proves
        # the field rejects with the permitted names rather than merely echoing the input.
        pytest.param(
            {"table": "not_a_table", "columns": ["name"]},
            "downtimes",
            id="unknown-table",
        ),
        pytest.param(
            {"table": "Hosts", "columns": ["name"]},
            "downtimes",
            id="table-class-name-not-wire-name",
        ),
        pytest.param(
            {"table": "hosts", "columns": ["nonexistent_column"]},
            "Unknown column",
            id="unknown-column",
        ),
        pytest.param(
            {"table": "hosts", "columns": ["name", "name"]},
            "Duplicate",
            id="duplicate-columns",
        ),
        pytest.param(
            {"table": "hosts", "columns": []},
            "columns",
            id="empty-columns",
        ),
        pytest.param(
            {"table": "hosts", "columns": ["name\nColumnHeaders: on"]},
            "Unknown column",
            id="newline-in-column",
        ),
        pytest.param(
            {
                "table": "hosts",
                "columns": ["name"],
                "query": {"op": "=", "left": "services.description", "right": "x"},
            },
            "can only query table",
            id="foreign-table-filter",
        ),
        pytest.param(
            {
                "table": "hosts",
                "columns": ["name"],
                "query": {"op": "bogus", "left": "name", "right": "x"},
            },
            "Unknown operator",
            id="unknown-operator",
        ),
        # For the two malformed-filter cases below no domain-owned message exists (the
        # wording comes from CPython builtins), so only the rejection itself is asserted.
        pytest.param(
            {
                "table": "hosts",
                "columns": ["name"],
                "query": {"op": "=", "left": 5, "right": "x"},
            },
            None,
            id="non-string-filter-left",
        ),
        pytest.param(
            {
                "table": "hosts",
                "columns": ["name"],
                "query": {"op": "=", "left": "__doc__", "right": "x"},
            },
            None,
            id="dunder-filter-left",
        ),
        pytest.param(
            {"table": "hosts", "columns": ["name"], "limit": 0},
            "greater than or equal to 1",
            id="limit-zero",
        ),
        pytest.param(
            {"table": "hosts", "columns": ["name"], "limit": _MAX_ROW_LIMIT + 1},
            f"less than or equal to {_MAX_ROW_LIMIT}",
            id="limit-above-ceiling",
        ),
    ],
)
def test_body_rejects_invalid_input(body: dict[str, object], match: str | None) -> None:
    adapter = TypeAdapter(LivestatusQueryBody)  # astrein: disable=pydantic-type-adapter
    with pytest.raises(ValidationError, match=match):
        adapter.validate_python(body)


def test_body_limit_defaults_and_accepts_bounds() -> None:
    adapter = TypeAdapter(LivestatusQueryBody)  # astrein: disable=pydantic-type-adapter
    assert (
        adapter.validate_python({"table": "hosts", "columns": ["name"]}).limit == _DEFAULT_ROW_LIMIT
    )
    for boundary in (1, _MAX_ROW_LIMIT):
        body = adapter.validate_python({"table": "hosts", "columns": ["name"], "limit": boundary})
        assert body.limit == boundary


def test_body_rejects_excessive_nesting() -> None:
    adapter = TypeAdapter(LivestatusQueryBody)  # astrein: disable=pydantic-type-adapter
    query: dict[str, object] = {"op": "=", "left": "name", "right": "heute"}
    for _ in range(_MAX_QUERY_DEPTH + 1):
        query = {"op": "not", "expr": query}
    with pytest.raises(ValidationError, match=str(_MAX_QUERY_DEPTH)):
        adapter.validate_python({"table": "hosts", "columns": ["name"], "query": query})


def test_body_accepts_nesting_at_exact_depth_cap() -> None:
    """Guards the `>` vs `>=` off-by-one: exactly `_MAX_QUERY_DEPTH` operators must pass."""
    adapter = TypeAdapter(LivestatusQueryBody)  # astrein: disable=pydantic-type-adapter
    query: dict[str, object] = {"op": "=", "left": "name", "right": "heute"}
    for _ in range(_MAX_QUERY_DEPTH):
        query = {"op": "not", "expr": query}
    body = adapter.validate_python({"table": "hosts", "columns": ["name"], "query": query})
    compiled = body.to_query().compile()
    assert "Filter: name = heute" in compiled, compiled


def test_body_compiles_compound_and_or_filter() -> None:
    adapter = TypeAdapter(LivestatusQueryBody)  # astrein: disable=pydantic-type-adapter
    body = adapter.validate_python(
        {
            "table": "hosts",
            "columns": ["name"],
            "query": {
                "op": "or",
                "expr": [
                    {
                        "op": "and",
                        "expr": [
                            {"op": "=", "left": "name", "right": "heute"},
                            {"op": "=", "left": "alias", "right": "heute alias"},
                        ],
                    },
                    {"op": "=", "left": "name", "right": "morgen"},
                ],
            },
        }
    )
    compiled = body.to_query().compile()
    assert "Filter: name = heute" in compiled, compiled
    assert "Filter: alias = heute alias" in compiled, compiled
    assert "And: 2" in compiled, compiled
    assert "Filter: name = morgen" in compiled, compiled
    assert "Or: 2" in compiled, compiled


def test_body_rejects_excessive_and_or_nesting() -> None:
    """The depth cap must also hold on the and/or (multi-child) branch, not just `not` chains."""
    adapter = TypeAdapter(LivestatusQueryBody)  # astrein: disable=pydantic-type-adapter
    query: dict[str, object] = {"op": "=", "left": "name", "right": "heute"}
    for op in ("and", "or"):
        nested = query
        for _ in range(_MAX_QUERY_DEPTH + 1):
            nested = {"op": op, "expr": [nested, {"op": "=", "left": "name", "right": "x"}]}
        with pytest.raises(ValidationError, match=str(_MAX_QUERY_DEPTH)):
            adapter.validate_python({"table": "hosts", "columns": ["name"], "query": nested})


def test_from_result_serializes_wire_shape() -> None:
    row = ResultRow({"name": "heute", "blob": b"\x00\x01"})
    response = LivestatusQueryResponse.from_result("hosts", ["name", "blob"], [row])
    adapter = TypeAdapter(LivestatusQueryResponse)  # astrein: disable=pydantic-type-adapter
    dumped = adapter.dump_python(response, mode="json")
    # The wrapping decision under test: the bytes cell becomes whatever the shared
    # BinaryBase64 codec emits (its base64 mechanics are covered in test_common_fields),
    # while the str cell passes through and the shape stays the flat three-key contract.
    expected_blob = TypeAdapter(BinaryBase64).dump_python(  # astrein: disable=pydantic-type-adapter
        BinaryBase64(b"\x00\x01"), mode="json"
    )
    assert dumped == {
        "table": "hosts",
        "columns": ["name", "blob"],
        "rows": [{"name": "heute", "blob": expected_blob}],
    }
