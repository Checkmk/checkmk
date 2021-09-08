#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

import cmk.utils.version as cmk_version

from cmk.gui.globals import config, user
from cmk.gui.utils.ntop import (
    get_ntop_misconfiguration_reason,
    is_ntop_available,
    is_ntop_configured,
)


@pytest.mark.usefixtures("load_config")
def test_is_ntop_available():
    available = is_ntop_available()

    if cmk_version.is_raw_edition():
        assert not available
    if not cmk_version.is_raw_edition():
        assert available


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
    mocker,
    ntop_connection,
    custom_user,
    answer,
    reason,
):
    if cmk_version.is_raw_edition():
        assert not is_ntop_configured()
        assert get_ntop_misconfiguration_reason() == "ntopng integration is only available in CEE"
    if not cmk_version.is_raw_edition():
        mocker.patch.object(
            config,
            "ntop_connection",
            ntop_connection,
        )
        if custom_user:
            user._set_attribute("ntop_alias", custom_user)
        assert is_ntop_configured() == answer
        assert get_ntop_misconfiguration_reason() == reason
