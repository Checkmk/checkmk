#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="type-arg"

from cmk.gui.i18n import _
from cmk.gui.mkeventd import syslog_facilities
from cmk.gui.valuespec import (
    Age,
    Alternative,
    CascadingDropdown,
    Checkbox,
    Dictionary,
    DropdownChoice,
    Filesize,
    FixedValue,
    ListOf,
    ListOfStrings,
    Migrate,
    MonitoringState,
    NetworkPort,
    TextInput,
    Transform,
)
from cmk.gui.wato import RulespecGroupCheckParametersApplications
from cmk.gui.watolib.rulespecs import (
    CheckParameterRulespecWithoutItem,
)


def _match_method(x: object) -> int:
    match x:
        case tuple():
            return 4
        case "":
            return 0
        case "spool:":
            return 2
        case str() as local if local.startswith("spool:"):
            return 3
    return 1


def _parameter_valuespec_logwatch_ec() -> Migrate:
    return Migrate(
        valuespec=Dictionary(
            title=_("Forward messages to Event Console"),
            help=_(
                "Instead of using the regular logwatch check all lines received by logwatch can be forwarded to a Checkmk Event Console daemon to be processed. The target Event Console can be configured for each host in a separate rule."
            ),
            elements=[
                (
                    "activation",
                    Checkbox(
                        title=_("Disable or enable forwarding"),
                        label=_("Enable forwarding"),
                        false_label=_("Messages are handled by logwatch."),
                        true_label=_(
                            "Messages are forwarded according to below or inherited settings."
                        ),
                    ),
                ),
                (
                    "method",
                    # TODO: Clean this up to some CascadingDropdown()
                    Alternative(
                        title=_("Forwarding method"),
                        elements=[
                            FixedValue(
                                value="",
                                title=_(
                                    "Local: Send events to local Event Console in same OMD site"
                                ),
                                totext=_("Directly forward to Event Console"),
                            ),
                            TextInput(
                                title=_(
                                    "Local: Send events to local Event Console into Unix socket"
                                ),
                                allow_empty=False,
                            ),
                            FixedValue(
                                value="spool:",
                                title=_(
                                    "Local: Spooling - Send events to local Event Console in same OMD site"
                                ),
                                totext=_("Spool to Event Console"),
                            ),
                            Transform(
                                valuespec=TextInput(
                                    allow_empty=False,
                                ),
                                title=_(
                                    "Local: Spooling - Send events to local Event Console into given spool directory"
                                ),
                                to_valuespec=lambda x: x[6:],
                                # remove prefix
                                from_valuespec=lambda x: "spool:" + x,  # add prefix
                            ),
                            CascadingDropdown(
                                title=_("Remote: Send events to remote syslog host"),
                                choices=[
                                    (
                                        "tcp",
                                        _("Send via TCP"),
                                        Dictionary(
                                            elements=[
                                                (
                                                    "address",
                                                    TextInput(
                                                        title=_("Address"),
                                                        allow_empty=False,
                                                    ),
                                                ),
                                                (
                                                    "port",
                                                    NetworkPort(
                                                        title=_("Port"),
                                                        default_value=514,
                                                    ),
                                                ),
                                                (
                                                    "spool",
                                                    Dictionary(
                                                        title=_(
                                                            "Spool messages that could not be sent"
                                                        ),
                                                        help=_(
                                                            "Messages that cannot be forwarded, e.g. when the target Event Console is not running, can temporarily be stored locally. Forwarding is tried again on next execution. When messages are spooled, the check will go into WARNING state. In case messages are dropped by the rules below, the check will shortly go into CRITICAL state for this execution."
                                                        ),
                                                        elements=[
                                                            (
                                                                "max_age",
                                                                Age(
                                                                    title=_(
                                                                        "Maximum spool duration"
                                                                    ),
                                                                    help=_(
                                                                        "Messages that are spooled longer than this time will be thrown away."
                                                                    ),
                                                                    default_value=60
                                                                    * 60
                                                                    * 24
                                                                    * 7,  # 1 week should be fine (if size is not exceeded)
                                                                ),
                                                            ),
                                                            (
                                                                "max_size",
                                                                Filesize(
                                                                    title=_("Maximum spool size"),
                                                                    help=_(
                                                                        "When the total size of spooled messages exceeds this number, the oldest "
                                                                        "messages of the currently spooled messages is thrown away until the left "
                                                                        "messages have the half of the maximum size."
                                                                    ),
                                                                    default_value=500000,  # do not save more than 500k of message
                                                                ),
                                                            ),
                                                        ],
                                                        optional_keys=[],
                                                    ),
                                                ),
                                            ],
                                            optional_keys=["spool"],
                                        ),
                                    ),
                                    (
                                        "udp",
                                        _("Send via UDP"),
                                        Dictionary(
                                            elements=[
                                                (
                                                    "address",
                                                    TextInput(
                                                        title=_("Address"),
                                                        allow_empty=False,
                                                    ),
                                                ),
                                                (
                                                    "port",
                                                    NetworkPort(
                                                        title=_("Port"),
                                                        default_value=514,
                                                    ),
                                                ),
                                            ],
                                            optional_keys=[],
                                        ),
                                    ),
                                ],
                            ),
                        ],
                        match=_match_method,
                    ),
                ),
                (
                    "facility",
                    DropdownChoice(
                        title=_("Syslog facility for forwarded messages"),
                        help=_(
                            "When forwarding messages and no facility can be extracted from the "
                            "message this facility is used."
                        ),
                        choices=syslog_facilities,
                        default_value=17,  # local1
                    ),
                ),
                (
                    "restrict_logfiles",
                    ListOfStrings(
                        title=_("Restrict log files (prefix matching regular expressions)"),
                        help=_(
                            'Put the item names of the log files here. For example "System$" '
                            'to select the service "LOG System". You can use regular expressions '
                            "which must match the beginning of the log file name."
                        ),
                    ),
                ),
                (
                    "monitor_logfilelist",
                    Checkbox(
                        title=_("Monitoring of forwarded log files"),
                        label=_("Warn if list of forwarded log files changes"),
                        help=_(
                            "If this option is enabled, the check monitors the list of forwarded log files and will warn you if at any time a log file is missing or exceeding when compared to the initial list that was snapshotted during service detection. Re-inventorize this check in order to make it OK again."
                        ),
                    ),
                ),
                (
                    "expected_logfiles",
                    ListOf(
                        valuespec=TextInput(),
                        title=_("List of expected log files"),
                        help=_(
                            "When the monitoring of forwarded log files is "
                            "enabled, the check verifies that all of the log "
                            "files listed here are reported by the monitored "
                            "system."
                        ),
                    ),
                ),
                (
                    "logwatch_reclassify",
                    Checkbox(
                        title=_("Reclassify messages before forwarding them to the EC"),
                        label=_("Apply logwatch patterns"),
                        help=_(
                            "If this option is enabled, the logwatch lines are first reclassified by the logwatch patterns before they are sent to the Event Console. If you reclassify specific lines to IGNORE they are not forwarded to the Event Console. This takes the burden from the Event Console to process the message itself through all of its rule sets. The reclassification of each line takes into account from which log file the message originates. So you can create logwatch reclassification rules specifically designed for a log file <i>access.log</i>, which do not apply to other log files."
                        ),
                    ),
                ),
                (
                    "monitor_logfile_access_state",
                    MonitoringState(
                        title=_("State if a log file cannot be read"),
                        default_value=2,
                        help=_(
                            "Choose the Checkmk state in case any of the forwarded log files cannot be read"
                        ),
                    ),
                ),
                (
                    "separate_checks",
                    Checkbox(
                        title=_("Create a separate check for each log file"),
                        label=_("Separate check"),
                        help=_(
                            "If this option is enabled, there will be one "
                            "separate check for each log file found during "
                            "the service discovery. This option also changes "
                            "the behavior for unknown log files. The default "
                            "logwatch check forwards all log files to the "
                            "Event Console, even log files which were not "
                            "known during the service discovery. Creating one "
                            "check per log file changes this behavior so that "
                            "any data from unknown log files is discarded."
                        ),
                    ),
                ),
            ],
            # host name and service level provided by nasty hack. Grep for "cmk_postprocessed"
            ignored_keys=["host_name", "service_level"],
        ),
        migrate=lambda p: {"activation": False} if isinstance(p, str) else p,
    )


RulespecLogwatchEC = CheckParameterRulespecWithoutItem(
    check_group_name="logwatch_ec",
    group=RulespecGroupCheckParametersApplications,
    parameter_valuespec=_parameter_valuespec_logwatch_ec,
    title=lambda: _("Logwatch Event Console forwarding"),
)
