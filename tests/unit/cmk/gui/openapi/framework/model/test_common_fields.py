#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import base64
import json
from collections.abc import Iterator
from typing import Annotated

import pytest
from pydantic import TypeAdapter, ValidationError

from livestatus import SiteConfigurations

from cmk.ccc.site import SiteId
from cmk.ccc.user import UserId
from cmk.gui.config import Config
from cmk.gui.logged_in import user as logged_in_user
from cmk.gui.openapi.framework.model.common_fields import (
    _FolderValidation,
    BinaryBase64,
    columns_validator,
    query_expression_validator,
)
from cmk.gui.watolib.audit_log import make_audit_log_change_hook
from cmk.gui.watolib.hosts_and_folders import Folder, folder_tree
from cmk.gui.watolib.pending_changes import NoopPendingChangesStore, PendingChanges
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


class TestFolderValidation:
    @pytest.fixture
    def subfolder(self, with_admin_login: UserId) -> Iterator[Folder]:
        # The name "abc" is a valid hex string, which makes it ambiguous with a folder id.
        pending_changes = PendingChanges(
            activation_sites=SiteConfigurations({}),
            local_site=SiteId("NO_SITE"),
            acting_user=None,
            store=NoopPendingChangesStore(),
            hooks=(make_audit_log_change_hook(use_git=False),),
        )
        root = folder_tree().root_folder()
        folder = root.create_subfolder(
            "abc",
            "abc",
            {},
            pprint_value=False,
            pending_changes=pending_changes,
            acting_user=logged_in_user,
        )
        yield folder
        root.delete_subfolder("abc", pending_changes=pending_changes, acting_user=logged_in_user)

    def test_root_via_slash(self, load_config: Config) -> None:
        assert _FolderValidation.validate("/") == folder_tree().root_folder()

    def test_root_via_empty_string(self, load_config: Config) -> None:
        assert _FolderValidation.validate("") == folder_tree().root_folder()

    @pytest.mark.parametrize(
        "value",
        [
            pytest.param("~abc", id="leading-tilde"),
            pytest.param("/abc", id="leading-slash"),
            pytest.param("\\abc", id="leading-backslash"),
            pytest.param("/abc/", id="surrounding-slashes"),
        ],
    )
    def test_separator_forces_path_lookup_for_hex_name(self, value: str, subfolder: Folder) -> None:
        assert _FolderValidation.validate(value) == subfolder

    @pytest.mark.parametrize("value", ["abc/", "abc~"])
    def test_trailing_separator_hex_name_resolves_as_path(
        self, value: str, subfolder: Folder
    ) -> None:
        assert _FolderValidation.validate(value) == subfolder

    def test_bare_hex_name_is_treated_as_id_not_path(self, subfolder: Folder) -> None:
        with pytest.raises(ValueError):
            _FolderValidation.validate("abc")

    def test_hex_id_resolved_by_id(self, subfolder: Folder) -> None:
        assert _FolderValidation.validate(subfolder.id()) == subfolder

    def test_invalid_hex_id_raises_value_error(self, load_config: Config) -> None:
        with pytest.raises(ValueError):
            _FolderValidation.validate("deadbeef")

    def test_unknown_path_raises_value_error(self, load_config: Config) -> None:
        with pytest.raises(ValueError):
            _FolderValidation.validate("~does~not~exist")
