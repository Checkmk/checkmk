#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from typing import Any

import pytest
from pytest import MonkeyPatch

import cmk.ccc.version as cmk_version

from cmk.utils import paths

from cmk.gui.config import active_config
from cmk.gui.logged_in import user
from cmk.gui.utils.ntop import (
    get_ntop_misconfiguration_reason,
    is_ntop_available,
    is_ntop_configured,
)


@pytest.mark.usefixtures("load_config")
def test_is_ntop_available() -> None:
    assert is_ntop_available() != (cmk_version.edition(paths.omd_root) is cmk_version.Edition.CRE)


@pytest.mark.usefixtures("load_config")
@pytest.mark.parametrize(
    "ntop_connection, custom_user, answer, reason",
    [
        (
            {"is_activated": False},
            "",
            False,
            "ntopng integration is not activated under global settings.",
        ),
        (
            {"is_activated": True, "use_custom_attribute_as_ntop_username": False},
            "",
            True,
            "",
        ),
        (
            {"is_activated": True, "use_custom_attribute_as_ntop_username": "ntop_alias"},
            "",
            False,
            (
                "The ntopng username should be derived from 'ntopng Username' "
                "under the current's user settings (identity) but this is not "
                "set for the current user."
            ),
        ),
        (
            {"is_activated": True, "use_custom_attribute_as_ntop_username": "ntop_alias"},
            "a_ntop_user",
            True,
            "",
        ),
    ],
)
def test_is_ntop_configured_and_reason(
    monkeypatch: MonkeyPatch,
    ntop_connection: dict[str, Any],
    custom_user: str,
    answer: bool,
    reason: str,
) -> None:
    if cmk_version.edition(paths.omd_root) is cmk_version.Edition.CRE:
        assert not is_ntop_configured()
        assert get_ntop_misconfiguration_reason() == "ntopng integration is only available in CEE"
    else:
        with monkeypatch.context() as m:
            m.setattr(active_config, "ntop_connection", ntop_connection)
            if custom_user:
                user._set_attribute("ntop_alias", custom_user)
            assert is_ntop_configured() == answer
            assert get_ntop_misconfiguration_reason() == reason
