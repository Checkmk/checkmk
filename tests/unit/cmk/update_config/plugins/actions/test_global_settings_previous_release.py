#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""The update run on the values a 2.5 site stored, see previous_release_fixtures."""

import logging

import pytest

from cmk.gui.config import active_config
from cmk.gui.exceptions import MKUserError
from cmk.gui.watolib.config_domain_name import config_variable_registry
from cmk.update_config.plugins.actions import global_settings
from tests.testlib.unit.fake_site import edition as edition_from_env
from tests.testlib.unit.gui.config_variable_form_data_test_helper import (
    make_global_settings_context,
    validate_disk_value,
)
from tests.unit.cmk.update_config.plugins.actions.previous_release_fixtures import (
    PREVIOUS_RELEASE_SETTINGS,
    previous_release_settings,
    WITHDRAWN_SINCE_THE_PREVIOUS_RELEASE,
)

REJECTED_BY_THE_CURRENT_FORM = frozenset({"acknowledge_problems", "log_levels"})
"""Settings the current form rejects after the update. The form needs a key
that 2.5 never stored (ack_expire, cmk.web.automatic_host_removal), and the
update does not add it. See CMK-38844 and CMK-38504."""


@pytest.mark.usefixtures("request_context")
def test_updating_the_updated_configuration_again_changes_nothing() -> None:
    once = global_settings.update_global_config(
        logging.getLogger(),
        previous_release_settings(),
        active_config,
    )

    twice = global_settings.update_global_config(logging.getLogger(), dict(once), active_config)

    assert twice == once


@pytest.mark.usefixtures("request_context")
def test_the_current_form_refuses_only_the_recorded_previous_release_values() -> None:
    updated = global_settings.update_global_config(
        logging.getLogger(),
        previous_release_settings(),
        active_config,
    )
    context = make_global_settings_context(edition_from_env())

    rejected = set()
    for ident in PREVIOUS_RELEASE_SETTINGS:
        try:
            validate_disk_value(config_variable_registry[ident], context, updated[ident])
        except MKUserError:
            rejected.add(ident)

    assert rejected == REJECTED_BY_THE_CURRENT_FORM


@pytest.mark.parametrize("ident", WITHDRAWN_SINCE_THE_PREVIOUS_RELEASE)
@pytest.mark.usefixtures("request_context")
def test_a_setting_withdrawn_since_the_previous_release_is_dropped(ident: str) -> None:
    still_offered = "wato_icon_categories"
    assert ident not in config_variable_registry

    updated = global_settings.update_global_config(
        logging.getLogger(),
        {
            ident: "whatever the previous release stored here",
            still_offered: previous_release_settings()[still_offered],
        },
        active_config,
    )

    assert updated == {still_offered: PREVIOUS_RELEASE_SETTINGS[still_offered]}
