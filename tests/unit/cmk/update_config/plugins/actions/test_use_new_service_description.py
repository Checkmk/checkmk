#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
from collections.abc import Generator
from contextlib import contextmanager

import pytest

from cmk.gui.type_defs import GlobalSettings
from cmk.gui.watolib.config_domains import ConfigDomainCACertificates
from cmk.gui.watolib.global_settings import load_configuration_settings, save_global_settings
from cmk.gui.watolib.sample_config import USE_NEW_DESCRIPTIONS_FOR_SETTING
from cmk.update_config.lib import ExpiryVersion
from cmk.update_config.plugins.actions.use_new_service_description import (
    UpdateUseNewServiceDescription,
)


@contextmanager
def _setup_global_settings(global_settings_setup: GlobalSettings) -> Generator[None]:
    original_global_settings = load_configuration_settings(full_config=True)
    try:
        save_global_settings(
            {**ConfigDomainCACertificates().default_globals(), **global_settings_setup}
        )
        yield
    finally:
        save_global_settings(
            {**ConfigDomainCACertificates().default_globals(), **original_global_settings}
        )


@pytest.mark.usefixtures("request_context")
def test_update_action_raises_on_removed_plugin() -> None:
    initial_global_settings: GlobalSettings = {
        "use_new_descriptions_for": dict.fromkeys(
            USE_NEW_DESCRIPTIONS_FOR_SETTING["use_new_descriptions_for"], True
        )
        | {"removed_plugin": True}
    }
    with _setup_global_settings(initial_global_settings):
        action = UpdateUseNewServiceDescription(
            name="use_new_service_description",
            title="Use new service description",
            sort_index=17,  # before rulesets and global settings
            expiry_version=ExpiryVersion.NEVER,
        )
        with pytest.raises(
            NotImplementedError,
            match="Removing plugins from 'use_new_descriptions_for' is not possible at the moment. The following plugins where found in the configuration under update, but are not configurable in the new Checkmk version: {'removed_plugin'}",
        ):
            action(logging.getLogger())
