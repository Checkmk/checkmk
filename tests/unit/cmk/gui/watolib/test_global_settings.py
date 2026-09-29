#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from typing import override

import pytest

from cmk.ccc.site import SiteId
from cmk.ccc.user import UserId
from cmk.ccc.version import Edition
from cmk.gui.mkeventd.config_domain import ConfigDomainEventConsole
from cmk.gui.session_context import SuperUserContext, UserContext
from cmk.gui.utils.roles import UserPermissions
from cmk.gui.watolib.config_domain_name import (
    ABCConfigDomain,
    config_variable_registry,
    ConfigVariable,
    GlobalSettingsContext,
)
from cmk.gui.watolib.config_domains import ConfigDomainGUI
from cmk.gui.watolib.config_variable_groups import ConfigVariableGroupUserInterface
from cmk.gui.watolib.global_settings import (
    add_global_settings_change,
    affected_sites,
    global_settings_diff_text,
    is_available_in_global_settings,
    may_read,
)
from cmk.gui.watolib.pending_changes import PendingChanges, PendingChangesStore
from cmk.livestatus_client import SiteConfigurations
from cmk.rulesets.internal.form_specs import SimplePassword
from cmk.rulesets.v1.form_specs import Integer
from tests.testlib.unit.gui.web_test_app import SetConfig
from tests.unit.cmk.gui.helpers.config_sync_test_helper import get_site_configuration
from tests.unit.cmk.gui.helpers.config_variable_form_data_test_helper import (
    make_global_settings_context,
)

DEFAULTS = {"test_var": 1}


def _variable(
    domain: type[ABCConfigDomain] = ConfigDomainGUI, *, in_global_settings: bool = True
) -> ConfigVariable:
    return ConfigVariable(
        group=ConfigVariableGroupUserInterface,
        primary_domain=domain,
        ident="test_var",
        form_spec=lambda context: Integer(),  # noqa: ARG005
        in_global_settings=in_global_settings,
    )


def _always_activated(varname: str) -> bool:  # noqa: ARG001
    return True


@pytest.fixture(name="global_settings_context")
def fixture_global_settings_context() -> GlobalSettingsContext:
    return make_global_settings_context(Edition.COMMUNITY)


def test_variable_with_a_factory_default_is_available() -> None:
    assert is_available_in_global_settings(
        _variable(), default_values=DEFAULTS, is_activated=_always_activated
    )


def test_variable_without_a_factory_default_is_unavailable() -> None:
    assert not is_available_in_global_settings(
        _variable(), default_values={}, is_activated=_always_activated
    )


def test_variable_opting_out_of_the_global_settings_is_unavailable() -> None:
    assert not is_available_in_global_settings(
        _variable(in_global_settings=False),
        default_values=DEFAULTS,
        is_activated=_always_activated,
    )


def test_deactivated_variable_is_unavailable() -> None:
    assert not is_available_in_global_settings(
        _variable(),
        default_values=DEFAULTS,
        is_activated=lambda varname: False,  # noqa: ARG005
    )


@pytest.mark.usefixtures("load_config")
def test_variable_of_a_disabled_domain_is_unavailable(set_config: SetConfig) -> None:
    with set_config(mkeventd_enabled=False):
        assert not is_available_in_global_settings(
            _variable(ConfigDomainEventConsole),
            default_values=DEFAULTS,
            is_activated=_always_activated,
        )


@pytest.mark.usefixtures("load_config")
def test_variable_of_a_domain_outside_the_main_page_is_available(set_config: SetConfig) -> None:
    with set_config(mkeventd_enabled=True):
        assert is_available_in_global_settings(
            _variable(ConfigDomainEventConsole),
            default_values=DEFAULTS,
            is_activated=_always_activated,
        )


@pytest.mark.usefixtures("request_context")
def test_affected_sites_of_an_event_console_variable() -> None:
    with SuperUserContext():
        assert affected_sites(config_variable_registry["log_level"]) == ["NO_SITE"]


def test_affected_sites_of_an_ordinary_variable() -> None:
    assert affected_sites(config_variable_registry["wato_max_snapshots"]) is None


class _FakePendingChangesStore(PendingChangesStore):
    def __init__(self) -> None:
        self.sites: set[SiteId] = set()

    @override
    def append(self, site_id: SiteId, entry: Mapping[str, object]) -> None:
        self.sites.add(site_id)


def _sites_recording_a_site_specific_change(variable: ConfigVariable) -> set[SiteId]:
    store = _FakePendingChangesStore()
    add_global_settings_change(
        variable,
        text="Changed test_var",
        sites=[SiteId("remote")],
        pending_changes=PendingChanges(
            activation_sites=SiteConfigurations(
                {
                    SiteId("central"): get_site_configuration(SiteId("unit_remote_1")),
                    SiteId("remote"): get_site_configuration(SiteId("unit_remote_2")),
                }
            ),
            local_site=SiteId("central"),
            acting_user=UserId("harry"),
            store=store,
            hooks=(),
        ),
    )
    return store.sites


def test_a_site_specific_change_is_recorded_for_that_site_only() -> None:
    assert _sites_recording_a_site_specific_change(_variable()) == {SiteId("remote")}


def test_a_site_specific_change_of_a_variable_affecting_the_local_site_is_recorded_there_too() -> (
    None
):
    variable = ConfigVariable(
        group=ConfigVariableGroupUserInterface,
        primary_domain=ConfigDomainGUI,
        ident="test_var",
        form_spec=lambda context: Integer(),  # noqa: ARG005
        always_affects_local_site=True,
    )

    assert _sites_recording_a_site_specific_change(variable) == {
        SiteId("central"),
        SiteId("remote"),
    }


def test_the_event_console_actions_need_the_executables_permission(
    with_user: tuple[UserId, str],
) -> None:
    with UserContext(
        with_user[0],
        UserPermissions({}, {}, {}, []),
        explicit_permissions={"mkeventd.config"},
    ):
        assert not may_read(config_variable_registry["actions"])


def test_the_event_console_actions_are_readable_with_the_executables_permission(
    with_user: tuple[UserId, str],
) -> None:
    with UserContext(
        with_user[0],
        UserPermissions({}, {}, {}, []),
        explicit_permissions={"mkeventd.config", "wato.add_or_modify_executables"},
    ):
        assert may_read(config_variable_registry["actions"])


def test_diff_text_form_spec_value_changed(
    global_settings_context: GlobalSettingsContext,
) -> None:
    assert (
        global_settings_diff_text(
            _variable(),
            global_settings_context,
            {"test_var": 100},
            {"test_var": 66},
        )
        == 'Value of "test_var" changed from 100 to 66.'
    )


def test_diff_text_first_override_reads_as_added(
    global_settings_context: GlobalSettingsContext,
) -> None:
    assert (
        global_settings_diff_text(
            _variable(),
            global_settings_context,
            {},
            {"test_var": 66},
        )
        == 'Attribute "test_var" with value 66 added.'
    )


def test_diff_text_reset_reads_as_removed(
    global_settings_context: GlobalSettingsContext,
) -> None:
    assert (
        global_settings_diff_text(
            _variable(),
            global_settings_context,
            {"test_var": 100},
            {},
        )
        == 'Attribute "test_var" with value 100 removed.'
    )


def test_diff_text_form_spec_secret_is_redacted(
    global_settings_context: GlobalSettingsContext,
) -> None:
    config_variable = ConfigVariable(
        group=ConfigVariableGroupUserInterface,
        primary_domain=ConfigDomainGUI,
        ident="test_var",
        form_spec=lambda context: SimplePassword(),  # noqa: ARG005
    )
    diff_text = global_settings_diff_text(
        config_variable,
        global_settings_context,
        {"test_var": "old-secret"},
        {"test_var": "new-secret"},
    )
    assert diff_text == "Redacted secrets changed."
    assert "old-secret" not in diff_text
    assert "new-secret" not in diff_text
