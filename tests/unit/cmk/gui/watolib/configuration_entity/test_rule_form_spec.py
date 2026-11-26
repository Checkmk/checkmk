#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

import pytest

from cmk.gui.form_specs import FormSpecValidationError, RawFrontendData
from cmk.gui.logged_in import LoggedInSuperUser
from cmk.gui.watolib.configuration_entity._rule_form_spec import (
    save_rule_form_spec_from_slidein_schema,
)
from cmk.gui.watolib.hosts_and_folders import folder_tree


@pytest.mark.parametrize(
    "rule_data",
    [
        pytest.param(
            {},
            id="no properties",
            marks=pytest.mark.xfail(
                strict=True, raises=KeyError, reason="Crash group 5037: KeyError"
            ),
        ),
        pytest.param(
            {"properties": {}},
            id="no rule ID",
            marks=pytest.mark.xfail(
                strict=True, raises=KeyError, reason="Crash group 5037: KeyError"
            ),
        ),
        pytest.param(
            {"properties": "x"},
            id="properties not a dictionary",
            marks=pytest.mark.xfail(
                strict=True, raises=TypeError, reason="Crash group 5037: TypeError"
            ),
        ),
    ],
)
@pytest.mark.usefixtures("with_admin_login")
def test_rule_data_without_a_rule_id_is_a_validation_error(rule_data: Mapping[str, object]) -> None:
    with pytest.raises(FormSpecValidationError) as excinfo:
        save_rule_form_spec_from_slidein_schema(
            "special_agents:elasticsearch",
            RawFrontendData(dict(rule_data)),
            folder_tree(),
            LoggedInSuperUser(),
        )

    assert [message.location for message in excinfo.value.messages] == [["properties", "id"]]
