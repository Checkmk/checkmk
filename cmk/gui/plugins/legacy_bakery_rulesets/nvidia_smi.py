#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.gui.agent_bakery import RulespecGroupMonitoringAgentsAgentPlugins
from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import HostRulespec, rulespec_registry
from cmk.gui.valuespec import Alternative, Dictionary, FixedValue, TextInput
from cmk.utils.rulesets.definition import RuleGroup


def _valuespec_agent_config_nvidia_smi() -> Alternative:
    return Alternative(
        title=_("Nvidia GPU monitoring (Linux, Windows)"),
        help=_(
            "This will deploy the agent plug-in <tt>nvidia_smi</tt> used for monitoring Nvidia GPUs."
        ),
        elements=[
            Dictionary(
                title=_("Deploy the nvidia_smi agent plug-in"),
                elements=[
                    (
                        "nvidia_smi_path",
                        TextInput(
                            title=_("Path to nvidia-smi.exe (Windows only)"),
                            help=_(
                                "Put the path to the nvidia-smi.exe executable here, e.g. "
                                "C:\\Program Files\\NVIDIA Corporation\\NVSMI\\nvidia-smi.exe. "
                                "Under Linux, the relevant executable is usually defined in the "
                                "PATH variable. Therefore, this setting is ignored under Linux."
                            ),
                            allow_empty=False,
                            regex=r"^[A-Za-z0-9\._\\ :-]+$",
                            regex_error=_("You have used an invalid character"),
                        ),
                    ),
                ],
                optional_keys=False,
            ),
            FixedValue(
                value=None,
                title=_("Do not deploy the nvidia_smi agent plug-in"),
                totext=_("(disabled)"),
            ),
        ],
        default_value={
            "nvidia_smi_path": r"C:\Program Files\NVIDIA Corporation\NVSMI\nvidia-smi.exe"
        },
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupMonitoringAgentsAgentPlugins,
        name=RuleGroup.AgentConfig("nvidia_smi"),
        valuespec=_valuespec_agent_config_nvidia_smi,
    )
)
