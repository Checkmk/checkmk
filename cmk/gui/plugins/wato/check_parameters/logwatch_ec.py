#!/usr/bin/python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2014             mk@mathias-kettner.de |
# +------------------------------------------------------------------+
#
# This file is part of Check_MK.
# The official homepage is at http://mathias-kettner.de/check_mk.
#
# check_mk is free software;  you can redistribute it and/or modify it
# under the  terms of the  GNU General Public License  as published by
# the Free Software Foundation in version 2.  check_mk is  distributed
# in the hope that it will be useful, but WITHOUT ANY WARRANTY;  with-
# out even the implied warranty of  MERCHANTABILITY  or  FITNESS FOR A
# PARTICULAR PURPOSE. See the  GNU General Public License for more de-
# tails. You should have  received  a copy of the  GNU  General Public
# License along with GNU Make; see the file  COPYING.  If  not,  write
# to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
# Boston, MA 02110-1301 USA.

import cmk.gui.mkeventd as mkeventd
from cmk.gui.i18n import _
from cmk.gui.valuespec import (
    Age,
    Alternative,
    CascadingDropdown,
    Checkbox,
    Dictionary,
    DropdownChoice,
    Filesize,
    FixedValue,
    Integer,
    ListOfStrings,
    TextAscii,
    Transform,
)
from cmk.gui.plugins.wato import (
    RulespecGroupCheckParametersApplications,
    register_check_parameters,
)


register_check_parameters(RulespecGroupCheckParametersApplications,
    "logwatch_ec",
    _('Logwatch Event Console Forwarding'),
    Alternative(
        title = _("Forwarding"),
        help = _("Instead of using the regular logwatch check all lines received by logwatch can "
                 "be forwarded to a Check_MK event console daemon to be processed. The target event "
                 "console can be configured for each host in a separate rule."),
        style = "dropdown",
        elements = [
            FixedValue(
                "",
                totext = _("Messages are handled by logwatch."),
                title = _("No forwarding"),
            ),
            Dictionary(
                title = _('Forward Messages to Event Console'),
                elements = [
                    ('method', Transform(
                        # TODO: Clean this up to some CascadingDropdown()
                        Alternative(
                            style = "dropdown",
                            title = _("Forwarding Method"),
                            elements = [
                                FixedValue(
                                    "",
                                    title = _("Local: Send events to local Event Console in same OMD site"),
                                    totext = _("Directly forward to Event Console"),
                                ),
                                TextAscii(
                                    title = _("Local: Send events to local Event Console into unix socket"),
                                    allow_empty = False,
                                ),
                                FixedValue(
                                    "spool:",
                                    title = _("Local: Spooling - Send events to local event console in same OMD site"),
                                    totext = _("Spool to Event Console"),
                                ),
                                Transform(
                                    TextAscii(),
                                    title = _("Local: Spooling - Send events to local Event Console into given spool directory"),
                                    allow_empty = False,
                                    forth = lambda x: x[6:],
        # remove prefix
                                    back  = lambda x: "spool:" + x, # add prefix
                                ),
                                CascadingDropdown(
                                    title = _("Remote: Send events to remote syslog host"),
                                    choices = [
                                        ("tcp", _("Send via TCP"), Dictionary(
                                            elements = [
                                                ("address", TextAscii(
                                                    title = _("Address"),
                                                    allow_empty = False,
                                                )),
                                                ("port", Integer(
                                                    title = _("Port"),
                                                    allow_empty = False,
                                                    default_value = 514,
                                                    minvalue = 1,
                                                    maxvalue = 65535,
                                                    size = 6,
                                                )),
                                                ("spool", Dictionary(
                                                    title = _("Spool messages that could not be sent"),
                                                    help = _("Messages that can not be forwarded, e.g. when the target Event Console is "
                                                             "not running, can temporarily be stored locally. Forwarding is tried again "
                                                             "on next execution. When messages are spooled, the check will go into WARNING "
                                                             "state. In case messages are dropped by the rules below, the check will shortly "
                                                             "go into CRITICAL state for this execution."),
                                                    elements = [
                                                        ("max_age", Age(
                                                            title = _("Maximum spool duration"),
                                                            help = _("Messages that are spooled longer than this time will be thrown away."),
                                                            default_value = 60*60*24*7, # 1 week should be fine (if size is not exceeded)
                                                        )),
                                                        ("max_size", Filesize(
                                                            title = _("Maximum spool size"),
                                                            help = _("When the total size of spooled messages exceeds this number, the oldest "
                                                                     "messages of the currently spooled messages is thrown away until the left "
                                                                     "messages have the half of the maximum size."),
                                                            default_value = 500000, # do not save more than 500k of message
                                                        )),
                                                    ],
                                                    optional_keys = [],
                                                )),
                                            ],
                                            optional_keys = [ "spool" ],
                                        )),
                                        ("udp", _("Send via UDP"), Dictionary(
                                            elements = [
                                                ("address", TextAscii(
                                                    title = _("Address"),
                                                    allow_empty = False,
                                                )),
                                                ("port", Integer(
                                                    title = _("Port"),
                                                    allow_empty = False,
                                                    default_value = 514,
                                                    minvalue = 1,
                                                    maxvalue = 65535,
                                                    size = 6,
                                                )),
                                            ],
                                            optional_keys = [],
                                        )),
                                    ],
                                ),
                            ],
                            match = lambda x: 4 if isinstance(x, tuple) else (0 if not x else (2 if x == 'spool:' else (3 if x.startswith('spool:') else 1)))
                        ),
                        # migrate old (tcp, address, port) tuple to new dict
                        forth = lambda v: (v[0], {"address": v[1], "port": v[2]}) if (isinstance(v, tuple) and not isinstance(v[1], dict)) else v,
                    )),
                    ('facility', DropdownChoice(
                        title = _("Syslog facility for forwarded messages"),
                        help = _("When forwarding messages and no facility can be extracted from the "
                                 "message this facility is used."),
                        choices = mkeventd.syslog_facilities,
                        default_value = 17, # local1
                    )),
                    ('restrict_logfiles',
                        ListOfStrings(
                            title = _('Restrict Logfiles (Prefix matching regular expressions)'),
                            help  = _("Put the item names of the logfiles here. For example \"System$\" "
                                      "to select the service \"LOG System\". You can use regular expressions "
                                      "which must match the beginning of the logfile name."),
                        ),
                    ),
                    ('monitor_logfilelist',
                        Checkbox(
                            title =  _("Monitoring of forwarded logfiles"),
                            label = _("Warn if list of forwarded logfiles changes"),
                            help = _("If this option is enabled, the check monitors the list of forwarded "
                                  "logfiles and will warn you if at any time a logfile is missing or exceeding "
                                  "when compared to the initial list that was snapshotted during service detection. "
                                  "Reinventorize this check in order to make it OK again."),
                     )
                    ),
                    ('expected_logfiles',
                        ListOfStrings(
                            title = _("List of expected logfiles"),
                            help = _("When the monitoring of forwarded logfiles is enabled, the check verifies that "
                                     "all of the logfiles listed here are reported by the monitored system."),
                        )
                    ),
                    ('logwatch_reclassify',
                        Checkbox(
                            title =  _("Reclassify messages before forwarding them to the EC"),
                            label = _("Apply logwatch patterns"),
                            help = _("If this option is enabled, the logwatch lines are first reclassified by the logwatch "
                                     "patterns before they are sent to the event console. If you reclassify specific lines to "
                                     "IGNORE they are not forwarded to the event console. This takes the burden from the "
                                     "event console to process the message itself through all of its rulesets. The reclassifcation "
                                     "of each line takes into account from which logfile the message originates. So you can create "
                                     "logwatch reclassification rules specifically designed for a logfile <i>access.log</i>, "
                                     "which do not apply to other logfiles."),
                     )
                    ),
                    ('separate_checks',
                        Checkbox(
                            title =  _("Create a separate check for each logfile"),
                            label = _("Separate check"),
                            help = _("If this option is enabled, there will be one separate check for each logfile found during "
                                     "the service discovery. This option also changes the behaviour for unknown logfiles. "
                                     "The default logwatch check forwards all logfiles to the event console, even logfiles "
                                     "which were not known during the service discovery. Creating one check per logfile changes "
                                     "this behaviour so that any data from unknown logfiles is discarded."),
                     )
                    )
                ],
                optional_keys = ['restrict_logfiles', 'expected_logfiles', 'logwatch_reclassify', 'separate_checks'],
            ),
        ],
        default_value = '',
    ),
    None,
    'first',
                         )# wmic_process does not support inventory at the moment
