#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import sys
import abc
import logging
import os
import re
import io
import time
import zipfile
from typing import Callable, Dict, List, Optional as _Optional, Text, TypeVar, Union  # pylint: disable=unused-import

if sys.version_info[0] >= 3:
    from pathlib import Path  # pylint: disable=import-error,unused-import
else:
    from pathlib2 import Path  # pylint: disable=import-error,unused-import

from pysmi.compiler import MibCompiler  # type: ignore[import]
from pysmi.parser.smiv1compat import SmiV1CompatParser  # type: ignore[import]
from pysmi.searcher.pypackage import PyPackageSearcher  # type: ignore[import]
from pysmi.searcher.pyfile import PyFileSearcher  # type: ignore[import]
from pysmi.writer.pyfile import PyFileWriter  # type: ignore[import]
from pysmi.reader.localfile import FileReader  # type: ignore[import]
from pysmi.codegen.pysnmp import PySnmpCodeGen  # type: ignore[import]
from pysmi.reader.callback import CallbackReader  # type: ignore[import]
from pysmi.searcher.stub import StubSearcher  # type: ignore[import]
from pysmi.error import PySmiError  # type: ignore[import]
import six

import cmk.utils.version as cmk_version
import cmk.utils.log
import cmk.utils.paths
import cmk.utils.store as store
import cmk.utils.render
import cmk.utils.packaging

# It's OK to import centralized config load logic
import cmk.ec.export as ec  # pylint: disable=cmk-module-layer-violation

if cmk_version.is_managed_edition():
    import cmk.gui.cme.managed as managed  # pylint: disable=no-name-in-module
else:
    managed = None  # type: ignore[assignment]

import cmk.gui.forms as forms
import cmk.gui.config as config
import cmk.gui.sites as sites
import cmk.gui.mkeventd
import cmk.gui.watolib as watolib
import cmk.gui.hooks as hooks
from cmk.gui.table import table_element
from cmk.gui.valuespec import CascadingDropdownChoice, DictionaryEntry  # pylint: disable=unused-import
from cmk.gui.valuespec import (
    TextUnicode,
    DropdownChoice,
    TextAscii,
    Integer,
    Tuple,
    FixedValue,
    Alternative,
    ListChoice,
    RegExp,
    RegExpUnicode,
    TextAreaUnicode,
    Transform,
    Dictionary,
    ID,
    CascadingDropdown,
    Optional,
    Checkbox,
    ListOf,
    ListOfStrings,
    Age,
    IPv4Address,
    IPv4Network,
    Foldable,
    DualListChoice,
    LogLevelChoice,
    rule_option_elements,
)
from cmk.gui.i18n import _
from cmk.gui.globals import html
from cmk.gui.htmllib import HTML, Choices  # pylint: disable=unused-import
from cmk.gui.exceptions import MKUserError, MKGeneralException
from cmk.gui.permissions import (
    Permission,
    permission_registry,
)
from cmk.gui.wato.pages.global_settings import (
    GlobalSettingsMode,
    EditGlobalSettingMode,
)

from cmk.gui.plugins.wato.utils import (
    config_variable_group_registry,
    ConfigVariableGroup,
    config_variable_registry,
    ConfigVariable,
    ConfigDomainGUI,
    WatoMode,
    mode_registry,
    SNMPCredentials,
    HostnameTranslation,
    ContactGroupSelection,
    ConfigDomainEventConsole,
    get_search_expression,
    add_change,
    changelog_button,
    home_button,
    make_action_link,
    rulespec_group_registry,
    RulespecGroup,
    rulespec_registry,
    HostRulespec,
    ServiceRulespec,
    main_module_registry,
    MainModule,
    wato_confirm,
    search_form,
    site_neutral_path,
    SampleConfigGenerator,
    sample_config_generator_registry,
)

from cmk.gui.plugins.wato.check_mk_configuration import (
    ConfigVariableGroupUserInterface,
    ConfigVariableGroupWATO,
    RulespecGroupGrouping,
)
from cmk.gui.plugins.wato.globals_notification import ConfigVariableGroupNotifications


def _compiled_mibs_dir():
    return cmk.utils.paths.omd_root + "/local/share/check_mk/compiled_mibs"


#.
#   .--ValueSpecs----------------------------------------------------------.
#   |        __     __    _            ____                                |
#   |        \ \   / /_ _| |_   _  ___/ ___| _ __   ___  ___ ___           |
#   |         \ \ / / _` | | | | |/ _ \___ \| '_ \ / _ \/ __/ __|          |
#   |          \ V / (_| | | |_| |  __/___) | |_) |  __/ (__\__ \          |
#   |           \_/ \__,_|_|\__,_|\___|____/| .__/ \___|\___|___/          |
#   |                                       |_|                            |
#   +----------------------------------------------------------------------+
#   | Declarations of the structure of rules and actions                   |
#   '----------------------------------------------------------------------'


def substitute_help():
    _help_list = [
        ("$ID$", _("Event ID")),
        ("$COUNT$", _("Number of occurrances")),
        ("$TEXT$", _("Message text")),
        ("$FIRST$", _("Time of the first occurrence (time stamp)")),
        ("$LAST$", _("Time of the most recent occurrance")),
        ("$COMMENT$", _("Event comment")),
        ("$SL$", _("Service Level")),
        ("$HOST$", _("Host name (as sent by syslog)")),
        ("$ORIG_HOST$", _("Original host name when host name has been rewritten, empty otherwise")),
        ("$CONTACT$", _("Contact information")),
        ("$APPLICATION$", _("Syslog tag / Application")),
        ("$PID$", _("Process ID of the origin process")),
        ("$PRIORITY$", _("Syslog Priority")),
        ("$FACILITY$", _("Syslog Facility")),
        ("$RULE_ID$", _("ID of the rule")),
        ("$STATE$", _("State of the event (0/1/2/3)")),
        ("$PHASE$", _("Phase of the event (open in normal situations, closed when cancelling)")),
        ("$OWNER$", _("Owner of the event")),
        ("$MATCH_GROUPS$", _("Text groups from regular expression match, separated by spaces")),
        ("$MATCH_GROUP_1$", _("Text of the first match group from expression match")),
        ("$MATCH_GROUP_2$", _("Text of the second match group from expression match")),
        ("$MATCH_GROUP_3$",
         _("Text of the third match group from expression match (and so on...)")),
    ]

    # TODO: While loading this module there is no "html" object available for generating the HTML
    # code below. The HTML generating code could be independent of a HTML request.
    _help_rows = [
        html.render_tr(html.render_td(key) + html.render_td(value)) for key, value in _help_list
    ]

    return _("The following macros will be substituted by value from the actual event:")\
         + html.render_br()\
         + html.render_br()\
         + html.render_table(HTML().join(_help_rows), class_="help")


def ActionList(vs, **kwargs):
    def validate_action_list(value, varprefix):
        action_ids = [v["id"] for v in value]
        rule_packs = load_mkeventd_rules()
        for rule_pack in rule_packs:
            for rule in rule_pack["rules"]:
                for action_id in rule.get("actions", []):
                    if action_id not in action_ids + ["@NOTIFY"]:
                        raise MKUserError(
                            varprefix,
                            _("You are missing the action with the ID <b>%s</b>, "
                              "which is still used in some rules.") % action_id)

    return ListOf(vs, validate=validate_action_list, **kwargs)


class RuleState(CascadingDropdown):
    def __init__(self, **kwargs):
        choices = [
            (0, _("OK")),
            (1, _("WARN")),
            (2, _("CRIT")),
            (3, _("UNKNOWN")),
            (-1, _("(set by syslog)")),
            ('text_pattern', _('(set by message text)'),
             Dictionary(
                 elements=[
                     ('2',
                      RegExpUnicode(
                          title=_("CRIT Pattern"),
                          help=_("When the given regular expression (infix search) matches "
                                 "the events state is set to CRITICAL."),
                          size=64,
                          mode=RegExp.infix,
                      )),
                     ('1',
                      RegExpUnicode(
                          title=_("WARN Pattern"),
                          help=_("When the given regular expression (infix search) matches "
                                 "the events state is set to WARNING."),
                          size=64,
                          mode=RegExp.infix,
                      )),
                     ('0',
                      RegExpUnicode(
                          title=_("OK Pattern"),
                          help=_("When the given regular expression (infix search) matches "
                                 "the events state is set to OK."),
                          size=64,
                          mode=RegExp.infix,
                      )),
                 ],
                 help=_('Individual patterns matching the text (which must have been matched by '
                        'the generic "text to match pattern" before) which set the state of the '
                        'generated event depending on the match.<br><br>'
                        'First the CRITICAL pattern is tested, then WARNING and OK at last. '
                        'When none of the patterns matches, the events state is set to UNKNOWN.'),
             )),
        ]  # type: List[CascadingDropdownChoice]
        CascadingDropdown.__init__(self, choices=choices, **kwargs)


def vs_mkeventd_rule_pack(fixed_id=None, fixed_title=None):
    elements = []  # type: List[DictionaryEntry]
    if fixed_id:
        elements.append(("id",
                         FixedValue(
                             title=_("Rule pack ID"),
                             value=fixed_id,
                             help=_("The ID of an exported rule pack cannot be modified."),
                         )))
    else:
        elements.append(("id",
                         ID(
                             title=_("Rule pack ID"),
                             help=_("A unique ID of this rule pack."),
                             allow_empty=False,
                             size=12,
                         )))

    if fixed_title:
        elements.append(("title",
                         FixedValue(
                             title=_("Title"),
                             value=fixed_title,
                             help=_("The title of an exported rule pack cannot be modified."),
                         )))
    else:
        elements.append(("title",
                         TextUnicode(
                             title=_("Title"),
                             help=_("A descriptive title for this rule pack"),
                             allow_empty=False,
                             size=64,
                         )),)

    elements.append(("disabled",
                     Checkbox(
                         title=_("Disable"),
                         label=_("Currently disable execution of all rules in the pack"),
                     )),)

    if cmk_version.is_managed_edition():
        elements += managed.customer_choice_element(deflt=managed.SCOPE_GLOBAL)

    return Dictionary(
        title=_("Rule pack properties"),
        render="form",
        elements=elements,
        optional_keys=["customer"],
    )


def vs_mkeventd_rule(customer=None):
    elements = [
        ("id",
         ID(
             title=_("Rule ID"),
             help=_("A unique ID of this rule. Each event will remember the rule "
                    "it was classified with by its rule ID."),
             allow_empty=False,
             size=24,
         )),
    ] + rule_option_elements()

    if cmk_version.is_managed_edition():
        if customer:
            # Enforced by rule pack
            elements += [
                ("customer",
                 FixedValue(
                     customer,
                     title=_("Customer"),
                     totext="%s (%s)" %
                     (managed.get_customer_name_by_id(customer), _("Set by rule pack")),
                 )),
            ]
        else:
            elements += managed.customer_choice_element()

    elements += [
        ("drop",
         DropdownChoice(
             title=_("Rule type"),
             choices=[
                 (False, _("Normal operation - process message according to action settings")),
                 (True, _("Do not perform any action, drop this message, stop processing")),
                 ("skip_pack",
                  _("Skip this rule pack, continue rule execution with next rule pack")),
             ],
             help=_(
                 "With this option you can implement rules that rule out certain message from the "
                 "procession totally. Either you can totally abort further rule execution, or "
                 "you can skip just the current rule pack and continue with the next one."),
         )),
        ("state",
         RuleState(
             title=_("State"),
             help=_("The monitoring state that this event will trigger."),
             default_value=-1,
         )),
        ("sl",
         Dictionary(title=_("Service Level"),
                    optional_keys=False,
                    elements=[
                        ("value",
                         DropdownChoice(
                             title=_("Value"),
                             choices=cmk.gui.mkeventd.service_levels,
                             prefix_values=True,
                             help=_("The default/fixed service level to use for this rule."),
                         )),
                        ("precedence",
                         DropdownChoice(
                             title=_("Precedence"),
                             choices=[
                                 ("message", _("Keep service level from message (if available)")),
                                 ("rule", _("Always use service level from rule")),
                             ],
                             help=_("Here you can specify which service level will be used when "
                                    "the incoming message already carries a service level."),
                             default_value="message",
                         )),
                    ])),
        ("contact_groups",
         Dictionary(
             title=_("Contact Groups"),
             elements=[
                 ("groups",
                  ListOf(
                      ContactGroupSelection(),
                      title=_("Contact groups"),
                      movable=False,
                  )),
                 ("notify",
                  Checkbox(
                      title=_("Use in notifications"),
                      label=_("Use in notifications"),
                      help=_(
                          "Also use these contact groups in eventually notifications created by "
                          "this rule. Historically this option only affected the visibility in the "
                          "GUI and <i>not</i> notifications. New rules will enable this option "
                          "automatically, existing rules have this disabled by default."),
                      default_value=True,
                  )),
                 ("precedence",
                  DropdownChoice(
                      title=_("Precedence of contact groups"),
                      choices=[
                          ("host", _("Host's contact groups have precedence")),
                          ("rule", _("Contact groups in rule have precedence")),
                      ],
                      help=_(
                          "Here you can specify which contact groups shall have "
                          "precedence when both, the host of an event can be found in the "
                          "monitoring and the event rule has defined contact groups for the event."
                      ),
                      default_value="host",
                  )),
             ],
             help=_(
                 "When you expect this rule to receive events from hosts that are <i>not</i> "
                 "known to the monitoring, you can specify contact groups for controlling "
                 "the visibility and eventually triggered notifications here.<br>"
                 "<br><i>Notes:</i><br>"
                 "1. If you activate this option and do not specify any group, then "
                 "users with restricted permissions can never see these events.<br>"
                 "2. If both the host is found in the monitoring <b>and</b> contact groups are "
                 "specified in the rule then usually the host's contact groups have precedence. "),
             optional_keys=[],
         )),
        ("actions",
         ListChoice(
             title=_("Actions"),
             help=_("Actions to automatically perform when this event occurs"),
             choices=cmk.gui.mkeventd.action_choices,
         )),
        ("actions_in_downtime",
         DropdownChoice(
             title=_("Do actions"),
             choices=[
                 (True, _("even when the host is in downtime")),
                 (False, _("only when the host is not in downtime")),
             ],
             default_value=True,
             help=_("With this setting you can prevent actions to be executed when "
                    "the host is in downtime. This setting applies to events that are "
                    "related to an existing monitoring host. Other event actions will "
                    "always be executed."),
         )),
        ("cancel_actions",
         ListChoice(
             title=_("Actions when cancelling"),
             help=_("Actions to automatically perform when an event is being cancelled."),
             choices=cmk.gui.mkeventd.action_choices,
         )),
        ("cancel_action_phases",
         DropdownChoice(
             title=_("Do Cancelling-Actions when..."),
             choices=[
                 ("always", _("Always when an event is being cancelled")),
                 ("open", _("Only when the cancelled event is in phase OPEN")),
             ],
             help=_("With this setting you can prevent actions to be executed when "
                    "events are being cancelled that are in the phases DELAYED or COUNTING."),
         )),
        ("autodelete",
         Checkbox(
             title=_("Automatic Deletion"),
             label=_("Delete event immediately after the actions"),
             help=_("Incoming messages might trigger actions (when configured above), "
                    "afterwards only an entry in the event history will be left. There "
                    "will be no \"open event\" to be handled by the administrators."),
         )),
        ("event_limit",
         Alternative(
             title=_("Custom rule event limit"),
             help=_("Use this option to override the "
                    "<a href=\"wato.py?mode=mkeventd_edit_configvar&site=&varname=event_limit\">"
                    "global rule event limit</a>"),
             style="dropdown",
             elements=[
                 FixedValue(
                     None,
                     title=_("Use global rule limit"),
                     totext="",
                 ),
                 vs_ec_rule_limit(),
             ],
         )),
        ("count",
         Dictionary(
             title=_("Count messages in defined interval"),
             help=_("With this option you can make the rule being executed not before "
                    "the matching message is seen a couple of times in a defined "
                    "time interval. Also counting activates the aggregation of messages "
                    "that result from the same rule into one event, even if <i>count</i> is "
                    "set to 1."),
             optional_keys=False,
             columns=2,
             elements=[
                 ("count",
                  Integer(
                      title=_("Count until triggered"),
                      help=_("That many times the message must occur until an event is created"),
                      minvalue=1,
                  )),
                 ("period",
                  Age(
                      title=_("Time period for counting"),
                      help=_(
                          "If in this time range the configured number of time the rule is "
                          "triggered, an event is being created. If the required count is not reached "
                          "then the count is reset to zero."),
                      default_value=86400,
                  )),
                 ("algorithm",
                  DropdownChoice(
                      title=_("Algorithm"),
                      help=
                      _("Select how the count is computed. The algorithm <i>Interval</i> will count the "
                        "number of messages from the first occurrance and reset this counter as soon as "
                        "the interval is elapsed or the maximum count has reached. The token bucket algorithm "
                        "does not work with intervals but simply decreases the current count by one for "
                        "each partial time interval. Please refer to the online documentation for more details."
                       ),
                      choices=[
                          ("interval", _("Interval")),
                          ("tokenbucket", _("Token Bucket")),
                          ("dynabucket", _("Dynamic Token Bucket")),
                      ],
                      default_value="interval")),
                 ("count_duration",
                  Optional(
                      Age(
                          label=_("Count only for"),
                          help=_(
                              "When the event is in the state <i>open</i> for that time span "
                              "then no further messages of the same time will be added to the "
                              "event. It will stay open, but the count does not increase anymore. "
                              "Any further matching message will create a new event."),
                      ),
                      label=_("Discontinue counting after time has elapsed"),
                      none_label=_("Bar"),
                  )),
                 ("count_ack",
                  Checkbox(
                      label=_("Continue counting when event is <b>acknowledged</b>"),
                      help=_("Otherwise counting will start from one with a new event for "
                             "the next rule match."),
                      default_value=False,
                  )),
                 ("separate_host",
                  Checkbox(
                      label=_("Force separate events for different <b>hosts</b>"),
                      help=_("When aggregation is turned on and the rule matches for "
                             "two different hosts then these two events will be kept "
                             "separate if you check this box."),
                      default_value=True,
                  )),
                 ("separate_application",
                  Checkbox(
                      label=_("Force separate events for different <b>applications</b>"),
                      help=_("When aggregation is turned on and the rule matches for "
                             "two different applications then these two events will be kept "
                             "separate if you check this box."),
                      default_value=True,
                  )),
                 ("separate_match_groups",
                  Checkbox(
                      label=_("Force separate events for different <b>match groups</b>"),
                      help=_("When you use subgroups in the regular expression of your "
                             "match text then you can have different values for the matching "
                             "groups be reflected in different events."),
                      default_value=True,
                  )),
             ],
         )),
        ("expect",
         Dictionary(title=_("Expect regular messages"),
                    help=_("With this option activated you can make the Event Console monitor "
                           "that a certain number of messages are <b>at least</b> seen within "
                           "each regular time interval. Otherwise an event will be created. "
                           "The options <i>week</i>, <i>two days</i> and <i>day</i> refer to "
                           "periodic intervals aligned at 00:00:00 on the 1st of January 1970. "
                           "You can specify a relative offset in hours in order to re-align this "
                           "to any other point of time. In a distributed environment, make "
                           "sure to specify which site should expect the messages in the match "
                           "criteria above, else all sites with config replication will warn if "
                           "messages fail to arrive."),
                    optional_keys=False,
                    columns=2,
                    elements=[
                        ("interval",
                         CascadingDropdown(
                             title=_("Interval"),
                             separator="&nbsp;",
                             choices=[
                                 (7 * 86400, _("week"),
                                  Integer(
                                      label=_("Timezone offset"),
                                      unit=_("hours"),
                                      default_value=0,
                                      minvalue=-167,
                                      maxvalue=167,
                                  )),
                                 (2 * 86400, _("two days"),
                                  Integer(
                                      label=_("Timezone offset"),
                                      unit=_("hours"),
                                      default_value=0,
                                      minvalue=-47,
                                      maxvalue=47,
                                  )),
                                 (86400, _("day"),
                                  DropdownChoice(
                                      label=_("in timezone"),
                                      choices=[
                                          (-12, _("UTC -12 hours")),
                                          (-11, _("UTC -11 hours")),
                                          (-10, _("UTC -10 hours")),
                                          (-9, _("UTC -9 hours")),
                                          (-8, _("UTC -8 hours")),
                                          (-7, _("UTC -7 hours")),
                                          (-6, _("UTC -6 hours")),
                                          (-5, _("UTC -5 hours")),
                                          (-4, _("UTC -4 hours")),
                                          (-3, _("UTC -3 hours")),
                                          (-2, _("UTC -2 hours")),
                                          (-1, _("UTC -1 hour")),
                                          (0, _("UTC")),
                                          (1, _("UTC +1 hour")),
                                          (2, _("UTC +2 hours")),
                                          (3, _("UTC +3 hours")),
                                          (4, _("UTC +4 hours")),
                                          (5, _("UTC +5 hours")),
                                          (6, _("UTC +8 hours")),
                                          (7, _("UTC +7 hours")),
                                          (8, _("UTC +8 hours")),
                                          (9, _("UTC +9 hours")),
                                          (10, _("UTC +10 hours")),
                                          (11, _("UTC +11 hours")),
                                          (12, _("UTC +12 hours")),
                                      ],
                                      default_value=0,
                                  )),
                                 (3600, _("hour")),
                                 (900, _("15 minutes")),
                                 (300, _("5 minutes")),
                                 (60, _("minute")),
                                 (10, _("10 seconds")),
                             ],
                             default_value=3600,
                         )),
                        ("count", Integer(
                            title=_("Number of expected messages"),
                            minvalue=1,
                        )),
                        ("merge",
                         DropdownChoice(
                             title=_("Merge with open event"),
                             help=_("If there already exists an open event because of absent "
                                    "messages according to this rule, you can optionally merge "
                                    "the new incident with the exising event or create a new "
                                    "event for each interval with absent messages."),
                             choices=[
                                 ("open", _("Merge if there is an open un-acknowledged event")),
                                 ("acked", _("Merge even if there is an acknowledged event")),
                                 ("never", _("Create a new event for each incident - never merge")),
                             ],
                             default_value="open",
                         )),
                    ])),
        ("delay",
         Age(title=_("Delay event creation"),
             help=_("The creation of an event will be delayed by this time period. This "
                    "does only make sense for events that can be cancelled by a negative "
                    "rule."))),
        (
            "livetime",
            Tuple(
                title=_("Limit event lifetime"),
                help=_(
                    "If you set a lifetime of an event, then it will automatically be "
                    "deleted after that time if, even if no action has taken by the user. You can "
                    "decide whether to expire open, acknowledged or both types of events. The lifetime "
                    "always starts when the event is entering the open state."),
                elements=[
                    Age(),
                    ListChoice(
                        choices=[
                            ("open", _("Expire events that are in the state <i>open</i>")),
                            ("ack", _("Expire events that are in the state <i>acknowledged</i>")),
                        ],
                        default_value=["open"],
                    )
                ],
            ),
        ),
        ("match",
         RegExpUnicode(
             title=_("Text to match"),
             help=_("The rules does only apply when the given regular expression matches "
                    "the message text (infix search)."),
             size=64,
             mode=RegExp.infix,
             case_sensitive=False,
         )),
        ("match_site",
         DualListChoice(
             title=_("Match site"),
             help=_("Apply this rule only on the following sites"),
             choices=config.get_event_console_site_choices(),
         )),
        ("match_host",
         RegExpUnicode(
             title=_("Match host"),
             help=_("The rules does only apply when the given regular expression matches "
                    "the host name the message originates from. Note: in some cases the "
                    "event might use the IP address instead of the host name."),
             mode=RegExp.complete,
             case_sensitive=False,
         )),
        ("match_ipaddress",
         IPv4Network(
             title=_("Match original source IP address"),
             help=_("The rules does only apply when the event is being received from a "
                    "certain IP address. You can specify either a single IP address "
                    "or an IPv4 network in the notation X.X.X.X/Bits."),
         )),
        ("match_application",
         RegExpUnicode(
             title=_("Match syslog application (tag)"),
             help=_("Regular expression for matching the syslog tag (case insenstive)"),
             mode=RegExp.infix,
             case_sensitive=False,
         )),
        ("match_priority",
         Tuple(
             title=_("Match syslog priority"),
             help=_("Define a range of syslog priorities this rule matches"),
             orientation="horizontal",
             show_titles=False,
             elements=[
                 DropdownChoice(
                     label=_("from:"),
                     choices=cmk.gui.mkeventd.syslog_priorities,
                     default_value=4,
                 ),
                 DropdownChoice(
                     label=_(" to:"),
                     choices=cmk.gui.mkeventd.syslog_priorities,
                     default_value=0,
                 ),
             ],
         )),
        ("match_facility",
         DropdownChoice(
             title=_("Match syslog facility"),
             help=_("Make the rule match only if the message has a certain syslog facility. "
                    "Messages not having a facility are classified as <tt>user</tt>."),
             choices=cmk.gui.mkeventd.syslog_facilities,
         )),
        ("match_sl",
         Tuple(
             title=_("Match service level"),
             help=_("This setting is only useful if you've configured service levels for hosts. "
                    "If the event results from forwarded service notifications or logwatch "
                    "messages the service's configured service level is used here. In such cases "
                    "you can make this rule match only certain service levels."),
             orientation="horizontal",
             show_titles=False,
             elements=[
                 DropdownChoice(
                     label=_("from:"),
                     choices=cmk.gui.mkeventd.service_levels,
                     prefix_values=True,
                 ),
                 DropdownChoice(
                     label=_(" to:"),
                     choices=cmk.gui.mkeventd.service_levels,
                     prefix_values=True,
                 ),
             ],
         )),
        ("match_timeperiod",
         watolib.timeperiods.TimeperiodSelection(
             title=_("Match only during timeperiod"),
             help=
             _("Match this rule only during times where the selected timeperiod from the monitoring "
               "system is active. The Timeperiod definitions are taken from the monitoring core that "
               "is running on the same host or OMD site as the event daemon. Please note, that this "
               "selection only offers timeperiods that are defined with WATO."),
         )),
        ("match_ok",
         RegExpUnicode(
             title=_("Text to cancel event(s)"),
             help=_(
                 "If a matching message appears with this text, then events created "
                 "by this rule will automatically be cancelled if host, application and match groups match. "
                 "If this expression has fewer match groups than \"Text to match\", "
                 "it will cancel all events where the specified groups match the same number "
                 "of groups in the initial text, starting from the left."),
             size=64,
             mode=RegExp.infix,
             case_sensitive=False,
         )),
        ("cancel_priority",
         Tuple(
             title=_("Syslog priority to cancel event"),
             help=
             _("If the priority of the event lies withing this range and either no text to cancel "
               "is specified or that text also matched, then events created with this rule will "
               "automatically be cancelled (if host, application, facility and match groups match)."
              ),
             orientation="horizontal",
             show_titles=False,
             elements=[
                 DropdownChoice(
                     label=_("from:"),
                     choices=cmk.gui.mkeventd.syslog_priorities,
                     default_value=7,
                 ),
                 DropdownChoice(
                     label=_(" to:"),
                     choices=cmk.gui.mkeventd.syslog_priorities,
                     default_value=5,
                 ),
             ],
         )),
        ("cancel_application",
         RegExpUnicode(
             title=_("Syslog application to cancel event"),
             help=_("If the application of the message matches this regular expression "
                    "(case insensitive) and either no text to cancel is specified or "
                    "that text also matched, then events created by this rule will "
                    "automatically be cancelled (if host, facility and match groups match)."),
             mode=RegExp.infix,
             case_sensitive=False,
         )),
        ("invert_matching",
         Checkbox(
             title=_("Invert matching"),
             label=_(
                 "Negate match: Execute this rule if the upper conditions are <b>not</b> fulfilled."
             ),
             help=
             _("By activating this checkbox the complete combined rule conditions will be inverted. That "
               "means that this rule with be executed, if at least on of the conditions does <b>not</b> match. "
               "This can e.g. be used for skipping a rule pack if the message text does not contain <tt>ORA-</tt>. "
               "Please note: When an inverted rule matches there can never be match groups."),
         )),
        ("set_text",
         TextUnicode(
             title=_("Rewrite message text"),
             help=_("Replace the message text with this text. If you have bracketed "
                    "groups in the text to match, then you can use the placeholders "
                    "<tt>\\1</tt>, <tt>\\2</tt>, etc. for inserting the first, second "
                    "etc matching group.") +
             _("The placeholder <tt>\\0</tt> will be replaced by the original text. "
               "This allows you to add new information in front or at the end. ") +
             _("You can also use the placeholders $MATCH_GROUPS_MESSAGE_1$ for message match groups and "
               "$MATCH_GROUPS_SYSLOG_APPLICATION_1$</tt> for the syslog application match groups."),
             size=64,
             allow_empty=False,
             attrencode=True,
         )),
        ("set_host",
         TextUnicode(
             title=_("Rewrite hostname"),
             help=_("Replace the host name with this text. If you have bracketed "
                    "groups in the text to match, then you can use the placeholders "
                    "<tt>\\1</tt>, <tt>\\2</tt>, etc. for inserting the first, second "
                    "etc matching group.") +
             _("The placeholder <tt>\\0</tt> will be replaced by the original text "
               "to match. Note that as an alternative, you may also use the rule "
               "Hostname translation for Incoming Messages in the Global Settings "
               "of the EC to accomplish your task.") +
             _("You can also use the placeholders $MATCH_GROUPS_MESSAGE_1$ for message match groups and "
               "$MATCH_GROUPS_SYSLOG_APPLICATION_1$</tt> for the syslog application match groups."),
             allow_empty=False,
             attrencode=True,
         )),
        ("set_application",
         TextUnicode(
             title=_("Rewrite application"),
             help=_("Replace the application (syslog tag) with this text. If you have bracketed "
                    "groups in the text to match, then you can use the placeholders "
                    "<tt>\\1</tt>, <tt>\\2</tt>, etc. for inserting the first, second "
                    "etc matching group.") +
             _("The placeholder <tt>\\0</tt> will be replaced by the original text. "
               "This allows you to add new information in front or at the end.") +
             _("You can also use the placeholders $MATCH_GROUPS_MESSAGE_1$ for message match groups and "
               "$MATCH_GROUPS_SYSLOG_APPLICATION_1$</tt> for the syslog application match groups."),
             allow_empty=False,
             attrencode=True,
         )),
        ("set_comment",
         TextUnicode(
             title=_("Add comment"),
             help=_("Attach a comment to the event. If you have bracketed "
                    "groups in the text to match, then you can use the placeholders "
                    "<tt>\\1</tt>, <tt>\\2</tt>, etc. for inserting the first, second "
                    "etc matching group.") +
             _("The placeholder <tt>\\0</tt> will be replaced by the original text. "
               "This allows you to add new information in front or at the end."),
             size=64,
             allow_empty=False,
             attrencode=True,
         )),
        ("set_contact",
         TextUnicode(
             title=_("Add contact information"),
             help=_("Attach information about a contact person. If you have bracketed "
                    "groups in the text to match, then you can use the placeholders "
                    "<tt>\\1</tt>, <tt>\\2</tt>, etc. for inserting the first, second "
                    "etc matching group.") +
             _("The placeholder <tt>\\0</tt> will be replaced by the original text. "
               "This allows you to add new information in front or at the end."),
             size=64,
             allow_empty=False,
             attrencode=True,
         )),
    ]

    return Dictionary(
        title=_("Rule Properties"),
        elements=elements,
        optional_keys=[
            "delay",
            "livetime",
            "count",
            "expect",
            "match_priority",
            "match_priority",
            "match_facility",
            "match_sl",
            "match_host",
            "match_site",
            "match_ipaddress",
            "match_application",
            "match_timeperiod",
            "set_text",
            "set_host",
            "set_application",
            "set_comment",
            "set_contact",
            "cancel_priority",
            "cancel_application",
            "match_ok",
            "contact_groups",
        ],
        headers=[
            (_("Rule Properties"),
             ["id", "description", "comment", "docu_url", "disabled", "customer"]),
            (_("Matching Criteria"), [
                "match", "match_site", "match_host", "match_ipaddress", "match_application",
                "match_priority", "match_facility", "match_sl", "match_ok", "cancel_priority",
                "cancel_application", "match_timeperiod", "invert_matching"
            ]),
            (_("Outcome & Action"), [
                "state", "sl", "contact_groups", "actions", "actions_in_downtime", "cancel_actions",
                "cancel_action_phases", "drop", "autodelete", "event_limit"
            ]),
            (_("Counting & Timing"), ["count", "expect", "delay", "livetime"]),
            (_("Rewriting"),
             ["set_text", "set_host", "set_application", "set_comment", "set_contact"]),
        ],
        render="form",
        form_narrow=True,
    )


#.
#   .--Load & Save---------------------------------------------------------.
#   |       _                    _    ___     ____                         |
#   |      | |    ___   __ _  __| |  ( _ )   / ___|  __ ___   _____        |
#   |      | |   / _ \ / _` |/ _` |  / _ \/\ \___ \ / _` \ \ / / _ \       |
#   |      | |__| (_) | (_| | (_| | | (_>  <  ___) | (_| |\ V /  __/       |
#   |      |_____\___/ \__,_|\__,_|  \___/\/ |____/ \__,_| \_/ \___|       |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |  Loading and saving of rule packages                                 |
#   '----------------------------------------------------------------------'


def load_mkeventd_rules():
    rule_packs = ec.load_rule_packs()

    # Add information about rule hits: If we are running on OMD then we know
    # the path to the state retention file of mkeventd and can read the rule
    # statistics directly from that file.
    rule_stats = {}  # type: Dict[str, int]
    for rule_id, count in sites.live().query("GET eventconsolerules\nColumns: rule_id rule_hits\n"):
        rule_stats.setdefault(rule_id, 0)
        rule_stats[rule_id] += count

    for rule_pack in rule_packs:
        pack_hits = 0
        for rule in rule_pack["rules"]:
            hits = rule_stats.get(rule["id"], 0)
            rule["hits"] = hits
            pack_hits += hits
        rule_pack["hits"] = pack_hits

    return rule_packs


def save_mkeventd_rules(rule_packs):
    ec.save_rule_packs(rule_packs, config.mkeventd_pprint_rules)


def export_mkp_rule_pack(rule_pack):
    ec.export_rule_pack(rule_pack, config.mkeventd_pprint_rules)


@sample_config_generator_registry.register
class SampleConfigGeneratorECSampleRulepack(SampleConfigGenerator):
    @classmethod
    def ident(cls):
        return "ec_sample_rule_pack"

    @classmethod
    def sort_index(cls):
        return 50

    def generate(self):
        save_mkeventd_rules([ec.default_rule_pack([])])


#.
#   .--WATO Modes----------------------------------------------------------.
#   |      __        ___  _____ ___    __  __           _                  |
#   |      \ \      / / \|_   _/ _ \  |  \/  | ___   __| | ___  ___        |
#   |       \ \ /\ / / _ \ | || | | | | |\/| |/ _ \ / _` |/ _ \/ __|       |
#   |        \ V  V / ___ \| || |_| | | |  | | (_) | (_| |  __/\__ \       |
#   |         \_/\_/_/   \_\_| \___/  |_|  |_|\___/ \__,_|\___||___/       |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   | The actual configuration modes for all rules, one rule and the       |
#   | activation of the changes.                                           |
#   '----------------------------------------------------------------------'


class ABCEventConsoleMode(six.with_metaclass(abc.ABCMeta, WatoMode)):
    # NOTE: This class is obviously still abstract, but pylint fails to see
    # this, even in the presence of the meta class assignment below, see
    # https://github.com/PyCQA/pylint/issues/179.

    # pylint: disable=abstract-method
    def __init__(self):
        self._rule_packs = load_mkeventd_rules()
        super(ABCEventConsoleMode, self).__init__()

    def _verify_ec_enabled(self):
        if not config.mkeventd_enabled:
            raise MKUserError(None, _("The Event Console is disabled (\"omd config\")."))

    def _search_expression(self):
        return get_search_expression()

    def _rule_pack_with_id(self, rule_pack_id):
        for nr, entry in enumerate(self._rule_packs):
            if entry["id"] == rule_pack_id:
                return nr, entry
        raise MKUserError(None, _("The requested rule pack does not exist."))

    def _show_event_simulator(self):
        event = config.user.load_file("simulated_event", {})
        html.begin_form("simulator")
        self._vs_mkeventd_event().render_input("event", event)
        forms.end()
        html.hidden_fields()
        html.button("simulate", _("Try out"))
        html.button("_generate", _("Generate Event!"))
        html.end_form()
        html.br()

        if html.request.var("simulate") or html.request.var("_generate"):
            return self._vs_mkeventd_event().from_html_vars("event")
        return None

    def _event_simulation_action(self):
        # Validation of input for rule simulation (no further action here)
        if html.request.var("simulate") or html.request.var("_generate"):
            vs = self._vs_mkeventd_event()
            event = vs.from_html_vars("event")
            vs.validate_value(event, "event")
            config.user.save_file("simulated_event", event)

        if html.request.has_var("_generate") and html.check_transaction():
            if not event.get("application"):
                raise MKUserError("event_p_application", _("Please specify an application name"))
            if not event.get("host"):
                raise MKUserError("event_p_host", _("Please specify a host name"))
            rfc = cmk.gui.mkeventd.send_event(event)
            return None, _("Test event generated and sent to Event Console.") \
                          + html.render_br() \
                          + html.render_pre(rfc) \
                          + html.render_reload_sidebar()

    def _add_change(self, what, message):
        add_change(what,
                   message,
                   domains=[ConfigDomainEventConsole],
                   sites=_get_event_console_sync_sites())

    def _changes_button(self):
        changelog_button()

    def _rules_button(self):
        html.context_button(_("Rule Packs"),
                            html.makeuri_contextless([("mode", "mkeventd_rule_packs")]), "back")

    def _config_button(self):
        if config.user.may("mkeventd.config"):
            html.context_button(_("Settings"),
                                html.makeuri_contextless([("mode", "mkeventd_config")]),
                                "configuration")

    def _status_button(self):
        html.context_button(_("Server Status"),
                            html.makeuri_contextless([("mode", "mkeventd_status")]), "status")

    def _mibs_button(self):
        html.context_button(_("SNMP MIBs"), html.makeuri_contextless([("mode", "mkeventd_mibs")]),
                            "snmpmib")

    def _get_rule_pack_to_mkp_map(self):
        return {} if cmk_version.is_raw_edition() else cmk.utils.packaging.rule_pack_id_to_mkp()

    def _vs_mkeventd_event(self):
        """Valuespec for simulating an event"""
        return Dictionary(
            title=_("Event Simulator"),
            help=_("You can simulate an event here and check out, which rules are matching."),
            render="form",
            form_narrow=True,
            optional_keys=False,
            elements=[
                ("text",
                 TextUnicode(title=_("Message text"),
                             size=30,
                             try_max_width=True,
                             allow_empty=False,
                             default_value=_("Still nothing happened."),
                             attrencode=True)),
                ("application",
                 TextUnicode(title=_("Application name"),
                             help=_("The syslog tag"),
                             size=40,
                             default_value=_("Foobar-Daemon"),
                             allow_empty=True,
                             attrencode=True)),
                ("host",
                 TextUnicode(
                     title=_("Host Name"),
                     help=_("The host name of the event"),
                     size=40,
                     default_value=_("myhost089"),
                     allow_empty=True,
                     attrencode=True,
                     regex="^\\S*$",
                     regex_error=_("The host name may not contain spaces."),
                 )),
                ("ipaddress",
                 IPv4Address(
                     title=_("IP Address"),
                     help=_("Original IP address the event was received from"),
                     default_value="1.2.3.4",
                 )),
                ("priority",
                 DropdownChoice(
                     title=_("Syslog Priority"),
                     choices=cmk.gui.mkeventd.syslog_priorities,
                     default_value=5,
                 )),
                ("facility",
                 DropdownChoice(
                     title=_("Syslog Facility"),
                     choices=cmk.gui.mkeventd.syslog_facilities,
                     default_value=1,
                 )),
                ("sl",
                 DropdownChoice(
                     title=_("Service Level"),
                     choices=cmk.gui.mkeventd.service_levels,
                     prefix_values=True,
                 )),
                ("site",
                 DropdownChoice(
                     title=_("Simulate for site"),
                     choices=config.get_event_console_site_choices,
                 )),
            ])


@mode_registry.register
class ModeEventConsoleRulePacks(ABCEventConsoleMode):
    @classmethod
    def name(cls):
        return "mkeventd_rule_packs"

    @classmethod
    def permissions(cls):
        return ["mkeventd.edit"]

    def title(self):
        return _("Event Console rule packages")

    def buttons(self):
        self._changes_button()
        home_button()
        if config.user.may("mkeventd.edit"):
            html.context_button(_("New Rule Pack"),
                                html.makeuri_contextless([("mode", "mkeventd_edit_rule_pack")]),
                                "new")
            html.context_button(
                _("Reset Counters"),
                make_action_link([("mode", "mkeventd_rule_packs"), ("_reset_counters", "1")]),
                "resetcounters")
        self._status_button()
        self._config_button()
        self._mibs_button()

    def action(self):
        action_outcome = self._event_simulation_action()
        if action_outcome:
            return action_outcome

        # Deletion of rule packs
        if html.request.has_var("_delete"):
            nr = html.request.get_integer_input_mandatory("_delete")
            rule_pack = self._rule_packs[nr]
            c = wato_confirm(
                _("Confirm rule pack deletion"),
                _("Do you really want to delete the rule pack <b>%s</b> <i>%s</i> with <b>%s</b> rules?"
                 ) % (rule_pack["id"], rule_pack["title"], len(rule_pack["rules"])))
            if c:
                self._add_change("delete-rule-pack", _("Deleted rule pack %s") % rule_pack["id"])
                del self._rule_packs[nr]
                save_mkeventd_rules(self._rule_packs)
            elif c is False:
                return ""

        # Reset all rule hit counteres
        elif html.request.has_var("_reset_counters"):
            c = wato_confirm(
                _("Confirm counter reset"),
                _("Do you really want to reset all rule hit counters in <b>all rule packs</b> to zero?"
                 ))
            if c:
                cmk.gui.mkeventd.execute_command("RESETCOUNTERS", site=config.omd_site())
                self._add_change("counter-reset", _("Resetted all rule hit counters to zero"))
            elif c is False:
                return ""

        # Copy rules from master
        elif html.request.has_var("_copy_rules"):
            c = wato_confirm(
                _("Confirm copying rules"),
                _("Do you really want to copy all event rules from the master and "
                  "replace your local configuration with them?"))
            if c:
                self._copy_rules_from_master()
                self._add_change(
                    "copy-rules-from-master",
                    _("Copied the event rules from the master "
                      "into the local configuration"))
                return None, _("Copied rules from master")
            elif c is False:
                return ""

        # Move rule packages
        elif html.request.has_var("_move"):
            from_pos = html.request.get_integer_input_mandatory("_move")
            to_pos = html.request.get_integer_input_mandatory("_index")
            rule_pack = self._rule_packs[from_pos]
            del self._rule_packs[from_pos]  # make to_pos now match!
            self._rule_packs[to_pos:to_pos] = [rule_pack]
            save_mkeventd_rules(self._rule_packs)
            self._add_change("move-rule-pack",
                             _("Changed position of rule pack %s") % rule_pack["id"])

        # Export rule pack
        elif html.request.has_var("_export"):
            nr = html.request.get_integer_input_mandatory("_export")
            try:
                rule_pack = self._rule_packs[nr]
            except KeyError:
                raise MKUserError("_export", _("The requested rule pack does not exist"))

            export_mkp_rule_pack(rule_pack)
            self._rule_packs[nr] = ec.MkpRulePackProxy(rule_pack['id'])
            save_mkeventd_rules(self._rule_packs)
            self._add_change("export-rule-pack",
                             _("Made rule pack %s available for MKP export") % rule_pack["id"])

        # Make rule pack non-exportable
        elif html.request.has_var("_dissolve"):
            nr = html.request.get_integer_input_mandatory("_dissolve")
            try:
                self._rule_packs[nr] = self._rule_packs[nr].rule_pack
            except KeyError:
                raise MKUserError("_dissolve", _("The requested rule pack does not exist"))
            save_mkeventd_rules(self._rule_packs)
            ec.remove_exported_rule_pack(self._rule_packs[nr]["id"])
            self._add_change("dissolve-rule-pack",
                             _("Removed rule_pack %s from MKP export") % self._rule_packs[nr]["id"])

        # Reset to rule pack provided via MKP
        elif html.request.has_var("_reset"):
            nr = html.request.get_integer_input_mandatory("_reset")
            try:
                self._rule_packs[nr] = ec.MkpRulePackProxy(self._rule_packs[nr]['id'])
            except KeyError:
                raise MKUserError("_reset", _("The requested rule pack does not exist"))
            save_mkeventd_rules(self._rule_packs)
            self._add_change(
                "reset-rule-pack",
                _("Resetted the rules of rule pack %s to the ones provided via MKP") %
                self._rule_packs[nr].id_)

        # Synchronize modified rule pack with MKP
        elif html.request.has_var("_synchronize"):
            nr = html.request.get_integer_input_mandatory("_synchronize")
            export_mkp_rule_pack(self._rule_packs[nr])
            try:
                self._rule_packs[nr] = ec.MkpRulePackProxy(self._rule_packs[nr]['id'])
            except KeyError:
                raise MKUserError("_synchronize", _("The requested rule pack does not exist"))
            save_mkeventd_rules(self._rule_packs)
            self._add_change(
                "synchronize-rule-pack",
                _("Synchronized MKP with the modified rule pack %s") % self._rule_packs[nr].id_)

        # Update data strcuture after actions
        self._rule_packs = load_mkeventd_rules()

    def _copy_rules_from_master(self):
        answer = cmk.gui.mkeventd.query_ec_directly("REPLICATE 0")
        if "rules" not in answer:
            raise MKGeneralException(_("Cannot get rules from local event daemon."))
        rule_packs = answer["rules"]
        save_mkeventd_rules(rule_packs)

    def page(self):
        self._verify_ec_enabled()
        rep_mode = cmk.gui.mkeventd.replication_mode()
        if rep_mode in ["sync", "takeover"]:
            copy_url = make_action_link([("mode", "mkeventd_rule_packs"), ("_copy_rules", "1")])
            html.show_warning(
                _("WARNING: This Event Console is currently running as a replication "
                  "slave. The rules edited here will not be used. Instead a copy of the rules of the "
                  "master are being used in the case of a takeover. The same holds for the event "
                  "actions in the global settings.<br><br>If you want you can copy the ruleset of "
                  "the master into your local slave configuration: ") + '<a href="%s">' % copy_url +
                _("Copy Rules From Master") + '</a>')

        elif rep_mode == "stopped":
            html.show_error(_("The Event Console is currently not running."))

        search_form("%s: " % _("Search in packs"), "mkeventd_rule_packs")
        search_expression = self._search_expression()
        if search_expression:
            found_packs = self._filter_mkeventd_rule_packs(search_expression, self._rule_packs)
            title = _("Found rule packs")
        else:
            found_packs = {}
            title = _("Rule packs")

        # Simulator
        event = self._show_event_simulator()
        if not self._rule_packs:
            html.show_message(
                _("You have not created any rule packs yet. The Event Console is useless unless "
                  "you have activated <i>Force message archiving</i> in the global settings."))
        elif search_expression and not found_packs:
            html.show_message(_("Found no rules packs."))
            return

        id_to_mkp = self._get_rule_pack_to_mkp_map()

        have_match = False
        with table_element(css="ruleset", limit=None, sortable=False, title=title) as table:
            for nr, rule_pack in enumerate(self._rule_packs):
                id_ = rule_pack['id']
                type_ = ec.RulePackType.type_of(rule_pack, id_to_mkp)

                if id_ in found_packs:
                    css_matches_search = "matches_search"  # type: _Optional[str]
                else:
                    css_matches_search = None

                table.row(css=css_matches_search)
                table.cell(_("Actions"), css="buttons")

                edit_url = html.makeuri_contextless([("mode", "mkeventd_edit_rule_pack"),
                                                     ("edit", nr)])
                html.icon_button(edit_url, _("Edit properties of this rule pack"), "edit")

                # Cloning does not work until we have unique IDs
                # clone_url  = html.makeuri_contextless([("mode", "mkeventd_edit_rule_pack"), ("clone", nr)])
                # html.icon_button(clone_url, _("Create a copy of this rule pack"), "clone")

                drag_url = make_action_link([("mode", "mkeventd_rule_packs"), ("_move", nr)])
                html.element_dragger_url("tr", base_url=drag_url)

                if type_ == ec.RulePackType.internal:
                    delete_url = make_action_link([("mode", "mkeventd_rule_packs"),
                                                   ("_delete", nr)])
                    html.icon_button(delete_url, _("Delete this rule pack"), "delete")
                elif type_ == ec.RulePackType.exported:
                    dissolve_url = make_action_link([("mode", "mkeventd_rule_packs"),
                                                     ("_dissolve", nr)])
                    html.icon_button(dissolve_url,
                                     _("Remove this rule pack from the Extension Packages module"),
                                     "release_mkp_yellow")
                elif type_ == ec.RulePackType.modified_mkp:
                    reset_url = make_action_link([("mode", "mkeventd_rule_packs"), ("_reset", nr)])
                    html.icon_button(reset_url, _("Reset rule pack to the MKP version"),
                                     "release_mkp")
                    sync_url = make_action_link([("mode", "mkeventd_rule_packs"),
                                                 ("_synchronize", nr)])
                    html.icon_button(sync_url, _("Synchronize MKP with modified version"),
                                     "sync_mkp")

                rules_url_vars = [("mode", "mkeventd_rules"), ("rule_pack", id_)]
                if found_packs.get(id_):
                    rules_url_vars.append(("search", search_expression))
                rules_url = html.makeuri_contextless(rules_url_vars)
                html.icon_button(rules_url, _("Edit the rules in this pack"), "mkeventd_rules")

                if type_ == ec.RulePackType.internal:
                    export_url = make_action_link([("mode", "mkeventd_rule_packs"),
                                                   ("_export", nr)])
                    html.icon_button(
                        export_url,
                        _("Make this rule pack available in the Extension Packages module"),
                        "cached")

                # Icons for mkp export and disabling
                table.cell("", css="buttons")
                if type_ == ec.RulePackType.unmodified_mkp:
                    html.icon(
                        _("This rule pack is provided via the MKP %s.") % id_to_mkp[id_], "mkps")
                elif type_ == ec.RulePackType.exported:
                    html.icon(
                        _("This is rule pack can be packaged with the Extension Packages module."),
                        "package")
                elif type_ == ec.RulePackType.modified_mkp:
                    html.icon(
                        _("This rule pack is modified. Originally it was provided via the MKP %s.")
                        % id_to_mkp[id_], "new_mkp")

                if rule_pack["disabled"]:
                    html.icon(
                        _("This rule pack is currently disabled. None of its rules will be applied."
                         ), "disabled")

                # Simulation of all rules in this pack
                elif event:
                    matches = 0
                    cancelling_matches = 0
                    skips = 0

                    for rule in rule_pack["rules"]:
                        result = cmk.gui.mkeventd.event_rule_matches(rule_pack, rule, event)
                        if isinstance(result, tuple):
                            cancelling, groups = result

                            if not cancelling and rule.get("drop") == "skip_pack":
                                matches += 1
                                skips = 1
                                break

                            if cancelling and matches == 0:
                                cancelling_matches += 1

                            matches += 1

                    if matches == 0:
                        msg = _("None of the rules in this pack matches")
                        icon = "rulenmatch"
                    else:
                        msg = _("Number of matching rules in this pack: %d") % matches
                        if skips:
                            msg += _(", the first match skips this rule pack")
                            icon = "rulenmatch"
                        else:
                            if cancelling:
                                msg += _(", first match is a cancelling match")
                            if groups:
                                msg += _(", match groups of decisive match: %s") % ",".join(
                                    [g or _('&lt;None&gt;') for g in groups])
                            if have_match:
                                msg += _(
                                    ", but it is overruled by a match in a previous rule pack.")
                                icon = "rulepmatch"
                            else:
                                icon = "rulematch"
                                have_match = True
                    html.icon(msg, icon)

                table.cell(_("ID"), id_)
                table.cell(_("Title"), html.render_text(rule_pack["title"]))

                if cmk_version.is_managed_edition():
                    table.cell(_("Customer"))
                    if "customer" in rule_pack:
                        html.write_text(managed.get_customer_name(rule_pack))

                table.cell(_("Rules"),
                           html.render_a("%d" % len(rule_pack["rules"]), href=rules_url),
                           css="number")

                hits = rule_pack.get('hits')
                table.cell(_("Hits"), hits is not None and hits or '', css="number")

    def _filter_mkeventd_rule_packs(self, search_expression, rule_packs):
        found_packs = {}  # type: Dict[str, List[ec.ECRuleSpec]]
        for rule_pack in rule_packs:
            if search_expression in rule_pack["id"].lower() \
               or search_expression in rule_pack["title"].lower():
                found_packs.setdefault(rule_pack["id"], [])
            for rule in rule_pack.get("rules", []):
                if search_expression in rule["id"].lower() \
                   or search_expression in rule.get("description", "").lower():
                    found_rules = found_packs.setdefault(rule_pack["id"], [])
                    found_rules.append(rule)
        return found_packs


T = TypeVar('T')


def _deref(x):
    # type: (Union[T, Callable[[], T]]) -> T
    return x() if callable(x) else x


@mode_registry.register
class ModeEventConsoleRules(ABCEventConsoleMode):
    @classmethod
    def name(cls):
        return "mkeventd_rules"

    @classmethod
    def permissions(cls):
        return ["mkeventd.edit"]

    def _from_vars(self):
        self._rule_pack_id = html.request.var("rule_pack")
        self._rule_pack_nr, self._rule_pack = self._rule_pack_with_id(self._rule_pack_id)
        self._rules = self._rule_pack["rules"]

    def title(self):
        return _("Rule Package %s") % self._rule_pack["title"]

    def buttons(self):
        self._rules_button()
        self._changes_button()
        if config.user.may("mkeventd.edit"):
            html.context_button(
                _("New Rule"),
                html.makeuri_contextless([("mode", "mkeventd_edit_rule"),
                                          ("rule_pack", self._rule_pack_id)]), "new")
            html.context_button(
                _("Properties"),
                html.makeuri_contextless([("mode", "mkeventd_edit_rule_pack"),
                                          ("edit", self._rule_pack_nr)]), "edit")

    def action(self):
        id_to_mkp = self._get_rule_pack_to_mkp_map()
        type_ = ec.RulePackType.type_of(self._rule_pack, id_to_mkp)

        if html.request.var("_move_to"):
            if html.check_transaction():
                for move_nr, rule in enumerate(self._rules):
                    move_var = "_move_to_%s" % rule["id"]
                    if html.request.var(move_var):
                        other_pack_nr, other_pack = self._rule_pack_with_id(
                            html.request.var(move_var))

                        other_type_ = ec.RulePackType.type_of(other_pack, id_to_mkp)
                        if other_type_ == ec.RulePackType.unmodified_mkp:
                            ec.override_rule_pack_proxy(other_pack_nr, self._rule_packs)

                        if type_ == ec.RulePackType.unmodified_mkp:
                            ec.override_rule_pack_proxy(self._rule_pack_nr, self._rule_packs)

                        self._rule_packs[other_pack_nr]["rules"][0:0] = [rule]
                        del self._rule_packs[self._rule_pack_nr]["rules"][move_nr]

                        if other_type_ == ec.RulePackType.exported:
                            export_mkp_rule_pack(other_pack)
                        if type_ == ec.RulePackType.exported:
                            export_mkp_rule_pack(self._rule_pack)
                        save_mkeventd_rules(self._rule_packs)

                        self._add_change(
                            "move-rule-to-pack",
                            _("Moved rule %s to pack %s") % (rule["id"], other_pack["id"]))
                        return None, html.render_text(
                            _("Moved rule %s to pack %s") % (rule["id"], other_pack["title"]))

        action_outcome = self._event_simulation_action()
        if action_outcome:
            return action_outcome

        if html.request.has_var("_delete"):
            nr = html.request.get_integer_input_mandatory("_delete")
            rules = self._rules
            rule = rules[nr]
            c = wato_confirm(
                _("Confirm rule deletion"),
                _("Do you really want to delete the rule <b>%s</b> <i>%s</i>?") %
                (rule["id"], rule.get("description", "")))
            if c:
                self._add_change("delete-rule", _("Deleted rule %s") % self._rules[nr]["id"])
                if type_ == ec.RulePackType.unmodified_mkp:
                    ec.override_rule_pack_proxy(self._rule_pack_nr, self._rule_packs)
                    rules = self._rule_packs[self._rule_pack_nr]['rules']

                del rules[nr]

                if type_ == ec.RulePackType.exported:
                    export_mkp_rule_pack(self._rule_pack)
                save_mkeventd_rules(self._rule_packs)
            elif c is False:
                return ""
            else:
                return

        if html.check_transaction():
            if html.request.has_var("_move"):
                from_pos = html.request.get_integer_input_mandatory("_move")
                to_pos = html.request.get_integer_input_mandatory("_index")

                rules = self._rules
                if type_ == ec.RulePackType.unmodified_mkp:
                    ec.override_rule_pack_proxy(self._rule_pack_nr, self._rule_packs)
                    rules = self._rule_packs[self._rule_pack_nr]['rules']

                rule = rules[from_pos]
                del rules[from_pos]  # make to_pos now match!
                rules[to_pos:to_pos] = [rule]

                if type_ == ec.RulePackType.exported:
                    export_mkp_rule_pack(self._rule_pack)
                save_mkeventd_rules(self._rule_packs)

                self._add_change("move-rule", _("Changed position of rule %s") % rule["id"])

    def page(self):
        self._verify_ec_enabled()
        search_expression = self._search_expression()
        search_form("%s: " % _("Search in rules"), "mkeventd_rules")
        if search_expression:
            found_rules = self._filter_mkeventd_rules(search_expression, self._rule_pack)
        else:
            found_rules = []

        # Simulator
        event = self._show_event_simulator()
        if not self._rules:
            html.show_message(_("This package does not yet contain any rules."))
            return
        elif search_expression and not found_rules:
            html.show_message(_("No rules found."))
            return

        if len(self._rule_packs) > 1:
            html.begin_form("move_to", method="POST")

        # TODO: Rethink the typing of syslog_facilites/syslog_priorities.
        priorities = _deref(cmk.gui.mkeventd.syslog_priorities)
        facilities = dict(_deref(cmk.gui.mkeventd.syslog_facilities))

        # Show content of the rule package
        with table_element(css="ruleset", limit=None, sortable=False) as table:
            have_match = False
            for nr, rule in enumerate(self._rules):
                if rule in found_rules:
                    css_matches_search = "matches_search"  # type: _Optional[str]
                else:
                    css_matches_search = None

                table.row(css=css_matches_search)
                delete_url = make_action_link([("mode", "mkeventd_rules"),
                                               ("rule_pack", self._rule_pack_id), ("_delete", nr)])
                drag_url = make_action_link([("mode", "mkeventd_rules"),
                                             ("rule_pack", self._rule_pack_id), ("_move", nr)])
                edit_url = html.makeuri_contextless([("mode", "mkeventd_edit_rule"),
                                                     ("rule_pack", self._rule_pack_id),
                                                     ("edit", nr)])
                clone_url = html.makeuri_contextless([("mode", "mkeventd_edit_rule"),
                                                      ("rule_pack", self._rule_pack_id),
                                                      ("clone", nr)])

                table.cell(_("Actions"), css="buttons")
                html.icon_button(edit_url, _("Edit this rule"), "edit")
                html.icon_button(clone_url, _("Create a copy of this rule"), "clone")
                html.element_dragger_url("tr", base_url=drag_url)
                html.icon_button(delete_url, _("Delete this rule"), "delete")

                table.cell("", css="buttons")
                if rule.get("disabled"):
                    html.icon(_("This rule is currently disabled and will not be applied"),
                              "disabled")
                elif event:
                    result = cmk.gui.mkeventd.event_rule_matches(self._rule_pack, rule, event)
                    if not isinstance(result, tuple):
                        html.icon(_("Rule does not match: %s") % result, "rulenmatch")
                    else:
                        cancelling, groups = result
                        if have_match:
                            msg = _("This rule matches, but is overruled by a previous match.")
                            icon = "rulepmatch"
                        else:
                            if cancelling:
                                msg = _("This rule does a cancelling match.")
                            else:
                                msg = _("This rule matches.")
                            icon = "rulematch"
                            have_match = True
                        if groups:
                            msg += _(" Match groups: %s") % ",".join(
                                [g or _('&lt;None&gt;') for g in groups])
                        html.icon(msg, icon)

                if rule.get("invert_matching"):
                    html.icon(_("Matching is inverted in this rule"), "inverted")

                if rule.get("contact_groups") is not None:
                    html.icon(
                        _("This rule attaches contact group(s) to the events: %s") %
                        (", ".join(rule["contact_groups"]["groups"]) or _("(none)")),
                        "contactgroups")

                table.cell(_("ID"), html.render_a(rule["id"], edit_url))

                if cmk_version.is_managed_edition():
                    table.cell(_("Customer"))
                    if "customer" in self._rule_pack:
                        html.write_text(
                            "%s (%s)" %
                            (managed.get_customer_name(self._rule_pack), _("Set by rule pack")))
                    else:
                        html.write_text(managed.get_customer_name(rule))

                if rule.get("drop"):
                    table.cell(_("State"), css="state statep nowrap")
                    if rule["drop"] == "skip_pack":
                        html.write_text(_("SKIP PACK"))
                    else:
                        html.write_text(_("DROP"))
                else:
                    if isinstance(rule['state'], tuple):
                        stateval = rule["state"][0]
                    else:
                        stateval = rule["state"]
                    txt = {
                        0: _("OK"),
                        1: _("WARN"),
                        2: _("CRIT"),
                        3: _("UNKNOWN"),
                        -1: _("(syslog)"),
                        'text_pattern': _("(set by message text)")
                    }[stateval]
                    table.cell(_("State"), txt, css="state state%s" % stateval)

                # Syslog priority
                if "match_priority" in rule:
                    prio_from, prio_to = rule["match_priority"]
                    if prio_from == prio_to:
                        prio_text = priorities[prio_from][1]
                    else:
                        prio_text = priorities[prio_from][1][:2] + ".." + priorities[prio_to][1][:2]
                else:
                    prio_text = ""
                table.cell(_("Priority"), prio_text)

                # Syslog Facility
                table.cell(_("Facility"))
                if "match_facility" in rule:
                    facnr = rule["match_facility"]
                    html.write("%s" % facilities[facnr])

                table.cell(
                    _("Service Level"),
                    dict(cmk.gui.mkeventd.service_levels()).get(rule["sl"]["value"],
                                                                rule["sl"]["value"]))
                hits = rule.get('hits')
                table.cell(_("Hits"), hits is not None and hits or '', css="number")

                # Text to match
                table.cell(_("Text to match"), rule.get("match"))

                # Description
                table.cell(_("Description"))
                url = rule.get("docu_url")
                if url:
                    html.icon_button(url,
                                     _("Context information about this rule"),
                                     "url",
                                     target="_blank")
                    html.nbsp()
                html.write_text(rule.get("description", ""))

                # Move rule to other pack
                if len(self._rule_packs) > 1:
                    table.cell(_("Move to pack..."))
                    choices = [("", u"")]  # type: Choices
                    choices += [(pack["id"], pack["title"])
                                for pack in self._rule_packs
                                if pack is not self._rule_pack]
                    html.dropdown("_move_to_%s" % rule["id"], choices, onchange="move_to.submit();")

            if len(self._rule_packs) > 1:
                html.hidden_field("_move_to", "yes")
                html.hidden_fields()
                html.end_form()

    def _filter_mkeventd_rules(self, search_expression, rule_pack):
        found_rules = []
        for rule in rule_pack.get("rules", []):
            if search_expression in rule["id"].lower() \
               or search_expression in rule.get("description", "").lower() \
               or search_expression in rule.get("match", "").lower():
                found_rules.append(rule)
        return found_rules


@mode_registry.register
class ModeEventConsoleEditRulePack(ABCEventConsoleMode):
    @classmethod
    def name(cls):
        return "mkeventd_edit_rule_pack"

    @classmethod
    def permissions(cls):
        return ["mkeventd.edit"]

    def _from_vars(self):
        self._edit_nr = html.request.get_integer_input_mandatory("edit",
                                                                 -1)  # missing -> new rule pack
        self._new = self._edit_nr < 0

        if self._new:
            self._rule_pack = {"rules": []}  # type: ec.ECRulePack
        else:
            try:
                self._rule_pack = self._rule_packs[self._edit_nr]
            except IndexError:
                raise MKUserError("edit",
                                  _("The rule pack you are trying to "
                                    "edit does not exist."))

        id_to_mkp = self._get_rule_pack_to_mkp_map()
        self._type = ec.RulePackType.type_of(self._rule_pack, id_to_mkp)

    def title(self):
        if self._new:
            return _("Create new rule pack")
        return _("Edit rule pack %s") % self._rule_packs[self._edit_nr]["id"]

    def buttons(self):
        self._rules_button()
        self._changes_button()
        if not self._new:
            rule_pack_id = self._rule_packs[self._edit_nr]["id"]
            html.context_button(
                _("Edit Rules"),
                html.makeuri([("mode", "mkeventd_rules"), ("rule_pack", rule_pack_id)]),
                "mkeventd_rules")

    def action(self):
        if not html.check_transaction():
            return "mkeventd_rule_packs"

        if not self._new:
            existing_rules = self._rule_pack["rules"]
        else:
            existing_rules = []

        vs = self._valuespec()
        self._rule_pack = vs.from_html_vars("rule_pack")
        vs.validate_value(self._rule_pack, "rule_pack")

        self._rule_pack["rules"] = existing_rules
        new_id = self._rule_pack["id"]

        # Make sure that ID is unique
        for nr, other_rule_pack in enumerate(self._rule_packs):
            if self._new or nr != self._edit_nr:
                if other_rule_pack["id"] == new_id:
                    raise MKUserError("rule_pack_p_id",
                                      _("A rule pack with this ID already exists."))

        if self._new:
            self._rule_packs = [self._rule_pack] + self._rule_packs
        else:
            if self._type == ec.RulePackType.internal or self._type == ec.RulePackType.modified_mkp:
                self._rule_packs[self._edit_nr] = self._rule_pack
            else:
                self._rule_packs[self._edit_nr].rule_pack = self._rule_pack
                export_mkp_rule_pack(self._rule_pack)

        save_mkeventd_rules(self._rule_packs)

        if self._new:
            self._add_change("new-rule-pack",
                             _("Created new rule pack with id %s") % self._rule_pack["id"])
        else:
            self._add_change("edit-rule-pack", _("Modified rule pack %s") % self._rule_pack["id"])
        return "mkeventd_rule_packs"

    def page(self):
        self._verify_ec_enabled()
        html.begin_form("rule_pack")
        vs = self._valuespec()
        vs.render_input("rule_pack", self._rule_pack)
        vs.set_focus("rule_pack")
        html.button("save", _("Save"))
        html.hidden_fields()
        html.end_form()

    def _valuespec(self):
        if self._type == ec.RulePackType.internal:
            return vs_mkeventd_rule_pack()
        return vs_mkeventd_rule_pack(fixed_id=self._rule_pack['id'],
                                     fixed_title=self._rule_pack['title'])


@mode_registry.register
class ModeEventConsoleEditRule(ABCEventConsoleMode):
    @classmethod
    def name(cls):
        return "mkeventd_edit_rule"

    @classmethod
    def permissions(cls):
        return ["mkeventd.edit"]

    def _from_vars(self):
        if html.request.has_var("rule_pack"):
            self._rule_pack_nr, self._rule_pack = self._rule_pack_with_id(
                html.request.var("rule_pack"))

        else:
            # In links from multisite views the rule pack is not known.
            # We just know the rule id and need to find the pack ourselves.
            rule_id = html.request.get_ascii_input_mandatory("rule_id")

            self._rule_pack = None
            for nr, pack in enumerate(self._rule_packs):
                for rnr, rule in enumerate(pack["rules"]):
                    if rule_id == rule["id"]:
                        self._rule_pack_nr, self._rule_pack = nr, pack
                        html.request.set_var("edit", str(rnr))
                        html.request.set_var("rule_pack", pack["id"])
                        break

            if not self._rule_pack:
                raise MKUserError("rule_id", _("The rule you are trying to edit does not exist."))

        self._rules = self._rule_pack["rules"]

        self._edit_nr = html.request.get_integer_input_mandatory("edit", -1)  # missing -> new rule
        self._clone_nr = html.request.get_integer_input_mandatory("clone",
                                                                  -1)  # Only needed in 'new' mode
        self._new = self._edit_nr < 0

        if self._new:
            if self._clone_nr >= 0 and not html.request.var("_clear"):
                self._rule = {}
                self._rule.update(self._rules[self._clone_nr])
            else:
                self._rule = {}
        else:
            try:
                self._rule = self._rules[self._edit_nr]
            except IndexError:
                raise MKUserError("edit", _("The rule you are trying to edit does not exist."))

    def title(self):
        if self._new:
            return _("Create new rule")
        return _("Edit rule %s") % self._rules[self._edit_nr]["id"]

    def buttons(self):
        home_button()
        self._rules_button()
        self._changes_button()
        if self._clone_nr >= 0:
            html.context_button(_("Clear Rule"), html.makeuri([("_clear", "1")]), "clear")

    def action(self):
        if not html.check_transaction():
            return "mkeventd_rules"

        if not self._new:
            old_id = self._rule["id"]
        vs = self._valuespec()
        self._rule = vs.from_html_vars("rule")
        vs.validate_value(self._rule, "rule")
        if not self._new and old_id != self._rule["id"]:
            raise MKUserError("rule_p_id",
                              _("It is not allowed to change the ID of an existing rule."))
        elif self._new:
            for pack in self._rule_packs:
                for r in pack["rules"]:
                    if r["id"] == self._rule["id"]:
                        raise MKUserError(
                            "rule_p_id",
                            _("A rule with this ID already exists in rule pack <b>%s</b>.") %
                            pack["title"])

        try:
            num_groups = re.compile(self._rule["match"]).groups
        except Exception:
            raise MKUserError("rule_p_match", _("Invalid regular expression"))
        if num_groups > 9:
            raise MKUserError(
                "rule_p_match",
                _("You matching text has too many regular expresssion subgroups. "
                  "Only nine are allowed."))

        if "count" in self._rule and "expect" in self._rule:
            raise MKUserError(
                "rule_p_expect_USE",
                _("You cannot use counting and expecting "
                  "at the same time in the same rule."))

        if "expect" in self._rule and "delay" in self._rule:
            raise MKUserError(
                "rule_p_expect_USE",
                _("You cannot use expecting and delay "
                  "at the same time in the same rule, sorry."))

        # Make sure that number of group replacements do not exceed number
        # of groups in regex of match
        num_repl = 9
        while num_repl > num_groups:
            repl = "\\%d" % num_repl
            for name, value in self._rule.items():
                if name.startswith("set_") and isinstance(value, six.string_types):
                    if repl in value:
                        raise MKUserError(
                            "rule_p_" + name,
                            _("You are using the replacment reference <tt>\\%d</tt>, "
                              "but your match text has only %d subgroups.") %
                            (num_repl, num_groups))
            num_repl -= 1

        if cmk_version.is_managed_edition() and "customer" in self._rule_pack:
            try:
                del self._rule["customer"]
            except KeyError:
                pass

        id_to_mkp = self._get_rule_pack_to_mkp_map()
        type_ = ec.RulePackType.type_of(self._rule_pack, id_to_mkp)
        if type_ == ec.RulePackType.unmodified_mkp:
            ec.override_rule_pack_proxy(self._rule_pack_nr, self._rule_packs)
            self._rules = self._rule_packs[self._rule_pack_nr]['rules']

        if self._new and self._clone_nr >= 0:
            self._rules[self._clone_nr:self._clone_nr] = [self._rule]
        elif self._new:
            self._rules[0:0] = [self._rule]
        else:
            self._rules[self._edit_nr] = self._rule

        if type_ == ec.RulePackType.exported:
            export_mkp_rule_pack(self._rule_pack)
        save_mkeventd_rules(self._rule_packs)

        if self._new:
            self._add_change("new-rule",
                             _("Created new event correlation rule with id %s") % self._rule["id"])
        else:
            self._add_change("edit-rule",
                             _("Modified event correlation rule %s") % self._rule["id"])
            # Reset hit counters of this rule
            cmk.gui.mkeventd.execute_command("RESETCOUNTERS", [self._rule["id"]], config.omd_site())
        return "mkeventd_rules"

    def page(self):
        self._verify_ec_enabled()
        html.begin_form("rule")
        vs = self._valuespec()
        vs.render_input("rule", self._rule)
        vs.set_focus("rule")
        html.button("save", _("Save"))
        html.hidden_fields()
        html.end_form()

    def _valuespec(self):
        return vs_mkeventd_rule(self._rule_pack.get('customer'))


@mode_registry.register
class ModeEventConsoleStatus(ABCEventConsoleMode):
    @classmethod
    def name(cls):
        return "mkeventd_status"

    @classmethod
    def permissions(cls):
        return []

    def title(self):
        return _("Local server status")

    def buttons(self):
        home_button()
        self._rules_button()
        self._config_button()
        self._mibs_button()

    def action(self):
        if not config.user.may("mkeventd.switchmode"):
            return

        if html.request.has_var("_switch_sync"):
            new_mode = "sync"
        else:
            new_mode = "takeover"
        c = wato_confirm(_("Confirm switching replication mode"),
                         _("Do you really want to switch the event daemon to %s mode?") % new_mode)
        if c:
            cmk.gui.mkeventd.execute_command("SWITCHMODE", [new_mode], config.omd_site())
            watolib.log_audit(None, "mkeventd-switchmode",
                              _("Switched replication slave mode to %s") % new_mode)
            return None, _("Switched to %s mode") % new_mode
        elif c is False:
            return ""
        return

    def page(self):
        self._verify_ec_enabled()

        if not cmk.gui.mkeventd.daemon_running():
            warning = _("The Event Console Daemon is currently not running. ")
            warning += _(
                "Please make sure that you have activated it with <tt>omd config set MKEVENTD on</tt> "
                "before starting this site.")
            html.show_warning(warning)
            return

        status = cmk.gui.mkeventd.get_local_ec_status()
        repl_mode = status["status_replication_slavemode"]
        html.h3(_("Current status of local Event Console"))
        html.open_ul()
        html.li(_("Event Daemon is running."))
        html.open_li()
        html.write_text("%s: " % _("Current replication mode"))
        html.open_b()
        html.write("%s" % ({
            "sync": _("synchronize"),
            "takeover": _("Takeover!"),
        }.get(repl_mode, _("master / standalone"))))
        html.close_b()
        html.close_li()
        if repl_mode in ["sync", "takeover"]:
            html.open_li()
            html.write_text(
                _("Status of last synchronization: <b>%s</b>") %
                (status["status_replication_success"] and _("Success") or _("Failed!")))
            html.close_li()
            last_sync = status["status_replication_last_sync"]
            if last_sync:
                html.li(_("Last successful sync %d seconds ago.") % (time.time() - last_sync))
            else:
                html.li(_("No successful synchronization so far."))

        html.close_ul()

        if config.user.may("mkeventd.switchmode"):
            html.begin_form("switch")
            if repl_mode == "sync":
                html.button("_switch_takeover", _("Switch to Takeover mode!"))
            elif repl_mode == "takeover":
                html.button("_switch_sync", _("Switch back to sync mode!"))
            html.hidden_fields()
            html.end_form()


@mode_registry.register
class ModeEventConsoleSettings(ABCEventConsoleMode, GlobalSettingsMode):
    @classmethod
    def name(cls):
        return "mkeventd_config"

    @classmethod
    def permissions(cls):
        return ["mkeventd.config"]

    def __init__(self):
        super(ModeEventConsoleSettings, self).__init__()

        self._default_values = ConfigDomainEventConsole().default_globals()
        self._current_settings = watolib.load_configuration_settings()

    def _groups(self, show_all=False):
        return [
            g for g in sorted([g_class() for g_class in config_variable_group_registry.values()],
                              key=lambda grp: grp.sort_index())
            if isinstance(g, ConfigVariableGroupEventConsole)
        ]

    def title(self):
        if self._search:
            return html.render_text(_("Event Console configuration matching '%s'") % self._search)
        return _('Event Console Configuration')

    def buttons(self):
        home_button()
        self._rules_button()
        self._changes_button()
        html.context_button(_("Server Status"),
                            html.makeuri_contextless([("mode", "mkeventd_status")]), "status")

    # TODO: Consolidate with ModeEditGlobals.action()
    def action(self):
        varname = html.request.var("_varname")
        action = html.request.var("_action")
        if not varname:
            return

        try:
            config_variable = config_variable_registry[varname]()
        except KeyError:
            raise MKUserError("_varname", _("The requested global setting does not exist."))

        def_value = config_variable.valuespec().default_value()

        if action == "reset" and not isinstance(config_variable.valuespec(), Checkbox):
            c = wato_confirm(
                _("Resetting configuration variable"),
                _("Do you really want to reset the configuration variable <b>%s</b> "
                  "back to the default value of <b><tt>%s</tt></b>?") %
                (varname, config_variable.valuespec().value_to_text(def_value)))
        else:
            if not html.check_transaction():
                return
            c = True  # no confirmation for direct toggle

        if c:
            if varname in self._current_settings:
                self._current_settings[varname] = not self._current_settings[varname]
            else:
                self._current_settings[varname] = not def_value
            msg = _("Changed Configuration variable %s to %s.") % (
                varname, self._current_settings[varname] and _("on") or _("off"))

            watolib.save_global_settings(self._current_settings)

            self._add_change("edit-configvar", msg)

            if action == "_reset":
                return "mkeventd_config", msg
            return "mkeventd_config"
        elif c is False:
            return ""

    def _edit_mode(self):
        return "mkeventd_edit_configvar"

    def page(self):
        self._verify_ec_enabled()
        self._show_configuration_variables(self._groups())


class ConfigVariableGroupEventConsole(ConfigVariableGroup):
    pass


@config_variable_group_registry.register
class ConfigVariableGroupEventConsoleGeneric(ConfigVariableGroupEventConsole):
    def title(self):
        return _("Event Console: Generic")

    def sort_index(self):
        return 18


@config_variable_group_registry.register
class ConfigVariableGroupEventConsoleLogging(ConfigVariableGroupEventConsole):
    def title(self):
        return _("Event Console: Logging & Diagnose")

    def sort_index(self):
        return 19


@config_variable_group_registry.register
class ConfigVariableGroupEventConsoleSNMP(ConfigVariableGroupEventConsole):
    def title(self):
        return _("Event Console: SNMP traps")

    def sort_index(self):
        return 20


@mode_registry.register
class ModeEventConsoleEditGlobalSetting(EditGlobalSettingMode):
    @classmethod
    def name(cls):
        return "mkeventd_edit_configvar"

    @classmethod
    def permissions(cls):
        return ["mkeventd.config"]

    def __init__(self):
        super(ModeEventConsoleEditGlobalSetting, self).__init__()
        self._need_restart = None

    def title(self):
        return _("Event Console Configuration")

    def buttons(self):
        html.context_button(_("Abort"),
                            watolib.folder_preserving_link([("mode", "mkeventd_config")]), "abort")

    def _back_mode(self):
        return "mkeventd_config"

    def _affected_sites(self):
        return _get_event_console_sync_sites()


def _get_event_console_sync_sites():
    """Returns a list of site ids which gets the Event Console configuration replicated"""
    return [s[0] for s in config.get_event_console_site_choices()]


@mode_registry.register
class ModeEventConsoleMIBs(ABCEventConsoleMode):
    @classmethod
    def name(cls):
        return "mkeventd_mibs"

    @classmethod
    def permissions(cls):
        return ["mkeventd.config"]

    def title(self):
        return _('SNMP MIBs for Trap Translation')

    def buttons(self):
        home_button()
        self._rules_button()
        self._changes_button()
        self._status_button()
        self._config_button()

    def action(self):
        if html.request.has_var("_delete"):
            filename = html.request.var("_delete")
            mibs = self._load_snmp_mibs(cmk.gui.mkeventd.mib_upload_dir())
            if filename in mibs:
                c = wato_confirm(
                    _("Confirm MIB deletion"),
                    _("Do you really want to delete the MIB file <b>%s</b>?") % filename)
                if c:
                    self._delete_mib(filename, mibs[filename]["name"])
                elif c is False:
                    return ""
                else:
                    return
        elif html.request.uploaded_file("_upload_mib"):
            uploaded_mib = html.request.uploaded_file("_upload_mib")
            filename, mimetype, content = uploaded_mib
            if filename:
                try:
                    msg = self._upload_mib(filename, mimetype, content)
                    return None, msg
                except Exception as e:
                    if config.debug:
                        raise
                    else:
                        raise MKUserError("_upload_mib", "%s" % e)

        elif html.request.var("_bulk_delete_custom_mibs"):
            return self._bulk_delete_custom_mibs_after_confirm()

    def _upload_mib(self, filename, mimetype, content):
        self._validate_mib_file_name(filename)

        if self._is_zipfile(io.BytesIO(content)):
            msg = self._process_uploaded_zip_file(filename, content)
        else:
            if mimetype == "application/tar" or filename.lower().endswith(
                    ".gz") or filename.lower().endswith(".tgz"):
                raise Exception(_("Sorry, uploading TAR/GZ files is not yet implemented."))

            msg = self._process_uploaded_mib_file(filename, content)

        return msg

    # Used zipfile.is_zipfile(io.BytesIO(content)) before, but this only
    # possible with python 2.7. zipfile is only supporting checking of files by
    # their path.
    def _is_zipfile(self, fo):
        try:
            zipfile.ZipFile(fo)
            return True
        except zipfile.BadZipfile:
            return False

    def _process_uploaded_zip_file(self, filename, content):
        zip_obj = zipfile.ZipFile(io.BytesIO(content))
        messages = []
        for entry in zip_obj.infolist():
            success, fail = 0, 0
            try:
                mib_file_name = entry.filename
                if mib_file_name[-1] == "/":
                    continue  # silently skip directories

                self._validate_mib_file_name(mib_file_name)

                mib_obj = zip_obj.open(mib_file_name)
                messages.append(self._process_uploaded_mib_file(mib_file_name, mib_obj.read()))
                success += 1
            except Exception as e:
                messages.append(_("Skipped %s: %s") % (html.render_text(mib_file_name), e))
                fail += 1

        return "<br>\n".join(messages) + \
               "<br><br>\nProcessed %d MIB files, skipped %d MIB files" % (success, fail)

    def _process_uploaded_mib_file(self, filename, content):
        if '.' in filename:
            mibname = filename.split('.')[0]
        else:
            mibname = filename

        msg = self._validate_and_compile_mib(mibname.upper(), content)
        with (cmk.gui.mkeventd.mib_upload_dir() / filename).open("wb") as f:
            f.write(content)
        self._add_change("uploaded-mib", _("MIB %s: %s") % (filename, msg))
        return msg

    def _validate_mib_file_name(self, filename):
        if filename.startswith(".") or "/" in filename:
            raise Exception(_("Invalid filename"))

    def _validate_and_compile_mib(self, mibname, content):
        defaultMibPackages = PySnmpCodeGen.defaultMibPackages
        baseMibs = PySnmpCodeGen.baseMibs

        compiled_mibs_dir = _compiled_mibs_dir()
        store.mkdir(compiled_mibs_dir)

        # This object manages the compilation of the uploaded SNMP mib
        # but also resolving dependencies and compiling dependents
        compiler = MibCompiler(SmiV1CompatParser(), PySnmpCodeGen(),
                               PyFileWriter(compiled_mibs_dir))

        # FIXME: This is a temporary local fix that should be removed once
        # handling of file contents uses a uniformly encoded representation
        try:
            content = content.decode("utf-8")
        except UnicodeDecodeError:
            content = content.decode("latin-1")

        # Provides the just uploaded MIB module
        compiler.addSources(CallbackReader(lambda m, c: m == mibname and c or '', content))

        # Directories containing ASN1 MIB files which may be used for
        # dependency resolution
        compiler.addSources(
            *[FileReader(str(path)) for path, _title in cmk.gui.mkeventd.mib_dirs()])

        # check for already compiled MIBs
        compiler.addSearchers(PyFileSearcher(compiled_mibs_dir))

        # and also check PySNMP shipped compiled MIBs
        compiler.addSearchers(*[PyPackageSearcher(x) for x in defaultMibPackages])

        # never recompile MIBs with MACROs
        compiler.addSearchers(StubSearcher(*baseMibs))

        try:
            if not content.strip():
                raise Exception(_("The file is empty"))

            results = compiler.compile(mibname, ignoreErrors=True, genTexts=True)

            errors = []
            for name, state_obj in sorted(results.items()):
                if mibname == name and state_obj == 'failed':
                    raise Exception(_('Failed to compile your module: %s') % state_obj.error)

                if state_obj == 'missing':
                    errors.append(_('%s - Dependency missing') % name)
                elif state_obj == 'failed':
                    errors.append(_('%s - Failed to compile (%s)') % (name, state_obj.error))

            msg = _("MIB file %s uploaded.") % mibname
            if errors:
                msg += '<br>' + _('But there were errors:') + '<br>'
                msg += '<br>\n'.join(errors)
            return msg

        except PySmiError as e:
            if config.debug:
                raise e
            raise Exception(_('Failed to process your MIB file (%s): %s') % (mibname, e))

    def _bulk_delete_custom_mibs_after_confirm(self):
        custom_mibs = self._load_snmp_mibs(cmk.gui.mkeventd.mib_upload_dir())
        selected_custom_mibs = []
        for varname, _value in html.request.itervars(prefix="_c_mib_"):
            if html.get_checkbox(varname):
                filename = varname.split("_c_mib_")[-1]
                if filename in custom_mibs:
                    selected_custom_mibs.append(filename)

        if selected_custom_mibs:
            c = wato_confirm(
                _("Confirm deletion of selected MIBs"),
                _("Do you really want to delete the selected %d MIBs?") % len(selected_custom_mibs))
            if c:
                for filename in selected_custom_mibs:
                    self._delete_mib(filename, custom_mibs[filename]["name"])
                return
            elif c is False:
                return ""  # not yet confirmed
            return  # browser reload

    def _delete_mib(self, filename, mib_name):
        self._add_change("delete-mib", _("Deleted MIB %s") % filename)

        # Delete the uploaded mib file
        (cmk.gui.mkeventd.mib_upload_dir() / filename).unlink()

        # Also delete the compiled files
        compiled_mibs_dir = _compiled_mibs_dir()
        for f in [
                compiled_mibs_dir + "/" + mib_name + ".py",
                compiled_mibs_dir + "/" + mib_name + ".pyc",
                compiled_mibs_dir + "/" + filename.rsplit('.', 1)[0].upper() + ".py",
                compiled_mibs_dir + "/" + filename.rsplit('.', 1)[0].upper() + ".pyc",
        ]:
            if os.path.exists(f):
                os.remove(f)

    def page(self):
        self._verify_ec_enabled()
        html.h3(_("Upload MIB file"))
        html.write_text(
            _("Use this form to upload MIB files for translating incoming SNMP traps. "
              "You can upload single MIB files with the extension <tt>.mib</tt> or "
              "<tt>.txt</tt>, but you can also upload multiple MIB files at once by "
              "packing them into a <tt>.zip</tt> file. Only files in the root directory "
              "of the zip file will be processed.<br><br>"))

        html.begin_form("upload_form", method="POST")
        forms.header(_("Upload MIB file"))

        forms.section(_("Select file"))
        html.upload_file("_upload_mib")
        forms.end()

        html.button("upload_button", _("Upload MIB(s)"), "submit")
        html.hidden_fields()
        html.end_form()

        cmk.gui.mkeventd.mib_upload_dir().mkdir(parents=True, exist_ok=True)

        for path, title in cmk.gui.mkeventd.mib_dirs():
            self._show_mib_table(path, title)

    def _show_mib_table(self, path, title):
        # type: (Path, Text) -> None
        is_custom_dir = path == cmk.gui.mkeventd.mib_upload_dir()

        if is_custom_dir:
            html.begin_form("bulk_delete_form", method="POST")

        with table_element("mibs_%s" % path, title, searchable=False) as table:
            for filename, mib in sorted(self._load_snmp_mibs(path).items()):
                table.row()

                if is_custom_dir:
                    table.cell("<input type=button class=checkgroup name=_toggle_group"
                               " onclick=\"cmk.selection.toggle_all_rows();\" value=\"%s\" />" %
                               _('X'),
                               sortable=False,
                               css="buttons")
                    html.checkbox("_c_mib_%s" % filename, deflt=False)

                table.cell(_("Actions"), css="buttons")
                if is_custom_dir:
                    delete_url = make_action_link([("mode", "mkeventd_mibs"),
                                                   ("_delete", filename)])
                    html.icon_button(delete_url, _("Delete this MIB"), "delete")

                table.text_cell(_("Filename"), filename)
                table.text_cell(_("MIB"), mib.get("name", ""))
                table.text_cell(_("Organization"), mib.get("organization", ""))
                table.text_cell(_("Size"),
                                cmk.utils.render.fmt_bytes(mib.get("size", 0)),
                                css="number")

        if is_custom_dir:
            html.button("_bulk_delete_custom_mibs",
                        _("Bulk Delete"),
                        "submit",
                        style="margin-top:10px")
            html.hidden_fields()
            html.end_form()

    def _load_snmp_mibs(self, path):
        # type: (Path) -> Dict[str, Dict]
        found = {}  # type: Dict[str, Dict]

        if not path.exists():
            return found

        for file_obj in path.iterdir():
            if file_obj.is_dir():
                continue

            if file_obj.name.startswith("."):
                continue

            found[file_obj.name] = self._parse_snmp_mib_header(file_obj)
        return found

    def _parse_snmp_mib_header(self, path):
        # type: (Path) -> Dict[str, Union[int, str]]
        mib = {"size": path.stat().st_size}  # type: Dict[str, Union[int, str]]

        # read till first "OBJECT IDENTIFIER" declaration
        head = ''
        with path.open() as f:
            for line in f:
                if not line.startswith("--"):
                    if 'OBJECT IDENTIFIER' in line:
                        break  # seems the header is finished
                    head += line

        # now try to extract some relevant information from the header

        matches = re.search('ORGANIZATION[^"]+"([^"]+)"', head, re.M)
        if matches:
            mib['organization'] = matches.group(1)

        matches = re.search(r'^\s*([A-Z0-9][A-Z0-9-]+)\s', head, re.I | re.M)
        if matches:
            mib['name'] = matches.group(1)

        return mib


#.
#   .--Permissions---------------------------------------------------------.
#   |        ____                     _         _                          |
#   |       |  _ \ ___ _ __ _ __ ___ (_)___ ___(_) ___  _ __  ___          |
#   |       | |_) / _ \ '__| '_ ` _ \| / __/ __| |/ _ \| '_ \/ __|         |
#   |       |  __/  __/ |  | | | | | | \__ \__ \ | (_) | | | \__ \         |
#   |       |_|   \___|_|  |_| |_| |_|_|___/___/_|\___/|_| |_|___/         |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   | Declaration of Event Console specific permissions for Multisite      |
#   '----------------------------------------------------------------------'


@permission_registry.register
class PermissionECConfig(Permission):
    @property
    def section(self):
        return cmk.gui.mkeventd.PermissionSectionEventConsole

    @property
    def permission_name(self):
        return "config"

    @property
    def title(self):
        return _("Configuration of Event Console")

    @property
    def description(self):
        return _("This permission allows to configure the global settings " "of the event console.")

    @property
    def defaults(self):
        return ["admin"]


@permission_registry.register
class PermissionECEdit(Permission):
    @property
    def section(self):
        return cmk.gui.mkeventd.PermissionSectionEventConsole

    @property
    def permission_name(self):
        return "edit"

    @property
    def title(self):
        return _("Configuration of event rules")

    @property
    def description(self):
        return _("This permission allows the creation, modification and "
                 "deletion of event correlation rules.")

    @property
    def defaults(self):
        return ["admin"]


@permission_registry.register
class PermissionECActivate(Permission):
    @property
    def section(self):
        return cmk.gui.mkeventd.PermissionSectionEventConsole

    @property
    def permission_name(self):
        return "activate"

    @property
    def title(self):
        return _("Activate changes for event console")

    @property
    def description(self):
        return _("Activation of changes for the event console (rule modification, "
                 "global settings) is done separately from the monitoring configuration "
                 "and needs this permission.")

    @property
    def defaults(self):
        return ["admin"]


@permission_registry.register
class PermissionECSwitchMode(Permission):
    @property
    def section(self):
        return cmk.gui.mkeventd.PermissionSectionEventConsole

    @property
    def permission_name(self):
        return "switchmode"

    @property
    def title(self):
        return _("Switch slave replication mode")

    @property
    def description(self):
        return _("This permission is only useful if the Event Console is "
                 "setup as a replication slave. It allows a manual switch "
                 "between sync and takeover mode.")

    @property
    def defaults(self):
        return ["admin"]


@main_module_registry.register
class MainModuleEventConsole(MainModule):
    @property
    def mode_or_url(self):
        return "mkeventd_rule_packs"

    @property
    def title(self):
        return _("Event Console")

    @property
    def icon(self):
        return "mkeventd"

    @property
    def permission(self):
        return "mkeventd.edit"

    @property
    def description(self):
        return _("Manage event classification and correlation rules for the Event Console")

    @property
    def sort_index(self):
        return 68

    @property
    def enabled(self):
        return config.mkeventd_enabled


#.
#   .--Settings & Rules----------------------------------------------------.
#   | ____       _   _   _                       ____        _             |
#   |/ ___|  ___| |_| |_(_)_ __   __ _ ___   _  |  _ \ _   _| | ___  ___   |
#   |\___ \ / _ \ __| __| | '_ \ / _` / __|_| |_| |_) | | | | |/ _ \/ __|  |
#   | ___) |  __/ |_| |_| | | | | (_| \__ \_   _|  _ <| |_| | |  __/\__ \  |
#   ||____/ \___|\__|\__|_|_| |_|\__, |___/ |_| |_| \_\\__,_|_|\___||___/  |
#   |                            |___/                                     |
#   +----------------------------------------------------------------------+
#   | Declarations for global settings of EC parameters and of a rule for  |
#   | active checks that query the EC status of a host.                    |
#   '----------------------------------------------------------------------'


@config_variable_registry.register
class ConfigVariableEventConsoleRemoteStatus(ConfigVariable):
    def group(self):
        return ConfigVariableGroupEventConsoleGeneric

    def domain(self):
        return ConfigDomainEventConsole

    def ident(self):
        return "remote_status"

    def valuespec(self):
        return Optional(
            Tuple(elements=[
                Integer(
                    title=_("Port number:"),
                    help=_(
                        "If you are running the Event Console as a non-root (such as in an OMD site) "
                        "please choose port number greater than 1024."),
                    minvalue=1,
                    maxvalue=65535,
                    default_value=6558,
                ),
                Checkbox(
                    title=_("Security"),
                    label=_("allow execution of commands and actions via TCP"),
                    help=_("Without this option the access is limited to querying the current "
                           "and historic event status."),
                    default_value=False,
                    true_label=_("allow commands"),
                    false_label=_("no commands"),
                ),
                Optional(
                    ListOfStrings(
                        help=_("The access to the event status via TCP will only be allowed from "
                               "this source IP addresses"),
                        valuespec=IPv4Address(),
                        orientation="horizontal",
                        allow_empty=False,
                    ),
                    label=_("Restrict access to the following source IP addresses"),
                    none_label=_("access unrestricted"),
                )
            ],),
            title=_("Access to event status via TCP"),
            help=
            _("In Multisite setups if you want <a href=\"%s\">event status checks</a> for hosts that "
              "live on a remote site you need to activate remote access to the event status socket "
              "via TCP. This allows to query the current event status via TCP. If you do not restrict "
              "this to queries also event actions are possible from remote. This feature is not used "
              "by the event status checks nor by Multisite so we propose not allowing commands via TCP."
             ) % "wato.py?mode=edit_ruleset&varname=active_checks%3Amkevents",
            none_label=_("no access via TCP"),
        )


@config_variable_registry.register
class ConfigVariableEventConsoleReplication(ConfigVariable):
    def group(self):
        return ConfigVariableGroupEventConsoleGeneric

    def domain(self):
        return ConfigDomainEventConsole

    def ident(self):
        return "replication"

    def valuespec(self):
        return Optional(
            Dictionary(
                optional_keys=["takeover", "fallback", "disabled", "logging"],
                elements=[
                    ("master",
                     Tuple(
                         title=_("Master Event Console"),
                         help=_(
                             "Specify the host name or IP address of the master Event Console that "
                             "you want to replicate from. The port number must be the same as set "
                             "in the master in <i>Access to event status via TCP</i>."),
                         elements=[
                             TextAscii(
                                 title=_("Hostname/IP address of Master Event Console:"),
                                 allow_empty=False,
                                 attrencode=True,
                             ),
                             Integer(
                                 title=_("TCP Port number of status socket:"),
                                 minvalue=1,
                                 maxvalue=65535,
                                 default_value=6558,
                             ),
                         ],
                     )),
                    ("interval",
                     Integer(
                         title=_("Replication interval"),
                         help=_("The replication will be triggered each this number of seconds"),
                         label=_("Do a replication every"),
                         unit=_("sec"),
                         minvalue=1,
                         default_value=10,
                     )),
                    ("connect_timeout",
                     Integer(
                         title=_("Connect Timeout"),
                         help=_("TCP connect timeout for connecting to the master"),
                         label=_("Try bringing up TCP connection for"),
                         unit=_("sec"),
                         minvalue=1,
                         default_value=10,
                     )),
                    ("takeover",
                     Integer(
                         title=_("Automatic takeover"),
                         help=_("If you enable this option then the slave will automatically "
                                "takeover and enable event processing if the master is for "
                                "the configured number of seconds unreachable."),
                         label=_("Takeover after a master downtime of"),
                         unit=_("sec"),
                         minvalue=1,
                         default_value=30,
                     )),
                    ("fallback",
                     Integer(
                         title=_("Automatic fallback"),
                         help=_("If you enable this option then the slave will automatically "
                                "fallback from takeover mode to slavemode if the master is "
                                "rechable again within the selected number of seconds since "
                                "the previous unreachability (not since the takeover)"),
                         label=_("Fallback if master comes back within"),
                         unit=_("sec"),
                         minvalue=1,
                         default_value=60,
                     )),
                    ("disabled",
                     FixedValue(
                         True,
                         totext=_("Replication is disabled"),
                         title=_("Currently disable replication"),
                         help=_("This allows you to disable the replication without loosing "
                                "your settings. If you check this box, then no replication "
                                "will be done and the Event Console will act as its own master."),
                     )),
                    ("logging",
                     FixedValue(
                         True,
                         title=_("Log replication events"),
                         totext=_("logging is enabled"),
                         help=_("Enabling this option will create detailed log entries for all "
                                "replication activities of the slave. If disabled only problems "
                                "will be logged."),
                     )),
                ]),
            title=_("Enable replication from a master"),
        )


@config_variable_registry.register
class ConfigVariableEventConsoleRetentionInterval(ConfigVariable):
    def group(self):
        return ConfigVariableGroupEventConsoleGeneric

    def domain(self):
        return ConfigDomainEventConsole

    def ident(self):
        return "retention_interval"

    def valuespec(self):
        return Age(
            title=_("State Retention Interval"),
            help=_("In this interval the event daemon will save its state "
                   "to disk, so that you won't lose your current event "
                   "state in case of a crash."),
        )


@config_variable_registry.register
class ConfigVariableEventConsoleHousekeepingInterval(ConfigVariable):
    def group(self):
        return ConfigVariableGroupEventConsoleGeneric

    def domain(self):
        return ConfigDomainEventConsole

    def ident(self):
        return "housekeeping_interval"

    def valuespec(self):
        return Age(
            title=_("Housekeeping Interval"),
            help=_("From time to time the eventd checks for messages that are expected to "
                   "be seen on a regular base, for events that time out and yet for "
                   "count periods that elapse. Here you can specify the regular interval "
                   "for that job."),
        )


@config_variable_registry.register
class ConfigVariableEventConsoleStatisticsInterval(ConfigVariable):
    def group(self):
        return ConfigVariableGroupEventConsoleGeneric

    def domain(self):
        return ConfigDomainEventConsole

    def ident(self):
        return "statistics_interval"

    def valuespec(self):
        return Age(
            title=_("Statistics Interval"),
            help=_("The event daemon keeps statistics about the rate of messages, events "
                   "rule hits, and other stuff. These values are updated in the interval "
                   "configured here and are available in the sidebar snapin <i>Event Console "
                   "Performance</i>"),
        )


@config_variable_registry.register
class ConfigVariableEventConsoleLogMessages(ConfigVariable):
    def group(self):
        return ConfigVariableGroupEventConsoleGeneric

    def domain(self):
        return ConfigDomainEventConsole

    def ident(self):
        return "log_messages"

    def valuespec(self):
        return Checkbox(
            title=_("Syslog-like message logging"),
            label=_("Log all messages into syslog-like logfiles"),
            help=_("When this option is enabled, then <b>every</b> incoming message is being "
                   "logged into the directory <tt>messages</tt> in the Event Consoles state "
                   "directory. The logfile rotation is analog to that of the history logfiles. "
                   "Please note that if you have lots of incoming messages then these "
                   "files can get very large."),
        )


@config_variable_registry.register
class ConfigVariableEventConsoleRuleOptimizer(ConfigVariable):
    def group(self):
        return ConfigVariableGroupEventConsoleGeneric

    def domain(self):
        return ConfigDomainEventConsole

    def ident(self):
        return "rule_optimizer"

    def valuespec(self):
        return Checkbox(
            title=_("Optimize rule execution"),
            label=_("enable optimized rule execution"),
            help=_("This option turns on a faster algorithm for matching events to rules. "),
        )


@config_variable_registry.register
class ConfigVariableEventConsoleActions(ConfigVariable):
    def group(self):
        return ConfigVariableGroupEventConsoleGeneric

    def domain(self):
        return ConfigDomainEventConsole

    def ident(self):
        return "actions"

    def valuespec(self):
        return ActionList(
            Foldable(
                Dictionary(
                    title=_("Action"),
                    optional_keys=False,
                    elements=[
                        ("id",
                         ID(
                             title=_("Action ID"),
                             help=_("A unique ID of this action that is used as an internal "
                                    "reference in the configuration. Changing the ID is not "
                                    "possible if still rules refer to this ID."),
                             allow_empty=False,
                             size=12,
                         )),
                        ("title",
                         TextUnicode(
                             title=_("Title"),
                             help=_("A descriptive title of this action."),
                             allow_empty=False,
                             size=64,
                             attrencode=True,
                         )),
                        ("disabled",
                         Checkbox(
                             title=_("Disable"),
                             label=_("Currently disable execution of this action"),
                         )),
                        (
                            "hidden",
                            Checkbox(
                                title=_("Hide from Status GUI"),
                                label=_("Do not offer this action as a command on open events"),
                                help=_("If you enabled this option, then this action will not "
                                       "be available as an interactive user command. It is usable "
                                       "as an ad-hoc action when a rule fires, nevertheless."),
                            ),
                        ),
                        (
                            "action",
                            CascadingDropdown(
                                title=_("Type of Action"),
                                help=_("Choose the type of action to perform"),
                                choices=[
                                    ("email", _("Send Email"),
                                     Dictionary(optional_keys=False,
                                                elements=[
                                                    (
                                                        "to",
                                                        TextAscii(
                                                            title=_("Recipient Email address"),
                                                            allow_empty=False,
                                                            attrencode=True,
                                                        ),
                                                    ),
                                                    (
                                                        "subject",
                                                        TextUnicode(
                                                            title=_("Subject"),
                                                            allow_empty=False,
                                                            size=64,
                                                            attrencode=True,
                                                        ),
                                                    ),
                                                    (
                                                        "body",
                                                        TextAreaUnicode(
                                                            title=_("Body"),
                                                            help=lambda: _(
                                                                "Text-body of the email to send. ")
                                                            + substitute_help(),
                                                            cols=64,
                                                            rows=10,
                                                            attrencode=True,
                                                        ),
                                                    ),
                                                ])),
                                    ("script", _("Execute Shell Script"),
                                     Dictionary(
                                         optional_keys=False,
                                         elements=[
                                             ("script",
                                              TextAreaUnicode(
                                                  title=_("Script body"),
                                                  help=lambda:
                                                  _("This script will be executed using the BASH shell. "
                                                   ) + substitute_help() + "<br>" +
                                                  _("These information are also available as environment variables with the prefix "
                                                    "<tt>CMK_</tt>. For example the text of the event is available as "
                                                    "<tt>CMK_TEXT</tt> as environment variable."),
                                                  cols=64,
                                                  rows=10,
                                                  attrencode=True,
                                              )),
                                         ])),
                                ]),
                        ),
                    ],
                ),
                title_function=lambda value: not value["id"] and _("New Action") or
                (value["id"] + " - " + value["title"]),
            ),
            title=_("Actions (Emails & Scripts)"),
            help=_("Configure that possible actions that can be performed when a "
                   "rule triggers and also manually by a user."),
            totext=_("%d actions"),
            add_label=_("Add new action"),
        )

    # TODO: Why? Can we drop this?
    def allow_reset(self):
        return False


@config_variable_registry.register
class ConfigVariableEventConsoleArchiveOrphans(ConfigVariable):
    def group(self):
        return ConfigVariableGroupEventConsoleGeneric

    def domain(self):
        return ConfigDomainEventConsole

    def ident(self):
        return "archive_orphans"

    def valuespec(self):
        return Checkbox(
            title=_("Force message archiving"),
            label=_("Archive messages that do not match any rule"),
            help=_("When this option is enabled then messages that do not match "
                   "a rule will be archived into the event history anyway (Messages "
                   "that do match a rule will be archived always, as long as they are not "
                   "explicitely dropped are being aggregated by counting.)"),
        )


@config_variable_registry.register
class ConfigVariableHostnameTranslation(ConfigVariable):
    def group(self):
        return ConfigVariableGroupEventConsoleGeneric

    def domain(self):
        return ConfigDomainEventConsole

    def ident(self):
        return "hostname_translation"

    def valuespec(self):
        return HostnameTranslation(
            title=_("Hostname translation for incoming messages"),
            help=_("When the Event Console receives a message than the host name "
                   "that is contained in that message will be translated using "
                   "this configuration. This can be used for unifying host names "
                   "from message with those of actively monitored hosts. Note: this translation "
                   "is happening before any rule is being applied."),
        )


def vs_ec_event_limit_actions(notify_txt):
    return DropdownChoice(
        title=_("Action"),
        help=_("Choose the action the Event Console should trigger once "
               "the limit is reached."),
        choices=[
            ("stop", _("Stop creating new events")),
            ("stop_overflow", _("Stop creating new events, create overflow event")),
            ("stop_overflow_notify",
             "%s, %s" % (_("Stop creating new events, create overflow event"), notify_txt)),
            ("delete_oldest", _("Delete oldest event, create new event")),
        ],
        default_value="stop_overflow_notify",
    )


def vs_ec_rule_limit():
    return Dictionary(
        title=_("Rule limit"),
        help=_("You can limit the number of current events created by a single "
               "rule here. This is meant to "
               "prevent you from too generous rules creating a lot of events.<br>"
               "Once the limit is reached, the Event Console will stop the rule "
               "creating new current events until the number of current "
               "events has been reduced to be below this limit. In the "
               "moment the limit is reached, the Event Console will notify "
               "the configured contacts of the rule or create a notification "
               "with empty contact information."),
        elements=[
            ("limit",
             Integer(
                 title=_("Limit"),
                 minvalue=1,
                 default_value=1000,
                 unit=_("current events"),
             )),
            ("action", vs_ec_event_limit_actions("notify contacts in rule or fallback contacts")),
        ],
        optional_keys=[],
    )


def vs_ec_host_limit(title):
    return Dictionary(
        title=title,
        help=_("You can limit the number of current events created by a single "
               "host here. This is meant to "
               "prevent you from message storms created by one device.<br>"
               "Once the limit is reached, the Event Console will block "
               "all future incoming messages sent by this host until the "
               "number of current "
               "events has been reduced to be below this limit. In the "
               "moment the limit is reached, the Event Console will notify "
               "the configured contacts of the host."),
        elements=[
            ("limit",
             Integer(
                 title=_("Limit"),
                 minvalue=1,
                 default_value=1000,
                 unit=_("current events"),
             )),
            ("action", vs_ec_event_limit_actions("notify contacts of the host")),
        ],
        optional_keys=[],
    )


@config_variable_registry.register
class ConfigVariableEventConsoleEventLimit(ConfigVariable):
    def group(self):
        return ConfigVariableGroupEventConsoleGeneric

    def domain(self):
        return ConfigDomainEventConsole

    def ident(self):
        return "event_limit"

    def valuespec(self):
        return Dictionary(
            title=_("Limit amount of current events"),
            help=_("This option helps you to protect the Event Console from resoure "
                   "problems which may occur in case of too many current events at the "
                   "same time."),
            elements=[
                ("by_host", vs_ec_host_limit(title=_("Host limit"))),
                ("by_rule", vs_ec_rule_limit()),
                ("overall",
                 Dictionary(
                     title=_("Overall current events"),
                     help=_("To protect you against a continously growing list of current "
                            "events created by different hosts or rules, you can configure "
                            "this overall limit of current events. All currently current events "
                            "are counted and once the limit is reached, no further events "
                            "will be currented which means that new incoming messages will be "
                            "dropped. In the moment the limit is reached, the Event Console "
                            "will create a notification with empty contact information."),
                     elements=[
                         ("limit",
                          Integer(
                              title=_("Limit"),
                              minvalue=1,
                              default_value=10000,
                              unit=_("current events"),
                          )),
                         ("action", vs_ec_event_limit_actions("notify all fallback contacts")),
                     ],
                     optional_keys=[],
                 )),
            ],
            optional_keys=[],
        )


@config_variable_registry.register
class ConfigVariableEventConsoleHistoryRotation(ConfigVariable):
    def group(self):
        return ConfigVariableGroupEventConsoleGeneric

    def domain(self):
        return ConfigDomainEventConsole

    def ident(self):
        return "history_rotation"

    def valuespec(self):
        return DropdownChoice(
            title=_("Event history logfile rotation"),
            help=_(
                "Specify at which time period a new file for the event history will be created."),
            choices=[("daily", _("daily")), ("weekly", _("weekly"))],
        )


@config_variable_registry.register
class ConfigVariableEventConsoleHistoryLifetime(ConfigVariable):
    def group(self):
        return ConfigVariableGroupEventConsoleGeneric

    def domain(self):
        return ConfigDomainEventConsole

    def ident(self):
        return "history_lifetime"

    def valuespec(self):
        return Integer(
            title=_("Event history lifetime"),
            help=_("After this number of days old logfile of event history "
                   "will be deleted."),
            unit=_("days"),
            minvalue=1,
        )


@config_variable_registry.register
class ConfigVariableEventConsoleSocketQueueLength(ConfigVariable):
    def group(self):
        return ConfigVariableGroupEventConsoleGeneric

    def domain(self):
        return ConfigDomainEventConsole

    def ident(self):
        return "socket_queue_len"

    def valuespec(self):
        return Integer(
            title=_("Max. number of pending connections to the status socket"),
            help=_(
                "When the Multisite GUI or the active check check_mkevents connects "
                "to the socket of the event daemon in order to retrieve information "
                "about current and historic events then its connection request might "
                "be queued before being processed. This setting defines the number of unaccepted "
                "connections to be queued before refusing new connections."),
            minvalue=1,
            label="max.",
            unit=_("pending connections"),
        )


@config_variable_registry.register
class ConfigVariableEventConsoleEventSocketQueueLength(ConfigVariable):
    def group(self):
        return ConfigVariableGroupEventConsoleGeneric

    def domain(self):
        return ConfigDomainEventConsole

    def ident(self):
        return "eventsocket_queue_len"

    def valuespec(self):
        return Integer(
            title=_("Max. number of pending connections to the event socket"),
            help=_("The event socket is an alternative way for sending events "
                   "to the Event Console. It is used by the Check_MK logwatch check "
                   "when forwarding log messages to the Event Console. "
                   "This setting defines the number of unaccepted "
                   "connections to be queued before refusing new connections."),
            minvalue=1,
            label="max.",
            unit=_("pending connections"),
        )


@config_variable_registry.register
class ConfigVariableEventConsoleTranslateSNMPTraps(ConfigVariable):
    def group(self):
        return ConfigVariableGroupEventConsoleSNMP

    def domain(self):
        return ConfigDomainEventConsole

    def ident(self):
        return "translate_snmptraps"

    def valuespec(self):
        return Transform(
            CascadingDropdown(choices=[
                (False, _("Do not translate SNMP traps")),
                (True, _("Translate SNMP traps using the available MIBs"),
                 Dictionary(elements=[
                     ("add_description",
                      FixedValue(
                          True,
                          title=_("Add OID descriptions"),
                          totext=_("Append descriptions of OIDs to message texts"),
                      )),
                 ],)),
            ],),
            title=_("Translate SNMP traps"),
            help=_("When this option is enabled all available SNMP MIB files will be used "
                   "to translate the incoming SNMP traps. Information which can not be "
                   "translated, e.g. because a MIB is missing, are written untouched to "
                   "the event message."),
            forth=lambda v: v is True and (v, {}) or v,
        )


@config_variable_registry.register
class ConfigVariableEventConsoleSNMPCredentials(ConfigVariable):
    def group(self):
        return ConfigVariableGroupEventConsoleSNMP

    def domain(self):
        return ConfigDomainEventConsole

    def ident(self):
        return "snmp_credentials"

    def valuespec(self):
        return ListOf(
            Dictionary(
                elements=[
                    ("description", TextUnicode(title=_("Description"),)),
                    ("credentials", SNMPCredentials()),
                    ("engine_ids",
                     ListOfStrings(
                         valuespec=TextAscii(
                             size=24,
                             minlen=2,
                             allow_empty=False,
                             regex="^[A-Fa-f0-9]*$",
                             regex_error=_("The engine IDs have to be configured as hex strings "
                                           "like <tt>8000000001020304</tt>."),
                         ),
                         title=_("Engine IDs (only needed for SNMPv3)"),
                         help=_("Each SNMPv3 device has it's own engine ID. This is normally "
                                "automatically generated, but can also be configured manually "
                                "for some devices. As the engine ID is used for the encryption "
                                "of SNMPv3 traps sent by the devices, Check_MK needs to know "
                                "the engine ID to be able to decrypt the SNMP traps.<br>"
                                "The engine IDs have to be configured as hex strings like "
                                "<tt>8000000001020304</tt>."),
                         allow_empty=False,
                     )),
                ],
                # NOTE: For SNMPv3, this should not be empty, otherwise users will be confused...
                optional_keys=["engine_ids"],
            ),
            title=_("Credentials for processing SNMP traps"),
            help=_("When you want to process SNMP traps with the Event Console it is "
                   "necessary to configure the credentials to decrypt the incoming traps."),
            text_if_empty=_("SNMP traps not configured"),
        )


@config_variable_registry.register
class ConfigVariableEventConsoleDebugRules(ConfigVariable):
    def group(self):
        return ConfigVariableGroupEventConsoleLogging

    def domain(self):
        return ConfigDomainEventConsole

    def ident(self):
        return "debug_rules"

    def valuespec(self):
        return Checkbox(
            title=_("Debug rule execution"),
            label=_("enable extensive rule logging"),
            help=_("This option turns on logging the execution of rules. For each message received "
                   "the execution details of each rule are logged. This creates an immense "
                   "volume of logging and should never be used in productive operation."),
            default_value=False,
        )


@config_variable_registry.register
class ConfigVariableEventConsoleLogLevel(ConfigVariable):
    def group(self):
        return ConfigVariableGroupEventConsoleLogging

    def domain(self):
        return ConfigDomainEventConsole

    def ident(self):
        return "log_level"

    def valuespec(self):
        return Transform(
            Dictionary(
                title=_("Log level"),
                help=_(
                    "You can configure the Event Console to log more details about it's actions. "
                    "These information are logged into the file <tt>%s</tt>") %
                site_neutral_path(cmk.utils.paths.log_dir + "/mkeventd.log"),
                elements=self._ec_log_level_elements(),
                optional_keys=[],
            ),
            # Transform old values:
            # 0 -> normal logging
            # 1 -> verbose logging
            forth=lambda x: {"cmk.mkeventd": (logging.INFO if x == 0 else cmk.utils.log.VERBOSE)}
            if x in (0, 1) else x,
        )

    def _ec_log_level_elements(self):
        elements = []

        for component, title, help_txt in [
            ("cmk.mkeventd", _("General messages"),
             _("Log level for all log messages that are not in one of the categories below")),
            ("cmk.mkeventd.EventServer", _("Processing of incoming events"),
             _("Log level for the processing of all incoming events")),
            ("cmk.mkeventd.EventStatus", _("Event database"),
             _("Log level for managing already created events")),
            ("cmk.mkeventd.StatusServer", _("Status queries"),
             _("Log level for handling of incoming queries to the status socket")),
            ("cmk.mkeventd.lock", _("Locking"),
             _("Log level for the locking mechanics. Setting this to debug will enable "
               "log entries for each lock/unlock action.")),
            ("cmk.mkeventd.EventServer.snmp", _("SNMP trap processing"),
             _("Log level for the SNMP trap processing mechanics. Setting this to debug will enable "
               "detailed log entries for each received SNMP trap.")),
        ]:
            elements.append((component, LogLevelChoice(
                title=title,
                help=help_txt,
            )))
        return elements


@config_variable_registry.register
class ConfigVariableEventLogRuleHits(ConfigVariable):
    def group(self):
        return ConfigVariableGroupEventConsoleLogging

    def domain(self):
        return ConfigDomainEventConsole

    def ident(self):
        return "log_rulehits"

    def valuespec(self):
        return Checkbox(
            title=_("Log rule hits"),
            label=_("Log hits for rules in log of Event Console"),
            help=_(
                "If you enable this option then every time an event matches a rule "
                "(by normal hit, cancelling, counting or dropping) a log entry will be written "
                "into the log file of the Event Console. Please be aware that this might lead to "
                "a large number of log entries. "),
        )


# TODO: Isn't this variable deprecated since 1.5? Investigate and drop/mark as deprecated
@config_variable_registry.register
class ConfigVariableEventConsoleConnectTimeout(ConfigVariable):
    def group(self):
        return ConfigVariableGroupUserInterface

    def domain(self):
        return ConfigDomainGUI

    def ident(self):
        return "mkeventd_connect_timeout"

    def valuespec(self):
        return Integer(
            title=_("Connect timeout to status socket of Event Console"),
            help=_("When the Multisite GUI connects the socket of the event daemon "
                   "in order to retrieve information about current and historic events "
                   "then this timeout will be applied."),
            minvalue=1,
            maxvalue=120,
            unit="sec",
        )


@config_variable_registry.register
class ConfigVariableEventConsolePrettyPrintRules(ConfigVariable):
    def group(self):
        return ConfigVariableGroupWATO

    def domain(self):
        return ConfigDomainGUI

    def ident(self):
        return "mkeventd_pprint_rules"

    def valuespec(self):
        return Checkbox(
            title=_("Pretty-Print rules in config file of Event Console"),
            label=_("enable pretty-printing of rules"),
            help=_(
                "When the WATO module of the Event Console saves rules to the file "
                "<tt>mkeventd.d/wato/rules.mk</tt> it usually prints the Python "
                "representation of the rules-list into one single line by using the "
                "native Python code generator. Enabling this option switches to <tt>pprint</tt>, "
                "which nicely indents everything. While this is a bit slower for large "
                "rulesets it makes debugging and manual editing simpler."),
        )


@config_variable_registry.register
class ConfigVariableEventConsoleNotifyContactgroup(ConfigVariable):
    def group(self):
        return ConfigVariableGroupNotifications

    def domain(self):
        return ConfigDomainGUI

    def ident(self):
        return "mkeventd_notify_contactgroup"

    def valuespec(self):
        return ContactGroupSelection(
            title=_("Send notifications to Event Console"),
            no_selection=_("(don't send notifications to Event Console)"),
            label=_("send notifications of contactgroup:"),
            help=_(
                "If you select a contact group here, then all notifications of "
                "hosts and services in that contact group will be sent to the "
                "event console. <b>Note</b>: you still need to create a rule "
                "matching those messages in order to have events created. <b>Note (2)</b>: "
                "If you are using the Check_MK Micro Core then this setting is deprecated. "
                "Please use the notification plugin <i>Forward Notification to Event Console</i> instead."
            ),
        )

    def need_restart(self):
        return True


@config_variable_registry.register
class ConfigVariableEventConsoleNotifyRemoteHost(ConfigVariable):
    def group(self):
        return ConfigVariableGroupNotifications

    def domain(self):
        return ConfigDomainGUI

    def ident(self):
        return "mkeventd_notify_remotehost"

    def valuespec(self):
        return Optional(
            TextAscii(
                title=_("Host running Event Console"),
                attrencode=True,
            ),
            title=_("Send notifications to remote Event Console"),
            help=_("This will send the notification to a Check_MK Event Console on a remote host "
                   "by using syslog. <b>Note</b>: this setting will only be applied if no Event "
                   "Console is running locally in this site! That way you can use the same global "
                   "settings on your central and decentralized system and makes distributed WATO "
                   "easier. Please also make sure that <b>Send notifications to Event Console</b> "
                   "is enabled."),
            label=_("Send to remote Event Console via syslog"),
            none_label=_("Do not send to remote host"),
        )

    def need_restart(self):
        return True


@config_variable_registry.register
class ConfigVariableEventConsoleNotifyFacility(ConfigVariable):
    def group(self):
        return ConfigVariableGroupNotifications

    def domain(self):
        return ConfigDomainGUI

    def ident(self):
        return "mkeventd_notify_facility"

    def valuespec(self):
        return DropdownChoice(
            title=_("Syslog facility for Event Console notifications"),
            help=_("When sending notifications from the monitoring system to the event console "
                   "the following syslog facility will be set for these messages. Choosing "
                   "a unique facility makes creation of rules easier."),
            choices=cmk.gui.mkeventd.syslog_facilities,
        )

    def need_restart(self):
        return True


@rulespec_group_registry.register
class RulespecGroupEventConsole(RulespecGroup):
    @property
    def name(self):
        return "eventconsole"

    @property
    def title(self):
        return _("Event Console")

    @property
    def help(self):
        return _("Settings and Checks dealing with the Check_MK Event Console")


def convert_mkevents_hostspec(value):
    if isinstance(value, list):
        return value
    elif value == "$HOSTADDRESS$":
        return ["$HOSTADDRESS$"]
    elif value == "$HOSTNAME$":
        return ["$HOSTNAME$"]
    elif value == "$HOSTNAME$/$HOSTADDRESS$":
        return ["$HOSTNAME$", "$HOSTADDRESS$"]
    # custom
    return value


def _valuespec_extra_host_conf__ec_event_limit():
    return Transform(
        vs_ec_host_limit(title=_("Host event limit")),
        forth=lambda x: dict([("limit", int(x.split(":")[0])), ("action", x.split(":")[1])]),
        back=lambda x: "%d:%s" % (x["limit"], x["action"]),
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupEventConsole,
        name="extra_host_conf:_ec_event_limit",
        valuespec=_valuespec_extra_host_conf__ec_event_limit,
    ))


def _valuespec_active_checks_mkevents():
    return Dictionary(
        title=_("Check event state in Event Console"),
        help=_("This check is part of the Check_MK Event Console and will check "
               "if there are any open events for a certain host (and maybe a certain "
               "application on that host. The state of the check will reflect the status "
               "of the worst open event for that host."),
        elements=[
            ("hostspec",
             Transform(
                 Alternative(title=_("Host specification"),
                             elements=[
                                 ListChoice(title=_("Match the hosts with..."),
                                            choices=[
                                                ('$HOSTNAME$', _("Hostname")),
                                                ('$HOSTADDRESS$', _("IP address")),
                                                ('$HOSTALIAS$', _("Alias")),
                                            ]),
                                 TextAscii(allow_empty=False,
                                           attrencode=True,
                                           title="Specify host explicitely"),
                             ],
                             default_value=['$HOSTNAME$', '$HOSTADDRESS$']),
                 help=_(
                     "When quering the event status you can either use the monitoring "
                     "host name, the IP address, the host alias or a custom host name for referring to a "
                     "host. This is needed in cases where the event source (syslog, snmptrapd) "
                     "do not send a host name that matches the monitoring host name."),
                 forth=convert_mkevents_hostspec)),
            ("item",
             TextAscii(
                 title=_("Item (used in service description)"),
                 help=_("If you enter an item name here, this will be used as "
                        "part of the service description after the prefix \"Events \". "
                        "The prefix plus the configured item must result in an unique "
                        "service description per host. If you leave this empty either the "
                        "string provided in \"Application\" is used as item or the service "
                        "gets no item when the \"Application\" field is also not configured."),
                 allow_empty=False,
             )),
            ("application",
             RegExp(
                 title=_("Application (regular expression)"),
                 help=_("If you enter an application name here then only "
                        "events for that application name are counted. You enter "
                        "a regular expression here that must match a <b>part</b> "
                        "of the application name. Use anchors <tt>^</tt> and <tt>$</tt> "
                        "if you need a complete match."),
                 allow_empty=False,
                 mode=RegExp.infix,
                 case_sensitive=False,
             )),
            ("ignore_acknowledged",
             FixedValue(
                 True,
                 title=_("Ignore acknowledged events"),
                 help=_("If you check this box then only open events are honored when "
                        "determining the event state. Acknowledged events are displayed "
                        "(i.e. their count) but not taken into account."),
                 totext=_("acknowledged events will not be honored"),
             )),
            ("remote",
             Alternative(
                 title=_("Access to the Event Console"),
                 style="dropdown",
                 elements=[
                     FixedValue(
                         None,
                         title=_("Connect to the local Event Console"),
                         totext=_("local connect"),
                     ),
                     Tuple(
                         elements=[
                             TextAscii(
                                 title=_("Hostname/IP address of Event Console:"),
                                 allow_empty=False,
                                 attrencode=True,
                             ),
                             Integer(
                                 title=_("TCP Port number:"),
                                 minvalue=1,
                                 maxvalue=65535,
                                 default_value=6558,
                             ),
                         ],
                         title=_("Access via TCP"),
                         help=
                         _("In a distributed setup where the Event Console is not running in the same "
                           "site as the host is monitored you need to access the remote Event Console "
                           "via TCP. Please make sure that this is activated in the global settings of "
                           "the event console. The default port number is 6558."),
                     ),
                     TextAscii(
                         title=_("Access via UNIX socket"),
                         allow_empty=False,
                         size=64,
                         attrencode=True,
                     ),
                 ],
                 default_value=None,
             )),
        ],
        optional_keys=["application", "remote", "ignore_acknowledged", "item"],
        ignored_keys=["less_verbose"],  # is deprecated
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupEventConsole,
        match_type="all",
        name="active_checks:mkevents",
        valuespec=_valuespec_active_checks_mkevents,
    ))


def _sl_help():
    return (_("A service level is a number that describes the business impact of a host or "
              "service. This level can be used in rules for notifications, as a filter in "
              "views or as a criteria in rules for the Event Console. A higher service level "
              "is assumed to be more business critical. This ruleset allows to assign service "
              "levels to hosts and/or services. Note: if you assign a service level to "
              "a host with the ruleset <i>Service Level of hosts</i>, then this level is "
              "inherited to all services that do <b>not</b> have explicitely assigned a service "
              "with the ruleset <i>Service Level of services</i>. Assigning no service level "
              "is equal to defining a level of 0.<br><br>The list of available service "
              "levels is configured via a <a href='%s'>global option.</a>") %
            "wato.py?varname=mkeventd_service_levels&mode=edit_configvar")


def _valuespec_extra_host_conf__ec_sl():
    return DropdownChoice(
        title=_("Service Level of hosts"),
        help=_sl_help(),
        choices=cmk.gui.mkeventd.service_levels,
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupGrouping,
        name="extra_host_conf:_ec_sl",
        valuespec=_valuespec_extra_host_conf__ec_sl,
    ))


def _valuespec_extra_service_conf__ec_sl():
    return DropdownChoice(
        title=_("Service Level of services"),
        help=_sl_help() + _(" Note: if no service level is configured for a service "
                            "then that of the host will be used instead (if configured)."),
        choices=cmk.gui.mkeventd.service_levels,
    )


rulespec_registry.register(
    ServiceRulespec(
        group=RulespecGroupGrouping,
        item_type="service",
        name="extra_service_conf:_ec_sl",
        valuespec=_valuespec_extra_service_conf__ec_sl,
    ))


def _vs_contact(title):
    return TextUnicode(
        title=title,
        help=_("This rule set is useful if you send your monitoring notifications "
               "into the Event Console. The contact information that is set by this rule "
               "will be put into the resulting event in the Event Console. "
               "This does not transport contact objects or contact groups, but is a free "
               "comment field.") + _(" Note: if no contact information is configured for a service "
                                     "then that of the host will be used instead (if configured)."),
        size=80,
        regex=r"^[^;'$|]*$",
        regex_error=_("The contact information must not contain one of the characters "
                      "<tt>;</tt> <tt>'</tt> <tt>|</tt> or <tt>$</tt>"),
    )


def _valuespec_extra_host_conf__ec_contact():
    return _vs_contact(_("Host contact information"))


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupEventConsole,
        name="extra_host_conf:_ec_contact",
        valuespec=_valuespec_extra_host_conf__ec_contact,
    ))


def _valuespec_extra_service_conf__ec_contact():
    return _vs_contact(title=_("Service contact information"))


rulespec_registry.register(
    ServiceRulespec(
        group=RulespecGroupEventConsole,
        item_type="service",
        name="extra_service_conf:_ec_contact",
        valuespec=_valuespec_extra_service_conf__ec_contact,
    ))


#.
#   .--Notifications-------------------------------------------------------.
#   |       _   _       _   _  __ _           _   _                        |
#   |      | \ | | ___ | |_(_)/ _(_) ___ __ _| |_(_) ___  _ __  ___        |
#   |      |  \| |/ _ \| __| | |_| |/ __/ _` | __| |/ _ \| '_ \/ __|       |
#   |      | |\  | (_) | |_| |  _| | (_| (_| | |_| | (_) | | | \__ \       |
#   |      |_| \_|\___/ \__|_|_| |_|\___\__,_|\__|_|\___/|_| |_|___/       |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   | Stuff for sending monitoring notifications into the event console.   |
#   '----------------------------------------------------------------------'
def mkeventd_update_notifiation_configuration(hosts):
    contactgroup = config.mkeventd_notify_contactgroup
    remote_console = config.mkeventd_notify_remotehost

    if not remote_console:
        remote_console = ""

    path = cmk.utils.paths.nagios_conf_dir + "/mkeventd_notifications.cfg"
    if not contactgroup and os.path.exists(path):
        os.remove(path)
    elif contactgroup:
        store.save_text_to_file(
            path, u"""# Created by Check_MK Event Console
# This configuration will send notifications about hosts and
# services in the contact group '%(group)s' to the Event Console.

define contact {
    contact_name                   mkeventd
    alias                          "Notifications for Check_MK Event Console"
    contactgroups                  %(group)s
    host_notification_commands     mkeventd-notify-host
    service_notification_commands  mkeventd-notify-service
    host_notification_options      d,u,r
    service_notification_options   c,w,u,r
    host_notification_period       24X7
    service_notification_period    24X7
    email                          none
}

define command {
    command_name                   mkeventd-notify-host
    command_line                   mkevent -n %(facility)s '%(remote)s' $HOSTSTATEID$ '$HOSTNAME$' '' '$HOSTOUTPUT$' '$_HOSTEC_SL$' '$_HOSTEC_CONTACT$'
}

define command {
    command_name                   mkeventd-notify-service
    command_line                   mkevent -n %(facility)s '%(remote)s' $SERVICESTATEID$ '$HOSTNAME$' '$SERVICEDESC$' '$SERVICEOUTPUT$' '$_SERVICEEC_SL$' '$_SERVICEEC_CONTACT$' '$_HOSTEC_SL$' '$_HOSTEC_CONTACT$'
}
""" % {
                "group": contactgroup,
                "facility": config.mkeventd_notify_facility,
                "remote": remote_console
            })


hooks.register_builtin("pre-activate-changes", mkeventd_update_notifiation_configuration)
