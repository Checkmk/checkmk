#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest
from pydantic import TypeAdapter
from pydantic.errors import PydanticSchemaGenerationError

from cmk.gui.watolib.simple_config_file import config_file_registry


@pytest.mark.usefixtures("load_gui_plugins")
def test_registered_config_files() -> None:
    expected_config_files = [
        "etc/check_mk/conf.d/wato/contacts.mk",
        "etc/check_mk/conf.d/wato/groups.mk",
        "etc/check_mk/conf.d/wato/notifications.mk",
        "etc/check_mk/conf.d/wato/passwords.mk",
        "etc/check_mk/multisite.d/broker_connections.mk",
        "etc/check_mk/multisite.d/sites.mk",
        "etc/check_mk/multisite.d/wato/configuration_bundles.mk",
        "etc/check_mk/multisite.d/wato/groups.mk",
        "etc/check_mk/multisite.d/wato/roles.mk",
        "etc/check_mk/multisite.d/wato/tags.mk",
        "etc/check_mk/multisite.d/wato/user_connections.mk",
        "etc/check_mk/multisite.d/wato/users.mk",
    ]

    assert sorted(config_file_registry.keys()) == sorted(expected_config_files)


# cmk-update-config validates every registered file against its spec_class.
@pytest.mark.usefixtures("load_gui_plugins")
def test_registered_config_files_have_a_validation_schema() -> None:
    without_schema = []
    for path, config_file in config_file_registry.items():
        try:
            TypeAdapter(config_file.spec_class)  # astrein: disable=pydantic-type-adapter
        except PydanticSchemaGenerationError:
            without_schema.append(path)

    assert not without_schema
