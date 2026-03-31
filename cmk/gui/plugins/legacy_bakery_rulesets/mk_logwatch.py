#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="type-arg"

import re

from cmk.gui.agent_bakery import RulespecGroupMonitoringAgentsAgentPlugins
from cmk.gui.exceptions import MKUserError
from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import HostRulespec, rulespec_registry
from cmk.gui.valuespec import (
    Age,
    Alternative,
    Checkbox,
    Dictionary,
    DropdownChoice,
    Filesize,
    FixedValue,
    HostAddress,
    ID,
    Integer,
    ListOf,
    ListOfStrings,
    TextInput,
    Tuple,
)
from cmk.utils.rulesets.definition import RuleGroup


def _validate_patterns(value: tuple[str, str], varprefix: str) -> None:
    state, pattern = value
    # SUP-11802: The REWRITE state pattern is not a regex so we should not run the validation on it
    if state == "R":
        return
    # Check if the pattern is a valid regex in any other case
    try:
        re.compile(pattern)
    except re.error as e:
        raise MKUserError(varprefix, _("Invalid regular expression: %s") % e)


def _agent_config_mk_logwatch_valuespec_cluster_section() -> ListOf:
    return ListOf(
        valuespec=Dictionary(
            elements=[
                (
                    "name",
                    ID(
                        title=_("Name of the cluster"),
                        size=40,
                        allow_empty=False,
                    ),
                ),
                (
                    "ips",
                    ListOfStrings(
                        title=_("Cluster node IPs"),
                        valuespec=HostAddress(
                            title=_("IPv4/IPv6 address"),
                            allow_host_name=False,
                            allow_empty=False,
                        ),
                        orientation="horizontal",
                        allow_empty=False,
                    ),
                ),
            ],
            optional_keys=False,
        ),
        title=_("Specify mappings of remote IPs to cluster names"),
        help=_(
            "With this option activated cluster node IPs "
            "may be mapped to a cluster. In case the monitoring site "
            "is operated in a failover cluster configuration this option "
            "is required to prevent from potentially duplicated log entries."
        ),
        add_label=_("Add cluster mapping"),
    )


def validate_python_encoding(encoding_name: str, varprefix: str) -> None:
    try:
        "".encode(encoding_name)
    except (LookupError, UnicodeEncodeError):
        raise MKUserError(varprefix, _('"%s" is not a valid python encoding.') % encoding_name)


def _agent_config_mk_logwatch_valuespec_file_section() -> Dictionary:
    return Dictionary(
        title=_("Configure a log file section"),
        elements=[
            (
                "logfiles",
                ListOfStrings(
                    title=_(
                        "Patterns for log files to monitor (allowing <tt>*</tt> and <tt>?</tt>)"
                    ),
                    valuespec=TextInput(
                        size=80,
                    ),
                    allow_empty=False,
                ),
            ),
            (
                "regex",
                Tuple(
                    title=_("Regular expression for log file filtering"),
                    help=_(
                        "Regular expression which is used to narrow down the selected files further. "
                        "Applies to the selected log file paths."
                    ),
                    show_titles=True,
                    orientation="horizontal",
                    elements=[
                        DropdownChoice(
                            title=_("Case sensitivity"),
                            choices=[
                                ("regex", _("Case sensitive")),
                                ("iregex", _("Case insensitive")),
                            ],
                        ),
                        TextInput(
                            title=_("Pattern (Regex)"),
                            size=64,
                        ),
                    ],
                ),
            ),
            (
                "maxlinesize",
                Integer(
                    title=_("Restrict the length of the lines"),
                    help=_(
                        "Lines longer then this number of characters will be truncated to the "
                        "configured length before parsing. The word <tt>[TRUNCATED]</tt> will be "
                        "appended to each such line."
                    ),
                    unit=_("Characters"),
                    minvalue=1,
                    default_value=500,
                ),
            ),
            (
                "maxfilesize",
                Filesize(
                    title=_("Watch the total size of the log file"),
                    help=_(
                        "If the total size of the log file exceeds this configured size "
                        "then an artificial warning message will be introduced. That message "
                        "will be repeated every time that the file has again grown by the configured size. "
                        "That way you can detect a broken log file rotation or the like."
                    ),
                    minvalue=1,
                    default_value=100 * 1024 * 1024,
                ),
            ),
            (
                "maxlines",
                Integer(
                    title=_("Restrict number of processed messages per cycle"),
                    help=_(
                        "With this option activated at most <i>X</i> messages "
                        "are processed per monitoring cycle."
                    ),
                    minvalue=1,
                    default_value=50000,
                ),
            ),
            (
                "maxtime",
                Age(
                    title=_("Restrict runtime of log file parsing"),
                    help=_(
                        "With this option activated at most the configured time is being "
                        "spent for each log file in question. "
                    ),
                    minvalue=1,
                    default_value=10,
                ),
            ),
            (
                "overflow",
                DropdownChoice(
                    title=_("In case of an overflow..."),
                    help=_(
                        "This option is only relevant when you limit the number of messages or the parsing time. It sets the behavior in case of too many new messages in a log file."
                    ),
                    choices=[
                        ("C", _("Skip exceeding messages, create one critical message")),
                        ("W", _("Skip exceeding messages, create one warning message")),
                        ("I", _("Silently skip exceeding messages")),
                    ],
                ),
            ),
            (
                "context",
                DropdownChoice(
                    title=_("Handling of context messages"),
                    help=_(
                        "If context messages are enabled and at least one relevant message "
                        "is found (classified as WARN or CRIT), then all new messages "
                        "of the current cycle are being transferred. This makes log file analysis "
                        "on the monitoring server simpler, but can result in much traffic on "
                        "log files with frequent new messages."
                    ),
                    choices=[
                        (True, _("Do transfer context")),
                        (False, _("Do not transfer context")),
                    ],
                ),
            ),
            (
                "maxcontextlines",
                Tuple(
                    title=_("Limit the amount of context data sent to the monitoring server"),
                    elements=[
                        Integer(title=_("Number of context lines before messages")),
                        Integer(title=_("Number of context lines after messages")),
                    ],
                ),
            ),
            (
                "maxoutputsize",
                Filesize(
                    title=_("Limit the amount of data sent to the monitoring server"),
                    help=_(
                        "Configure the maximum number of bytes that is sent to the monitoring "
                        "site. By default, the limit is set to the maximum size of the file "
                        "storing the log lines on the server side, which is 500 KB"
                    ),
                    minvalue=1,
                    default_value=500000,
                ),
            ),
            (
                "fromstart",
                DropdownChoice(
                    title=_("Process new log files from the beginning"),
                    help=_(
                        "If a new log file is found we usually skip to its end to avoid processing"
                        " ancient log messages. You can enable this flag to start processing the"
                        " file from the beginning and see all messages that may already be"
                        " present."
                    ),
                    choices=[
                        (False, _("Skip preexisting log messages")),
                        (True, _("Process preexisting log messages")),
                    ],
                ),
            ),
            (
                "encoding",
                TextInput(
                    title=_("Character encoding that should be used to decode the matching files"),
                    help=_(
                        "mk_logwatch tries its best to determine the correct encoding of a file,"
                        " and to recover from errors if it is wrong. If that does not work for"
                        " you, you can configure a specific encoding."
                    ),
                    default_value="utf-8",
                    validate=validate_python_encoding,
                ),
            ),
            (
                "skipconsecutiveduplicated",
                Checkbox(
                    title=_("Duplicated messages management"),
                    label=_("Filter out consecutive duplicated messages in the agent output"),
                    help=_(
                        "If there are multiple consecutive messages with the same content, the"
                        " agent delivers only the first message and then it outputs a context line"
                        " with the number of lines that have been removed: [the above message was"
                        " repeated n times]. Setting this flag may help to decrease the size of the"
                        " agent output in case many duplicate lines are generated."
                    ),
                ),
            ),
            (
                "patterns",
                ListOf(
                    valuespec=Tuple(
                        show_titles=True,
                        orientation="horizontal",
                        elements=[
                            DropdownChoice(
                                title=_("State"),
                                choices=[
                                    ("C", _("CRITICAL")),
                                    ("W", _("WARNING")),
                                    ("O", _("OK")),
                                    ("I", _("IGNORE")),
                                    ("R", _("REWRITE")),
                                    ("A", _("APPEND")),
                                ],
                            ),
                            # This should remain a TextInput because the regex validation is
                            # performed at the tuple level since it dependes on the "state" field
                            TextInput(
                                title=_("Pattern (Regex)"),
                                size=64,
                            ),
                        ],
                        validate=_validate_patterns,
                    ),
                    title=_("Regular expressions for message classification"),
                    help=_(
                        "Each new message runs through this list of rules. As soon as "
                        "a regular expression is found <i>in</i> the message, the state "
                        "is determined and the search terminated. If no rule matches "
                        "the message is classified as <i>IGNORE</i>. Note: <i>OK</i> "
                        "messages are being sent to the central Checkmk server, where "
                        "they can be reclassified. <i>IGNORE</i> messages are silently "
                        "dropped.<br><br><i>REWRITE</i> allows to change the content "
                        "of a message that has been matched by the <i>previous</i> rule. "
                        "You can specify a new text and use the placeholders <tt>\\0</tt> for "
                        "the original message, <tt>\\1</tt> for the first regex match group "
                        "of the match, <tt>\\2</tt> for the second and so on.<br><br><i>APPEND</i> "
                        "allows for appending messages to a <i>previous</i> message. A block of "
                        "APPEND patterns (one more multiple) works in conjunction with the pattern "
                        "directly <i>before</i> this block. Once this pattern matches a message "
                        "(call it the 'initial message'), the agent plug-in starts to check the "
                        "subsequent messages against the patterns in the APPEND block. As long as "
                        "there is a match, these subsequent messages are appended to the initial "
                        "message. Once there is no match, the appending is stopped and the regular "
                        "processing of messages continues. One use case for this feature is the "
                        "handling of multi-line stack traces."
                    ),
                    add_label=_("Add message pattern"),
                ),
            ),
        ],
        required_keys=["logfiles", "overflow", "context", "patterns"],
    )


def _valuespec_agent_config_mk_logwatch() -> Alternative:
    return Alternative(
        title=_("Text log files (Windows, Linux, Solaris, AIX)"),
        help=_(
            "The agent plug-in <tt>mk_logwatch.py</tt> monitors a configured set "
            "of text logfiles for new messages, classifies these according "
            "to a set of rules and sends (only) relevant messages to the "
            "Checkmk server for further processing. Here the messages can "
            "further be (re-)classified using the "
            "<a href='wato.py?varname=logwatch_rules&folder=&mode=edit_ruleset'>"
            "Logwatch Ruleset</a>. <b>Note:</b> If you want to configure "
            "several log files with different sets of patterns, then simply "
            "create several rules. In this ruleset <b>all</b> matching rules "
            "are being executed, not only the first one. "
            "<b>Note (2):</b> This duplicate possibility for "
            "classification is due to performance issues. It is always a good "
            "idea that the agent forwards only messages that are potential "
            "problems in order to cut down network traffic. Central reclassification "
            "on the other hand is more convenient because no agent update is "
            "necessary when rules need to be changed."
        ),
        elements=[
            Dictionary(
                title=_("Deploy the %s plug-in and its configuration") % "Logwatch",
                elements=[
                    (
                        "global_retention_period",
                        Age(
                            title=_("Retention period"),
                            default_value=60,
                            help=_(
                                "Every time the plug-in is executed, it gathers all relevant"
                                " messages since its last execution. It then puts these"
                                " messages in a bundle and stores it on disk. All bundles that"
                                " have been created within this <i>retention period</i> are"
                                " output and sent to the monitoring site. The monitoring site"
                                " will keep track of the bundles, and only process the ones it"
                                " has not seen before. This prevents messages from being lost"
                                " if the transmitted agent output is not processed in the"
                                " context of a check cycle (for instance during discovery or"
                                " when pulling via <tt>cmk -d my_host</tt>).\n\n"
                                "It is recommended to set it at least to the check interval"
                                " (which is 60 seconds by default). Note that if you set this"
                                " to <i>N</i> times the check interval, the amount of data"
                                " sent will be about <i>N</i> times as much (not taking into"
                                " account the compression by the agent controller)."
                            ),
                        ),
                    ),
                    ("file_section", _agent_config_mk_logwatch_valuespec_file_section()),
                    ("cluster_section", _agent_config_mk_logwatch_valuespec_cluster_section()),
                ],
            ),
            FixedValue(
                value=True,
                title=_("Deploy the %s plug-in without configuration") % "Logwatch",
                help=_("The file %s needs to be created and maintained manually.")
                % "<tt>/etc/check_mk/logwatch.cfg</tt>",
                totext=_("manually configure %s") % "<tt>/etc/check_mk/logwatch.cfg</tt>",
            ),
            FixedValue(
                value=None,
                title=_("Do not deploy the %s plug-in") % "Logwatch",
                totext=_("(disabled)"),
            ),
        ],
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupMonitoringAgentsAgentPlugins,
        match_type="all",
        name=RuleGroup.AgentConfig("mk_logwatch"),
        valuespec=_valuespec_agent_config_mk_logwatch,
    )
)
