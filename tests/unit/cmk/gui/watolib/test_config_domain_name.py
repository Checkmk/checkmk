#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

import pytest

from cmk.ccc.site import SiteId
from cmk.ccc.version import Edition
from cmk.gui.valuespec import FixedValue
from cmk.gui.watolib.config_domain_name import (
    ConfigVariable,
    GlobalSettingsContext,
)
from cmk.gui.watolib.config_domains import ConfigDomainCore, ConfigDomainGUI, ConfigDomainOMD
from cmk.gui.watolib.config_variable_groups import (
    ConfigVariableGroupSiteManagement,
)
from cmk.livestatus_client import SiteConfigurations
from cmk.rulesets.v1.form_specs import FormSpec, Integer

DUMMY_CONTEXT = GlobalSettingsContext(
    target_site_id=SiteId("test-site"),
    edition_of_local_site=Edition.COMMUNITY,
    site_neutral_log_dir=Path(""),
    site_neutral_var_dir=Path(""),
    configured_sites=SiteConfigurations({}),
    configured_graph_timeranges=[],
)


def test_config_variable_add_domain() -> None:
    test_var = ConfigVariable(
        group=ConfigVariableGroupSiteManagement,
        primary_domain=ConfigDomainGUI,
        ident="test_var",
        valuespec=lambda context: FixedValue(None),
    )
    test_var.add_config_domain_affected_by_change(ConfigDomainCore)
    test_var.add_config_domain_affected_by_change(ConfigDomainOMD)
    assert [config_domain.ident() for config_domain in test_var.all_domains()] == [
        ConfigDomainGUI.ident(),
        ConfigDomainCore.ident(),
        ConfigDomainOMD.ident(),
    ]


def test_config_variable_add_domain_unique() -> None:
    test_var = ConfigVariable(
        group=ConfigVariableGroupSiteManagement,
        primary_domain=ConfigDomainGUI,
        ident="test_var",
        valuespec=lambda context: FixedValue(None),
    )
    test_var.add_config_domain_affected_by_change(ConfigDomainCore)
    test_var.add_config_domain_affected_by_change(ConfigDomainCore)
    assert sorted([config_domain.ident() for config_domain in test_var.all_domains()]) == sorted(
        [
            ConfigDomainGUI.ident(),
            ConfigDomainCore.ident(),
        ]
    )


def test_config_variable_valuespec_backend() -> None:
    test_var = ConfigVariable(
        group=ConfigVariableGroupSiteManagement,
        primary_domain=ConfigDomainGUI,
        ident="test_var",
        valuespec=lambda context: FixedValue(None),
    )
    assert isinstance(test_var.value_model(DUMMY_CONTEXT), FixedValue)


def test_config_variable_form_spec_backend() -> None:
    test_var = ConfigVariable(
        group=ConfigVariableGroupSiteManagement,
        primary_domain=ConfigDomainGUI,
        ident="test_var",
        form_spec=lambda context: Integer(),
    )
    assert isinstance(test_var.value_model(DUMMY_CONTEXT), FormSpec)


def test_config_variable_valuespec_on_form_spec_raises() -> None:
    test_var = ConfigVariable(
        group=ConfigVariableGroupSiteManagement,
        primary_domain=ConfigDomainGUI,
        ident="test_var",
        form_spec=lambda context: Integer(),
    )
    with pytest.raises(RuntimeError, match="declared with a form spec"):
        test_var.valuespec(DUMMY_CONTEXT)


def test_config_variable_requires_exactly_one_backend() -> None:
    with pytest.raises(ValueError, match="Exactly one"):
        ConfigVariable(
            group=ConfigVariableGroupSiteManagement,
            primary_domain=ConfigDomainGUI,
            ident="test_var",
        )

    with pytest.raises(ValueError, match="Exactly one"):
        ConfigVariable(
            group=ConfigVariableGroupSiteManagement,
            primary_domain=ConfigDomainGUI,
            ident="test_var",
            valuespec=lambda context: FixedValue(None),
            form_spec=lambda context: Integer(),
        )
