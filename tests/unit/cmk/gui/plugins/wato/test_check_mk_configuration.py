#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from pathlib import Path
from unittest.mock import patch

from livestatus import SiteConfigurations

from cmk.ccc.site import omd_site, SiteId
from cmk.ccc.version import Edition, edition
from cmk.gui.plugins.wato.utils import ConfigVariableGroupUserInterface
from cmk.gui.theme.choices import theme_choices
from cmk.gui.valuespec import DropdownChoice
from cmk.gui.wato._check_mk_configuration import ConfigVariableUseNewDescriptionsFor
from cmk.gui.watolib.config_domain_name import config_variable_registry, GlobalSettingsContext
from cmk.gui.watolib.config_domains import ConfigDomainGUI
from cmk.gui.watolib.sample_config import USE_NEW_DESCRIPTIONS_FOR_SETTING
from cmk.gui.watolib.utils import site_neutral_path
from cmk.utils.paths import log_dir, omd_root, var_dir


def test_ui_theme_registration() -> None:
    var = config_variable_registry["ui_theme"]
    assert isinstance(var.primary_domain(), ConfigDomainGUI)
    assert var.group() == ConfigVariableGroupUserInterface

    valuespec = var.valuespec(
        GlobalSettingsContext(
            target_site_id=omd_site(),
            edition_of_local_site=edition(omd_root),
            site_neutral_log_dir=site_neutral_path(log_dir),
            site_neutral_var_dir=site_neutral_path(var_dir),
            configured_sites=SiteConfigurations({}),
            configured_graph_timeranges=[],
        )
    )
    assert isinstance(valuespec, DropdownChoice)
    assert valuespec.choices() == theme_choices()


def test_ui_theme_default_value() -> None:
    var = config_variable_registry["ui_theme"]

    default_setting = var.primary_domain().default_globals()[var.ident()]
    assert default_setting == "modern-dark"

    with patch(
        "cmk.gui.wato._check_mk_configuration.theme_choices",
        return_value=[("modern-dark", "Dark")],
    ):
        assert (
            var.valuespec(
                GlobalSettingsContext(
                    target_site_id=omd_site(),
                    edition_of_local_site=edition(omd_root),
                    site_neutral_log_dir=site_neutral_path(log_dir),
                    site_neutral_var_dir=site_neutral_path(var_dir),
                    configured_sites=SiteConfigurations({}),
                    configured_graph_timeranges=[],
                )
            ).value_to_html(default_setting)
            == "Dark"
        )


# TODO: Was in the sample config, but not available for selection in the UI
#  Excluded for now to test the status-quo, but needs to be investigated if it needs be added
#  to the selection
_KNOWN_EXCEPTIONS = frozenset(["megaraid_vdisks"])

DUMMY_CONTEXT = GlobalSettingsContext(
    target_site_id=SiteId("test-site"),
    edition_of_local_site=Edition.COMMUNITY,
    site_neutral_log_dir=Path(""),
    site_neutral_var_dir=Path(""),
    configured_sites=SiteConfigurations({}),
    configured_graph_timeranges=[],
)


def test_use_new_descriptions_for_sample_config_readable() -> None:
    value_spec = ConfigVariableUseNewDescriptionsFor.valuespec(DUMMY_CONTEXT)

    sample_config = USE_NEW_DESCRIPTIONS_FOR_SETTING["use_new_descriptions_for"]
    sample_config_as_ui_model = value_spec.transform_value(
        USE_NEW_DESCRIPTIONS_FOR_SETTING["use_new_descriptions_for"]
    )
    value_spec.validate_value(sample_config_as_ui_model, "")
    value_spec.validate_datatype(sample_config_as_ui_model, "")

    for plugin_name, expected_selected in sample_config.items():
        if plugin_name in _KNOWN_EXCEPTIONS:
            continue
        assert sample_config_as_ui_model[plugin_name] == expected_selected


def test_use_new_descriptions_sample_config_same_entries_as_ui_selection() -> None:
    """Ensure sample config and UI selection of plugins for new descriptions are in sync"""
    value_spec = ConfigVariableUseNewDescriptionsFor.valuespec(DUMMY_CONTEXT)

    assert isinstance(value_spec.default_value(), dict)
    ui_selection = value_spec.default_value().keys()
    sample_config_selection = (
        set(USE_NEW_DESCRIPTIONS_FOR_SETTING["use_new_descriptions_for"].keys()) - _KNOWN_EXCEPTIONS
    )
    assert sorted(ui_selection) == sorted(sample_config_selection)
