#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="exhaustive-match"


from collections.abc import Mapping

from cmk.gui.agent_bakery import RulespecGroupMonitoringAgentsAgentPlugins
from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import HostRulespec, rulespec_registry
from cmk.gui.valuespec import Alternative, Dictionary, FixedValue, Migrate, TextInput
from cmk.gui.wato import MigrateToIndividualOrStoredPassword
from cmk.utils.rulesets.definition import RuleGroup


def _migrate_mk_msoffice(param: object) -> Mapping[str, str] | None:
    match param:
        case None:
            return None
        case {
            "client_id": _client_id,
            "tenant_id": _tenant_id,
            "client_secret": _client_secret,
        } as already_migrated:
            assert isinstance(already_migrated, Mapping)
            if set(already_migrated.keys()) != {"client_id", "tenant_id", "client_secret"}:
                raise ValueError(f"Unexpected keys in input: {already_migrated.keys()}")
            return already_migrated
        case {"user": user, "password": _password}:
            return {
                "client_id": f"Please provide valid client id (user was {user!r})",
                "tenant_id": "Please provide valid tenant id",
                "client_secret": "explicit_password",
            }
    raise ValueError(param)


def _valuespec_agent_config_mk_msoffice() -> Migrate[Mapping[str, str] | None]:
    return Migrate(
        valuespec=Alternative(
            title=_("MS Office 365 (Windows)"),
            help=_(
                "This plug-in can be used to collect information of all MS Office 365 licenses and serviceplans "
                "using the MgGraph PowerShell module."
            ),
            elements=[
                Dictionary(
                    title=_("Deploy MS Office 365 plug-in"),
                    elements=[
                        ("client_id", TextInput(title=_("ClientID"), allow_empty=False)),
                        ("tenant_id", TextInput(title=_("TenantId"), allow_empty=False)),
                        (
                            "client_secret",
                            MigrateToIndividualOrStoredPassword(
                                title=_("ClientSecret"),
                                help=_(
                                    "Enter the client secret explicitly or select one from the password store."
                                ),
                                allow_empty=False,
                            ),
                        ),
                    ],
                    required_keys=["client_id", "tenant_id", "client_secret"],
                ),
                FixedValue(
                    value=None,
                    title=_("Do not deploy plug-in for MS Office 365"),
                    totext=_("(disabled)"),
                ),
            ],
        ),
        migrate=_migrate_mk_msoffice,
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupMonitoringAgentsAgentPlugins,
        name=RuleGroup.AgentConfig("mk_msoffice"),
        valuespec=_valuespec_agent_config_mk_msoffice,
    )
)
