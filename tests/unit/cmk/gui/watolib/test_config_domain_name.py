#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.gui.watolib.config_domain_name import ConfigVariable
from cmk.gui.watolib.config_domains import ConfigDomainCore, ConfigDomainGUI, ConfigDomainOMD
from cmk.gui.watolib.config_variable_groups import (
    ConfigVariableGroupSiteManagement,
)
from cmk.rulesets.v1.form_specs import Integer


def test_config_variable_add_domain() -> None:
    test_var = ConfigVariable(
        group=ConfigVariableGroupSiteManagement,
        primary_domain=ConfigDomainGUI,
        ident="test_var",
        form_spec=lambda context: Integer(),  # noqa: ARG005
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
        form_spec=lambda context: Integer(),  # noqa: ARG005
    )
    test_var.add_config_domain_affected_by_change(ConfigDomainCore)
    test_var.add_config_domain_affected_by_change(ConfigDomainCore)
    assert sorted([config_domain.ident() for config_domain in test_var.all_domains()]) == sorted(
        [
            ConfigDomainGUI.ident(),
            ConfigDomainCore.ident(),
        ]
    )
