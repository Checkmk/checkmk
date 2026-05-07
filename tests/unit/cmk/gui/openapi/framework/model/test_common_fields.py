#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import base64
import json
from typing import Annotated

import pytest
from pydantic import TypeAdapter, ValidationError

from cmk.gui.openapi.framework.model.common_fields import (
    BinaryBase64,
    columns_validator,
    query_expression_validator,
)
from cmk.livestatus_client.expressions import BinaryExpression, NothingExpression, QueryExpression
from cmk.livestatus_client.tables import Hosts
from cmk.livestatus_client.types import Column


class TestBinaryBase64:
    @pytest.fixture(scope="class")
    def adapter(self) -> TypeAdapter[BinaryBase64]:
        return TypeAdapter(BinaryBase64)  # astrein: disable=pydantic-type-adapter

    def test_is_bytes_subclass(self) -> None:
        value = BinaryBase64(b"hello")
        assert isinstance(value, bytes)
        assert bytes(value) == b"hello"

    def test_serializes_to_wire_format(self, adapter: TypeAdapter[BinaryBase64]) -> None:
        data = b"hello world"
        result = adapter.dump_python(BinaryBase64(data))
        assert result == {
            "value_type": "binary_base64",
            "value": base64.encodebytes(data).decode("ascii"),
        }

    def test_serializes_empty_bytes(self, adapter: TypeAdapter[BinaryBase64]) -> None:
        result = adapter.dump_python(BinaryBase64(b""))
        assert result == {"value_type": "binary_base64", "value": ""}

    def test_pydantic_accepts_binary_base64_instance(
        self, adapter: TypeAdapter[BinaryBase64]
    ) -> None:
        value = BinaryBase64(b"data")
        assert adapter.validate_python(value) == value

    def test_validate_from_bytes(self, adapter: TypeAdapter[BinaryBase64]) -> None:
        result = adapter.validate_python(b"hello")
        assert isinstance(result, BinaryBase64)
        assert bytes(result) == b"hello"

    def test_validate_from_wire_format(self, adapter: TypeAdapter[BinaryBase64]) -> None:
        data = b"hello world"
        wire = {"value_type": "binary_base64", "value": base64.encodebytes(data).decode("ascii")}
        result = adapter.validate_python(wire)
        assert isinstance(result, BinaryBase64)
        assert bytes(result) == data

    def test_validate_rejects_invalid_dict(self, adapter: TypeAdapter[BinaryBase64]) -> None:
        with pytest.raises(ValidationError, match="Expected bytes"):
            adapter.validate_python({"not": "valid"})

    def test_validate_rejects_non_bytes(self, adapter: TypeAdapter[BinaryBase64]) -> None:
        with pytest.raises(ValidationError, match="Expected bytes"):
            adapter.validate_python("not bytes")


class TestQueryExpressionValidator:
    @pytest.fixture(scope="class")
    def adapter(self) -> TypeAdapter[QueryExpression]:
        return TypeAdapter(  # astrein: disable=pydantic-type-adapter
            Annotated[QueryExpression, query_expression_validator(Hosts)]
        )

    def test_accepts_dict(self, adapter: TypeAdapter[QueryExpression]) -> None:
        result = adapter.validate_python({"op": "=", "left": "name", "right": "example.com"})
        assert isinstance(result, BinaryExpression)

    def test_accepts_json_string(self, adapter: TypeAdapter[QueryExpression]) -> None:
        value = json.dumps({"op": "=", "left": "name", "right": "example.com"})
        result = adapter.validate_python(value)
        assert isinstance(result, BinaryExpression)

    def test_invalid_json_string_raises(self, adapter: TypeAdapter[QueryExpression]) -> None:
        with pytest.raises(ValidationError, match="Invalid JSON"):
            adapter.validate_python("{not valid json")

    def test_unknown_column_raises(self, adapter: TypeAdapter[QueryExpression]) -> None:
        with pytest.raises(ValidationError):
            adapter.validate_python({"op": "=", "left": "nonexistent_column", "right": "x"})

    def test_invalid_type_raises(self, adapter: TypeAdapter[QueryExpression]) -> None:
        with pytest.raises(ValidationError):
            adapter.validate_python(42)

    def test_empty_dict_raises_by_default(self, adapter: TypeAdapter[QueryExpression]) -> None:
        with pytest.raises(ValidationError):
            adapter.validate_python({})

    def test_empty_string_raises_by_default(self, adapter: TypeAdapter[QueryExpression]) -> None:
        with pytest.raises(ValidationError):
            adapter.validate_python("")


class TestQueryExpressionValidatorAllowEmpty:
    @pytest.fixture(scope="class")
    def adapter(self) -> TypeAdapter[QueryExpression]:
        return TypeAdapter(  # astrein: disable=pydantic-type-adapter
            Annotated[QueryExpression, query_expression_validator(Hosts, allow_empty=True)]
        )

    def test_empty_dict_returns_nothing_expression(
        self, adapter: TypeAdapter[QueryExpression]
    ) -> None:
        assert isinstance(adapter.validate_python({}), NothingExpression)

    def test_empty_string_returns_nothing_expression(
        self, adapter: TypeAdapter[QueryExpression]
    ) -> None:
        assert isinstance(adapter.validate_python(""), NothingExpression)

    def test_non_empty_expression_still_parsed(self, adapter: TypeAdapter[QueryExpression]) -> None:
        result = adapter.validate_python({"op": "=", "left": "name", "right": "foo"})
        assert isinstance(result, BinaryExpression)


class TestColumnsValidator:
    @pytest.fixture(scope="class")
    def adapter(self) -> TypeAdapter[list[Column]]:
        return TypeAdapter(  # astrein: disable=pydantic-type-adapter
            Annotated[list[Column], columns_validator(Hosts)]
        )

    def test_valid_columns_returned_as_column_objects(
        self, adapter: TypeAdapter[list[Column]]
    ) -> None:
        result = adapter.validate_python(["name", "alias"])
        assert repr(result) == repr([Hosts.name, Hosts.alias])

    def test_no_mandatory_accepts_empty_list(self, adapter: TypeAdapter[list[Column]]) -> None:
        result = adapter.validate_python([])
        assert result == []

    def test_unknown_column_raises(self, adapter: TypeAdapter[list[Column]]) -> None:
        with pytest.raises(ValidationError, match="Unknown column"):
            adapter.validate_python(["nonexistent_column"])

    def test_invalid_input_type_raises(self, adapter: TypeAdapter[list[Column]]) -> None:
        with pytest.raises(ValidationError):
            adapter.validate_python(42)

    def test_invalid_item_type_raises(self, adapter: TypeAdapter[list[Column]]) -> None:
        with pytest.raises(ValidationError):
            adapter.validate_python([123])

    def test_invalid_mandatory_at_construction_raises(self) -> None:
        with pytest.raises(ValueError, match="not a column of table"):
            columns_validator(Hosts, mandatory=["nonexistent_column"])

    @pytest.fixture(scope="class")
    def adapter_mandatory(self) -> TypeAdapter[list[Column]]:
        return TypeAdapter(  # astrein: disable=pydantic-type-adapter
            Annotated[list[Column], columns_validator(Hosts, mandatory=[Hosts.name])]
        )

    def test_mandatory_prepended_when_missing(
        self, adapter_mandatory: TypeAdapter[list[Column]]
    ) -> None:
        result = adapter_mandatory.validate_python(["alias"])
        assert repr(result[0]) == repr(Hosts.name)
        assert Hosts.alias in result

    def test_mandatory_not_duplicated_when_present(
        self, adapter_mandatory: TypeAdapter[list[Column]]
    ) -> None:
        result = adapter_mandatory.validate_python(["name", "alias"])
        assert len(result) == 2
        assert [c.name for c in result].count("name") == 1

    def test_empty_list_returns_mandatory_only(
        self, adapter_mandatory: TypeAdapter[list[Column]]
    ) -> None:
        result = adapter_mandatory.validate_python([])
        assert repr(result) == repr([Hosts.name])

    def test_multiple_mandatory_prepended_in_order(self) -> None:
        adapter: TypeAdapter[list[Column]] = TypeAdapter(  # astrein: disable=pydantic-type-adapter
            Annotated[list[Column], columns_validator(Hosts, mandatory=[Hosts.name, Hosts.alias])]
        )
        result = adapter.validate_python(["address"])
        assert repr(result[0]) == repr(Hosts.name)
        assert repr(result[1]) == repr(Hosts.alias)

    def test_mandatory_as_string(self) -> None:
        adapter: TypeAdapter[list[Column]] = TypeAdapter(  # astrein: disable=pydantic-type-adapter
            Annotated[list[Column], columns_validator(Hosts, mandatory=["name"])]
        )
        result = adapter.validate_python(["alias"])
        assert repr(result[0]) == repr(Hosts.name)
