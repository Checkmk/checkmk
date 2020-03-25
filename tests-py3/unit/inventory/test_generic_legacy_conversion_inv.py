#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from contextlib import contextmanager
import pytest  # type: ignore[import]

from testlib.base import KNOWN_AUTO_MIGRATION_FAILURES_INV
import cmk.base.inventory_plugins as inventory_plugins
import cmk.base.config as config
import cmk.base.check_api as check_api
import cmk.base.check_utils as check_utils

from cmk.base.api import PluginName

from cmk.base.api.agent_based.section_types import SNMPSectionPlugin

pytestmark = pytest.mark.checks

KNOWN_FAILURES = set(plugin_name for _, plugin_name in KNOWN_AUTO_MIGRATION_FAILURES_INV)


@contextmanager
def known_exceptions(name):
    if name not in KNOWN_FAILURES:
        yield
        return

    with pytest.raises(NotImplementedError):
        yield


@pytest.fixture(scope="module", name="inv_info")
def _get_inv_info():
    inventory_plugins.load_plugins(check_api.get_check_api_context, lambda: {})
    assert len(inventory_plugins.inv_info) > 100  # sanity check
    return inventory_plugins.inv_info.copy()


def test_create_section_plugin_from_legacy(inv_info):
    for name, inv_info_dict in inv_info.items():
        if 'snmp_info' not in inv_info_dict:
            continue

        section_name = PluginName(check_utils.section_name_of(name))
        with known_exceptions(name):
            if section_name not in config.registered_snmp_sections:
                raise NotImplementedError(name)
            section = config.registered_snmp_sections[section_name]
            assert isinstance(section, SNMPSectionPlugin)
