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

from cmk.gui.i18n import _
from cmk.gui.valuespec import (
    Alternative,
    CascadingDropdown,
    defines,
    Dictionary,
    DropdownChoice,
    Integer,
    ListChoice,
    ListOf,
    MonitoringState,
    Optional,
    OptionalDropdownChoice,
    Percentage,
    RadioChoice,
    TextAscii,
    Transform,
    Tuple,
)
from cmk.gui.plugins.wato import (
    PredictiveLevels,
    RulespecGroupCheckParametersNetworking,
    register_check_parameters,
)


def vs_interface_traffic():
    def vs_abs_perc():
        return CascadingDropdown(
            orientation="horizontal",
            choices=[("perc", _("Percentual levels (in relation to port speed)"),
                      Tuple(
                          orientation="float",
                          show_titles=False,
                          elements=[
                              Percentage(label=_("Warning at")),
                              Percentage(label=_("Critical at")),
                          ])),
                     ("abs", _("Absolute levels in bits or bytes per second"),
                      Tuple(
                          orientation="float",
                          show_titles=False,
                          elements=[
                              Integer(label=_("Warning at")),
                              Integer(label=_("Critical at")),
                          ])), ("predictive", _("Predictive Levels"), PredictiveLevels())])

    return CascadingDropdown(
        orientation="horizontal",
        choices=[
            ("upper", _("Upper"), vs_abs_perc()),
            ("lower", _("Lower"), vs_abs_perc()),
        ])


def transform_if(v):
    new_traffic = []

    if 'traffic' in v and not isinstance(v['traffic'], list):
        warn, crit = v['traffic']
        if isinstance(warn, int):
            new_traffic.append(('both', ('upper', ('abs', (warn, crit)))))
        elif isinstance(warn, float):
            new_traffic.append(('both', ('upper', ('perc', (warn, crit)))))

    if 'traffic_minimum' in v:
        warn, crit = v['traffic_minimum']
        if isinstance(warn, int):
            new_traffic.append(('both', ('lower', ('abs', (warn, crit)))))
        elif isinstance(warn, float):
            new_traffic.append(('both', ('lower', ('perc', (warn, crit)))))
        del v['traffic_minimum']

    if new_traffic:
        v['traffic'] = new_traffic

    return v


register_check_parameters(
    RulespecGroupCheckParametersNetworking,
    "if",
    _("Network interfaces and switch ports"),
    # Transform old traffic related levels which used "traffic" and "traffic_minimum"
    # keys where each was configured with an Alternative valuespec
    Transform(
        Dictionary(
            ignored_keys=["aggregate"],  # Created by discovery when using interface grouping
            elements=[
                ("errors",
                 Alternative(
                     title=_("Levels for error rates"),
                     help=
                     _("These levels make the check go warning or critical whenever the "
                       "<b>percentual error rate</b> or the <b>absolute error rate</b> of the monitored interface reaches "
                       "the given bounds. The percentual error rate is computed by dividing number of "
                       "errors by the total number of packets (successful plus errors)."),
                     elements=[
                         Tuple(
                             title=_("Percentual levels for error rates"),
                             elements=[
                                 Percentage(
                                     title=_("Warning at"),
                                     unit=_("percent errors"),
                                     default_value=0.01,
                                     display_format='%.3f'),
                                 Percentage(
                                     title=_("Critical at"),
                                     unit=_("percent errors"),
                                     default_value=0.1,
                                     display_format='%.3f')
                             ]),
                         Tuple(
                             title=_("Absolute levels for error rates"),
                             elements=[
                                 Integer(title=_("Warning at"), unit=_("errors")),
                                 Integer(title=_("Critical at"), unit=_("errors"))
                             ])
                     ])),
                ("speed",
                 OptionalDropdownChoice(
                     title=_("Operating speed"),
                     help=_("If you use this parameter then the check goes warning if the "
                            "interface is not operating at the expected speed (e.g. it "
                            "is working with 100Mbit/s instead of 1Gbit/s.<b>Note:</b> "
                            "some interfaces do not provide speed information. In such cases "
                            "this setting is used as the assumed speed when it comes to "
                            "traffic monitoring (see below)."),
                     choices=[
                         (None, _("ignore speed")),
                         (10000000, "10 Mbit/s"),
                         (100000000, "100 Mbit/s"),
                         (1000000000, "1 Gbit/s"),
                         (10000000000, "10 Gbit/s"),
                     ],
                     otherlabel=_("specify manually ->"),
                     explicit=Integer(
                         title=_("Other speed in bits per second"), label=_("Bits per second")))),
                ("state",
                 Optional(
                     ListChoice(
                         title=_("Allowed states:"), choices=defines.interface_oper_states()),
                     title=_("Operational state"),
                     help=
                     _("If you activate the monitoring of the operational state (<tt>ifOperStatus</tt>) "
                       "the check will get warning or critical if the current state "
                       "of the interface does not match one of the expected states. Note: the status 9 (<i>admin down</i>) "
                       "is only visible if you activate this status during switch port inventory or if you manually "
                       "use the check plugin <tt>if64adm</tt> instead of <tt>if64</tt>."),
                     label=_("Ignore the operational state"),
                     none_label=_("ignore"),
                     negate=True)),
                ("map_operstates",
                 ListOf(
                     Tuple(
                         orientation="horizontal",
                         elements=[
                             DropdownChoice(choices=defines.interface_oper_states()),
                             MonitoringState()
                         ]),
                     title=_('Map operational states'),
                 )),
                ("assumed_speed_in",
                 OptionalDropdownChoice(
                     title=_("Assumed input speed"),
                     help=_(
                         "If the automatic detection of the link speed does not work "
                         "or the switch's capabilities are throttled because of the network setup "
                         "you can set the assumed speed here."),
                     choices=[
                         (None, _("ignore speed")),
                         (10000000, "10 Mbit/s"),
                         (100000000, "100 Mbit/s"),
                         (1000000000, "1 Gbit/s"),
                         (10000000000, "10 Gbit/s"),
                     ],
                     otherlabel=_("specify manually ->"),
                     default_value=16000000,
                     explicit=Integer(
                         title=_("Other speed in bits per second"),
                         label=_("Bits per second"),
                         size=10))),
                ("assumed_speed_out",
                 OptionalDropdownChoice(
                     title=_("Assumed output speed"),
                     help=_(
                         "If the automatic detection of the link speed does not work "
                         "or the switch's capabilities are throttled because of the network setup "
                         "you can set the assumed speed here."),
                     choices=[
                         (None, _("ignore speed")),
                         (10000000, "10 Mbit/s"),
                         (100000000, "100 Mbit/s"),
                         (1000000000, "1 Gbit/s"),
                         (10000000000, "10 Gbit/s"),
                     ],
                     otherlabel=_("specify manually ->"),
                     default_value=1500000,
                     explicit=Integer(
                         title=_("Other speed in bits per second"),
                         label=_("Bits per second"),
                         size=12))),
                ("unit",
                 RadioChoice(
                     title=_("Measurement unit"),
                     help=_("Here you can specifiy the measurement unit of the network interface"),
                     default_value="byte",
                     choices=[
                         ("bit", _("Bits")),
                         ("byte", _("Bytes")),
                     ],
                 )),
                ("infotext_format",
                 DropdownChoice(
                     title=_("Change infotext in check output"),
                     help=
                     _("This setting allows you to modify the information text which is displayed between "
                       "the two brackets in the check output. Please note that this setting does not work for "
                       "grouped interfaces, since the additional information of grouped interfaces is different"
                      ),
                     choices=[
                         ("alias", _("Show alias")),
                         ("description", _("Show description")),
                         ("alias_and_description", _("Show alias and description")),
                         ("alias_or_description", _("Show alias if set, else description")),
                         ("desription_or_alias", _("Show description if set, else alias")),
                         ("hide", _("Hide infotext")),
                     ])),
                ("traffic",
                 ListOf(
                     CascadingDropdown(
                         title=_("Direction"),
                         orientation="horizontal",
                         choices=[
                             ('both', _("In / Out"), vs_interface_traffic()),
                             ('in', _("In"), vs_interface_traffic()),
                             ('out', _("Out"), vs_interface_traffic()),
                         ]),
                     title=_("Used bandwidth (minimum or maximum traffic)"),
                     help=_("Setting levels on the used bandwidth is optional. If you do set "
                            "levels you might also consider using averaging."),
                 )),
                (
                    "nucasts",
                    Tuple(
                        title=_("Non-unicast packet rates"),
                        help=_(
                            "Setting levels on non-unicast packet rates is optional. This may help "
                            "to detect broadcast storms and other unwanted traffic."),
                        elements=[
                            Integer(title=_("Warning at"), unit=_("pkts / sec")),
                            Integer(title=_("Critical at"), unit=_("pkts / sec")),
                        ]),
                ),
                ("discards",
                 Tuple(
                     title=_("Absolute levels for discards rates"),
                     elements=[
                         Integer(title=_("Warning at"), unit=_("discards")),
                         Integer(title=_("Critical at"), unit=_("discards"))
                     ])),
                ("average",
                 Integer(
                     title=_("Average values"),
                     help=_("By activating the computation of averages, the levels on "
                            "errors and traffic are applied to the averaged value. That "
                            "way you can make the check react only on long-time changes, "
                            "not on one-minute events."),
                     unit=_("minutes"),
                     minvalue=1,
                     default_value=15,
                 )),
            ]),
        forth=transform_if,
    ),
    TextAscii(title=_("port specification"), allow_empty=False),
    "dict",
)
