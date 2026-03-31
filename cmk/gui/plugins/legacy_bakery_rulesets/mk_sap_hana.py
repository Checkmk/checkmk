#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.gui.agent_bakery import RulespecGroupMonitoringAgentsAgentPlugins
from cmk.gui.i18n import _
from cmk.gui.valuespec import (
    Alternative,
    Dictionary,
    DropdownChoice,
    FixedValue,
    ID,
    ListOf,
    TextInput,
    Tuple,
)
from cmk.gui.wato import MigrateToIndividualOrStoredPassword
from cmk.gui.watolib.rulespecs import HostRulespec, rulespec_registry
from cmk.utils.rulesets.definition import RuleGroup


def _valuespec_agent_config_mk_sap_hana() -> Alternative:
    return Alternative(
        title=_("SAP HANA"),
        help=_(
            "This will deploy and configure the Checkmk agent plug-in <tt>mk_sap_hana</tt>. "
            "To make this plug-in work, you have to configure default credentials that are used "
            "for all databases or configure credentials per database. To configure credentials "
            "specify USERSTOREKEY or USER and PASSWORD, i.e. USERSTOREKEY=SVAMON and SID=I08 "
            "means we need a key for SVAMONI08 in the HDB userstore specified in "
            "$MK_CONFDIR/sap_hana.cfg. Moreover you can configure 'RUNAS' with the following "
            "values 'agent' or 'instance'. The latter one is default."
            " Use the FQDN in the query if HOSTNAME is not set, otherwise the short host name."
        ),
        elements=[
            Dictionary(
                title=_("Deploy the SAP HANA plug-in"),
                optional_keys=["runas", "credentials_sap_connect"],
                elements=[
                    (
                        "credentials",
                        Alternative(
                            title=_("Credentials"),
                            elements=[
                                Alternative(
                                    title=_("Default credentials"),
                                    elements=[
                                        Tuple(
                                            title=_("User and password"),
                                            elements=[
                                                TextInput(
                                                    title=_("Username"),
                                                    allow_empty=False,
                                                ),
                                                MigrateToIndividualOrStoredPassword(
                                                    title=_("Password"),
                                                    allow_empty=False,
                                                ),
                                            ],
                                        ),
                                        TextInput(
                                            title=_("User store key"),
                                            allow_empty=False,
                                        ),
                                    ],
                                ),
                                ListOf(
                                    valuespec=Tuple(
                                        title=_("Databases"),
                                        elements=[
                                            ID(
                                                title=_("SID"),
                                                allow_empty=False,
                                                size=12,
                                            ),
                                            TextInput(
                                                title=_("Instance"),
                                                allow_empty=False,
                                                size=12,
                                            ),
                                            TextInput(
                                                title=_("Database"),
                                                allow_empty=False,
                                            ),
                                            Alternative(
                                                elements=[
                                                    Tuple(
                                                        title=_("User and password"),
                                                        elements=[
                                                            TextInput(
                                                                title=_("Username"),
                                                                allow_empty=False,
                                                            ),
                                                            MigrateToIndividualOrStoredPassword(
                                                                title=_("Password"),
                                                                allow_empty=False,
                                                            ),
                                                        ],
                                                    ),
                                                    TextInput(
                                                        title=_("User store key"),
                                                        allow_empty=False,
                                                    ),
                                                ]
                                            ),
                                        ],
                                    ),
                                    title=_("Credentials for selected databases"),
                                ),
                            ],
                        ),
                    ),
                    (
                        "credentials_sap_connect",
                        Tuple(
                            title=_("Credentials for Connect (ODBC interface)"),
                            elements=[
                                TextInput(title=_("User"), allow_empty=False),
                                MigrateToIndividualOrStoredPassword(
                                    title=_("Password"),
                                    allow_empty=False,
                                ),
                            ],
                        ),
                    ),
                    (
                        "runas",
                        DropdownChoice(
                            title=_("Run as"),
                            choices=[
                                ("instance", _("Instance")),
                                ("agent", _("Agent")),
                            ],
                        ),
                    ),
                ],
            ),
            FixedValue(
                value=None,
                title=_("Do not deploy the SAP HANA plug-in"),
                totext=_("(disabled)"),
            ),
        ],
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupMonitoringAgentsAgentPlugins,
        name=RuleGroup.AgentConfig("mk_sap_hana"),
        valuespec=_valuespec_agent_config_mk_sap_hana,
    )
)
