#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="type-arg"

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    HostRulespec,
    rulespec_registry,
    RulespecGroupMonitoringAgentsGenericOptions,
)
from cmk.gui.valuespec import (
    Age,
    Dictionary,
    DictionaryElements,
    ListOf,
    Migrate,
    TextInput,
)
from cmk.utils.mrpe_config import ensure_mrpe_configs
from cmk.utils.rulesets.definition import RuleGroup


def _regex_service_description() -> str:
    """All printable ASCII characters (32 - 126) except '~' (7E), since urllib.parse.quote does not
    encode '~' (RFC 3986)."""
    return "([\x20-\x7d])+$"


def _mrpe_elements() -> DictionaryElements:
    return (
        (
            "description",
            TextInput(
                title=_("Service name"),
                help=_(
                    "This will be used as service name within "
                    "Checkmk. It must be a unique name per host."
                ),
                allow_empty=False,
                regex=_regex_service_description(),
                regex_error=_(
                    "You can use any printable ASCII character except '~' here, since the "
                    "latter will cause problems in cache file names."
                ),
            ),
        ),
        (
            "cmdline",
            TextInput(
                title=_("Command line to execute"),
                help=_("This command will be executed on the target host."),
                size=40,
                try_max_width=True,
            ),
        ),
        (
            "interval",
            Age(
                title=_("Execution interval"),
                default_value=60,
                help=_(
                    "If this is option is enabled the actual check plug-in "
                    "will not be run every check cycle but just every time "
                    "the configured age has expired. Furthermore the plug-in "
                    "will be executed asynchronously as a background process. "
                    "This is useful for plug-ins that have a long execution "
                    "time."
                ),
                label=_("Run asynchronously, run at larger interval"),
            ),
        ),
    )


def _valuespec_agent_config_mrpe() -> Migrate:
    return Migrate(
        valuespec=ListOf(
            valuespec=Dictionary(
                elements=_mrpe_elements(),
                optional_keys=["interval"],
            ),
            title=_("Execute MRPE checks"),
            help=_(
                "The Checkmk agent supports executing Nagios plug-ins on the remote host like you might "
                "have done it before when monitoring via NRPE. This feature is called MRPE (MK's Remote Plug-in Executor). "
                "This rule can be used to configure the agent to execute plug-ins of your choice using the given arguments."
            ),
            add_label=_("Add plug-in"),
        ),
        migrate=ensure_mrpe_configs,
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupMonitoringAgentsGenericOptions,
        match_type="list",
        name=RuleGroup.AgentConfig("mrpe"),
        valuespec=_valuespec_agent_config_mrpe,
    )
)
