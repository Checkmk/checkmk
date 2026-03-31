#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.gui.agent_bakery import RulespecGroupMonitoringAgentsWindowsAgent
from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import HostRulespec, rulespec_registry
from cmk.gui.valuespec import Checkbox, Dictionary, DropdownChoice, Integer, Migrate
from cmk.utils.rulesets.definition import RuleGroup

_ValueType = int | str | bool


def _logging_level_to_dict(v: str | dict[str, _ValueType]) -> dict[str, _ValueType]:
    """
    The str originates from earlier versions of the Setup, pre-2.2.
    Currently valuespec is a dict.

    >>> _logging_level_to_dict("yes")
    {'logging_level': 'yes'}
    >>> _logging_level_to_dict("no")
    {'logging_level': 'no'}
    >>> _logging_level_to_dict("all")
    {'logging_level': 'all'}
    >>> _logging_level_to_dict({"z":3})
    {'z': 3}
    """
    if isinstance(v, dict):
        return v

    if isinstance(v, str):
        if v in {"yes", "no", "all"}:
            return {"logging_level": v}

    return {}


def _valuespec_agent_config_logging() -> Migrate[dict[str, int | str | bool]]:
    return Migrate(
        valuespec=Dictionary(
            title=_("Windows agent logging"),
            elements=[
                (
                    "logging_level",
                    DropdownChoice(
                        title=_("Logging level"),
                        label=_("Set the logging level for Windows agent"),
                        help=_(
                            "This setting determines how detailed the log file of the Windows agent will be."
                        ),
                        choices=[
                            ("no", _("Write to log file only most important events")),
                            ("yes", _("Write to log file all important events and all warnings")),
                            ("all", _("Write to log file everything")),
                        ],
                        default_value="yes",
                    ),
                ),
                (
                    "max_log_file_count",
                    Integer(
                        title=_("Maximal number of log files to backup"),
                        default_value=5,
                        help=_(
                            "Number of log files used during log rotation as a backup. "
                            "Once this number of log files is exceeded, "
                            "the oldest log file will be deleted."
                        ),
                        minvalue=0,
                        maxvalue=64,
                    ),
                ),
                (
                    "max_log_file_size",
                    Integer(
                        title=_("Maximal log file size"),
                        default_value=8000000,
                        help=_("Maximal size of a log file"),
                        minvalue=256 * 1024,
                        maxvalue=256 * 1024 * 1024,
                    ),
                ),
                (
                    "log_to_windbg",
                    Checkbox(
                        title=_("Windows debugging"),
                        label=_("write log messages to the Windows debugging interface"),
                        default_value=False,
                        help=_(
                            "Enable/Disable logging to Windows debugging interface. Off by default. View with <i>WinDbg</i>"
                        ),
                    ),
                ),
            ],
        ),
        migrate=_logging_level_to_dict,
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupMonitoringAgentsWindowsAgent,
        match_type="dict",
        name=RuleGroup.AgentConfig("logging"),
        valuespec=_valuespec_agent_config_logging,
    )
)
