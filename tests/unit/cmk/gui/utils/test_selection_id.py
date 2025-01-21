#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from unittest.mock import patch

import pytest

from cmk.gui.exceptions import MKUserError
from cmk.gui.utils.selection_id import SelectionId


@pytest.mark.parametrize("id_", ("../foo",))
def test_selection_id_validation_failures(id_: str) -> None:
    with pytest.raises(ValueError):
        SelectionId(id_)


@pytest.mark.parametrize("id_", ("foo", "481236ac-3e3b-4159-b61c-3be758691606"))
def test_selection_id_validation_success(id_: str) -> None:
    SelectionId(id_)


class _RequestMock:
    def __init__(self, selection_id: str) -> None:
        self.selection_id = selection_id

    def get_validated_type_input_mandatory(
        self, type_: type[SelectionId], name: str
    ) -> SelectionId:
        assert name == "selection"
        if not self.selection_id:
            raise MKUserError(None, "foo")
        try:
            return SelectionId(self.selection_id)
        except ValueError:
            raise MKUserError(None, "foo")

    def set_var(self, _varname: str, _value: str) -> None:
        return


@patch("uuid.uuid4", lambda: "9f959db3-3881-49a7-8f41-0d048af2d30f")
def test_from_request() -> None:
    assert SelectionId.from_request(_RequestMock("foo")) == "foo"  # type: ignore[arg-type]
    assert SelectionId.from_request(_RequestMock("foo.")) == "9f959db3-3881-49a7-8f41-0d048af2d30f"  # type: ignore[arg-type]
