#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import override

import pytest
from marshmallow import Schema

from cmk.fields import String
from cmk.gui.config import get_default_config, make_config_object
from cmk.gui.openapi.restful_objects.validators import PathParamsValidator
from cmk.gui.watolib.hosts_and_folders import FolderTree
from cmk.gui.watolib.openapi_fields import folder_tree_of, request_schema_context


def test_verify_marshmallow_params_matching() -> None:
    class Params(Schema):
        bar = String()

    PathParamsValidator.verify_marshmallow_params_presence("/foo/{bar}", Params)


def test_verify_marshmallow_params_no_schema_no_params() -> None:
    PathParamsValidator.verify_marshmallow_params_presence("/foo", None)


def test_verify_marshmallow_params_unused_schema_field() -> None:
    class Params(Schema):
        bar = String()

    with pytest.raises(ValueError, match="not used in path"):
        PathParamsValidator.verify_marshmallow_params_presence("/foo", Params)


def test_verify_marshmallow_params_missing_schema() -> None:
    with pytest.raises(ValueError, match="were not given in schema parameters"):
        PathParamsValidator.verify_marshmallow_params_presence("/foo/{bar}", None)


class _TreeRecordingField(String):
    """Records the folder tree the field is validated against"""

    seen: list[FolderTree] = []

    @override
    def _validate(self, value: str) -> None:
        super()._validate(value)
        self.seen.append(folder_tree_of(self))


@pytest.mark.usefixtures("request_context")
def test_validate_marshmallow_schema_hands_the_fields_one_tree_of_the_config() -> None:
    class Params(Schema):
        bar = _TreeRecordingField()
        baz = _TreeRecordingField()

    _TreeRecordingField.seen.clear()
    config = make_config_object(get_default_config())

    PathParamsValidator.validate_marshmallow_schema(
        Params, {"bar": "1", "baz": "2"}, request_schema_context(config)
    )

    assert len(_TreeRecordingField.seen) == 2
    assert _TreeRecordingField.seen[0] is _TreeRecordingField.seen[1]


def test_field_without_a_request_tree_complains() -> None:
    class Params(Schema):
        bar = _TreeRecordingField()

    with pytest.raises(RuntimeError, match="No folder tree in the context"):
        Params().load({"bar": "1"})
