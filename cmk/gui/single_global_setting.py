#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
# mypy: disable-error-code="no-any-return"

from typing import Any, Literal

from cmk.ccc.store import load_mk_file

import cmk.utils.paths


def load_gui_log_levels() -> dict[str, int]:
    """Load the GUI log-level global setting from the Setup GUI config"""
    return _load_single_global_wato_setting(
        "log_levels",
        {
            "cmk.web": 30,
            "cmk.web.ldap": 30,
            "cmk.web.saml2": 30,
            "cmk.web.auth": 30,
            "cmk.web.bi.compilation": 30,
            "cmk.web.automations": 30,
            "cmk.web.background-job": 30,
            "cmk.web.ui-job-scheduler": 20,
            "cmk.web.slow-views": 30,
            "cmk.web.agent_registration": 30,
        },
    )


def load_profiling_mode() -> Literal[True, False, "enable_by_var"]:
    return _load_single_global_wato_setting("profile", deflt=False)


def _load_single_global_wato_setting(varname: str, deflt: Any = None) -> Any:
    """Load a single config option from Setup globals (Only for special use)

    This is a small hack to get access to the current configuration without
    the need to load the whole GUI config.

    The problem is: The profiling setting is needed before the GUI config
    is loaded regularly. This is needed, because we want to be able to
    profile our whole WSGI app, including the config loading logic.

    We only process the Setup written global settings file to get the WATO
    settings, which should be enough for most cases.
    """
    settings = load_mk_file(
        cmk.utils.paths.default_config_dir / "multisite.d/wato/global.mk", default={}, lock=False
    )
    return settings.get(varname, deflt)
