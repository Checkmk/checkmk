#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    IndividualOrStoredPassword,
    rulespec_group_registry,
    RulespecGroup,
    RulespecSubGroup,
)
from cmk.gui.valuespec import CascadingDropdown, Dictionary, Integer, TextInput, Transform


@rulespec_group_registry.register
class RulespecGroupVMCloudContainer(RulespecGroup):
    @property
    def name(self):
        return "vm_cloud_container"

    @property
    def title(self):
        return _("VM, Cloud, Container")

    @property
    def help(self):
        return _("Integrate with VM, cloud or container platforms")


@rulespec_group_registry.register
class RulespecGroupDatasourcePrograms(RulespecGroup):
    @property
    def name(self):
        return "datasource_programs"

    @property
    def title(self):
        return _("Other integrations")

    @property
    def help(self):
        return _("Integrate platforms using special agents, e.g. SAP R/3")


@rulespec_group_registry.register
class RulespecGroupDatasourceProgramsOS(RulespecSubGroup):
    @property
    def main_group(self):
        return RulespecGroupDatasourcePrograms

    @property
    def sub_group_name(self):
        return "os"

    @property
    def title(self):
        return _("Operating systems")


@rulespec_group_registry.register
class RulespecGroupDatasourceProgramsApps(RulespecSubGroup):
    @property
    def main_group(self):
        return RulespecGroupDatasourcePrograms

    @property
    def sub_group_name(self):
        return "apps"

    @property
    def title(self):
        return _("Applications")


@rulespec_group_registry.register
class RulespecGroupDatasourceProgramsCloud(RulespecSubGroup):
    @property
    def main_group(self):
        return RulespecGroupDatasourcePrograms

    @property
    def sub_group_name(self):
        return "cloud"

    @property
    def title(self):
        return _("Cloud based environments")


class RulespecGroupDatasourceProgramsContainer(RulespecSubGroup):
    @property
    def main_group(self):
        return RulespecGroupDatasourcePrograms

    @property
    def sub_group_name(self):
        return "container"

    @property
    def title(self):
        return _("Containerization")


@rulespec_group_registry.register
class RulespecGroupDatasourceProgramsCustom(RulespecSubGroup):
    @property
    def main_group(self):
        return RulespecGroupDatasourcePrograms

    @property
    def sub_group_name(self):
        return "custom"

    @property
    def title(self):
        return _("Custom integrations")


@rulespec_group_registry.register
class RulespecGroupDatasourceProgramsHardware(RulespecSubGroup):
    @property
    def main_group(self):
        return RulespecGroupDatasourcePrograms

    @property
    def sub_group_name(self):
        return "hw"

    @property
    def title(self):
        return _("Hardware")


@rulespec_group_registry.register
class RulespecGroupDatasourceProgramsTesting(RulespecSubGroup):
    @property
    def main_group(self):
        return RulespecGroupDatasourcePrograms

    @property
    def sub_group_name(self):
        return "testing"

    @property
    def title(self):
        return _("Testing")


def api_request_authentication():
    return (
        "auth_basic",
        Transform(
            valuespec=CascadingDropdown(
                title=_("Authentication"),
                choices=[
                    (
                        "auth_login",
                        _("Basic authentication"),
                        Dictionary(
                            elements=[
                                (
                                    "username",
                                    TextInput(
                                        title=_("Login username"),
                                        allow_empty=False,
                                    ),
                                ),
                                (
                                    "password",
                                    IndividualOrStoredPassword(
                                        title=_("Password"),
                                        allow_empty=False,
                                    ),
                                ),
                            ],
                            optional_keys=[],
                        ),
                    ),
                    (
                        "auth_token",
                        _("Token authentication"),
                        Dictionary(
                            elements=[
                                (
                                    "token",
                                    IndividualOrStoredPassword(
                                        title=_("Login token"),
                                        allow_empty=False,
                                    ),
                                ),
                            ],
                            optional_keys=[],
                        ),
                    ),
                ],
            ),
            forth=lambda v: ("auth_login", v) if "username" in v else v,
        ),
    )


def api_request_connection_elements(help_text: str, default_port: int):
    return [
        ("port", Integer(title=_("Port"), default_value=default_port)),
        (
            "path-prefix",
            TextInput(title=_("Custom path prefix"), help=help_text, allow_empty=False),
        ),
    ]
