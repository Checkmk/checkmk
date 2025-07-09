#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest
from marshmallow.exceptions import ValidationError

from cmk.gui.fields.utils import attr_openapi_schema, collect_attributes


@pytest.fixture(autouse=True)
def attr_openapi_schema_clear_cache():
    attr_openapi_schema.cache_clear()
    yield
    attr_openapi_schema.cache_clear()


@pytest.mark.usefixtures("load_config")
def test_collect_attributes_host_create() -> None:
    attrs = collect_attributes("host", "create")
    assert len(attrs) > 10, len(attrs)


@pytest.mark.usefixtures("load_config")
def test_collect_attributes_host_update() -> None:
    attrs = collect_attributes("host", "update")
    assert len(attrs) > 10, len(attrs)


@pytest.mark.usefixtures("load_config")
def test_collect_attributes_cluster_create() -> None:
    attrs = collect_attributes("cluster", "create")
    assert len(attrs) > 10, len(attrs)


@pytest.mark.usefixtures("load_config")
def test_collect_attributes_cluster_update() -> None:
    attrs = collect_attributes("cluster", "update")
    assert len(attrs) > 10, len(attrs)


@pytest.mark.usefixtures("load_config")
def test_collect_attributes_folder_create() -> None:
    attrs = collect_attributes("folder", "create")
    assert len(attrs) > 10, len(attrs)


@pytest.mark.usefixtures("load_config")
def test_collect_attributes_folder_update() -> None:
    attrs = collect_attributes("folder", "update")
    assert len(attrs) > 10


@pytest.mark.usefixtures("load_config")
def test_schema_load_accepts_known_attributes_host_create() -> None:
    schema_class = attr_openapi_schema("host", "create")
    schema_obj = schema_class()
    assert schema_obj.load({"tag_address_family": "ip-v4-only"}) == {
        "tag_address_family": "ip-v4-only"
    }


@pytest.mark.usefixtures("load_config")
def test_schema_load_accepts_known_attributes_folder_update() -> None:
    schema_class = attr_openapi_schema("folder", "update")
    schema_obj = schema_class()
    assert schema_obj.load({"tag_address_family": "ip-v4-only"}) == {
        "tag_address_family": "ip-v4-only"
    }


@pytest.mark.usefixtures("load_config")
def test_schema_load_accepts_known_attributes_cluster_create() -> None:
    schema_class = attr_openapi_schema("cluster", "create")
    schema_obj = schema_class()
    assert schema_obj.load({"tag_address_family": "ip-v4-only"}) == {
        "tag_address_family": "ip-v4-only"
    }


@pytest.mark.usefixtures("load_config")
def test_schema_load_unknown_attributes_raise_exception() -> None:
    schema_obj = attr_openapi_schema("host", "create")()
    with pytest.raises(ValidationError, match="Unknown field"):
        schema_obj.load({"unknown_key": "unknown_value"})


@pytest.mark.usefixtures("load_config")
def test_schema_load_wrong_tags_raise_exception() -> None:
    schema_obj = attr_openapi_schema("host", "create")()
    with pytest.raises(ValidationError, match="is not one of the enum values"):
        schema_obj.load({"tag_address_family": "ip-v5-only"})
