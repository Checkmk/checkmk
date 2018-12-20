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
    Age,
    Alternative,
    Dictionary,
    DropdownChoice,
    Filesize,
    FixedValue,
    Integer,
    Percentage,
    RegExp,
    TextAscii,
    Transform,
    Tuple,
)
from cmk.gui.plugins.wato import (
    RulespecGroupCheckParametersApplications,
    register_check_parameters,
    UserIconOrAction,
)

process_level_elements = [
    ('levels',
     Tuple(
         title=_('Levels for process count'),
         help=
         _("Please note that if you specify and also if you modify levels here, the change is activated "
           "only during an inventory.  Saving this rule is not enough. This is due to the nature of inventory rules."
          ),
         elements=[
             Integer(
                 title=_("Critical below"),
                 unit=_("processes"),
                 default_value=1,
             ),
             Integer(
                 title=_("Warning below"),
                 unit=_("processes"),
                 default_value=1,
             ),
             Integer(
                 title=_("Warning above"),
                 unit=_("processes"),
                 default_value=99999,
             ),
             Integer(
                 title=_("Critical above"),
                 unit=_("processes"),
                 default_value=99999,
             ),
         ],
     )),
    ("cpulevels",
     Tuple(
         title=_("Levels on total CPU utilization"),
         help=_("By activating this options you can set levels on the total "
                "CPU utilization of all included processes."),
         elements=[
             Percentage(title=_("Warning at"), default_value=90, maxvalue=10000),
             Percentage(title=_("Critical at"), default_value=98, maxvalue=10000),
         ],
     )),
    ("cpu_average",
     Integer(
         title=_("CPU Averaging"),
         help=_("By activating averaging, Check_MK will compute the average of "
                "the total CPU utilization over a given interval. If you have defined "
                "alerting levels then these will automatically be applied on the "
                "averaged value. This helps to mask out short peaks. "),
         unit=_("minutes"),
         minvalue=1,
         default_value=15,
     )),
    ("single_cpulevels",
     Tuple(
         title=_("Levels on CPU utilization of a single process"),
         help=_("Here you can define levels on the CPU utilization of single "
                "processes. For performance reasons CPU Averaging will not be "
                "applied to to the levels of single processes."),
         elements=[
             Percentage(title=_("Warning at"), default_value=90, maxvalue=10000),
             Percentage(title=_("Critical at"), default_value=98, maxvalue=10000),
         ],
     )),
    ("max_age",
     Tuple(
         title=_("Maximum allowed age"),
         help=_("Alarms you if the age of the process (not the consumed CPU "
                "time, but the real time) exceed the configured levels."),
         elements=[
             Age(title=_("Warning at"), default_value=3600),
             Age(title=_("Critical at"), default_value=7200),
         ])),
    ("virtual_levels",
     Tuple(
         title=_("Virtual memory usage"),
         elements=[
             Filesize(title=_("Warning at"), default_value=1000 * 1024 * 1024 * 1024),
             Filesize(title=_("Critical at"), default_value=2000 * 1024 * 1024 * 1024),
         ],
     )),
    ("resident_levels",
     Tuple(
         title=_("Physical memory usage"),
         elements=[
             Filesize(title=_("Warning at"), default_value=100 * 1024 * 1024),
             Filesize(title=_("Critical at"), default_value=200 * 1024 * 1024),
         ],
     )),
    ("resident_levels_perc",
     Tuple(
         title=_("Physical memory usage, in percentage of total RAM"),
         elements=[
             Percentage(title=_("Warning at"), default_value=25.0),
             Percentage(title=_("Critical at"), default_value=50.0),
         ])),
    ("handle_count",
     Tuple(
         title=_('Handle Count (Windows only)'),
         help=_(
             "The number of object handles in the processes object table. This includes open handles to "
             "threads, files and other resources like registry keys."),
         elements=[
             Integer(
                 title=_("Warning above"),
                 unit=_("handles"),
             ),
             Integer(
                 title=_("Critical above"),
                 unit=_("handles"),
             ),
         ],
     )),
    ('process_info',
     DropdownChoice(
         title=_("Enable per-process details in long-output"),
         label=_("Enable per-process details"),
         help=
         _("If active, the long output of this service will contain a list of "
           "all the matching processes and their details (i.e. PID, CPU usage, memory usage). "
           "Please note that HTML output will only work if \"Escape HTML codes in plugin output\" is "
           "disabled in global settings. This might expose you to Cross-Site-Scripting (everyone "
           "with write-access to checks could get scripts executed on the monitoring site in the context "
           "of the user of the monitoring site) so please do this if you understand the consequences."
          ),
         choices=[
             (None, _("Disable")),
             ("text", _("Text output")),
             ("html", _("HTML output")),
         ],
         default_value="disable",
     )),
]


# Add checks that have parameters but are only configured as manual checks
def ps_convert_from_tuple(params):
    if isinstance(params, (list, tuple)):
        if len(params) == 5:
            procname, warnmin, okmin, okmax, warnmax = params
            user = None
        elif len(params) == 6:
            procname, user, warnmin, okmin, okmax, warnmax = params
        params = {
            "process": procname,
            "warnmin": warnmin,
            "okmin": okmin,
            "okmax": okmax,
            "warnmax": warnmax,
        }
        if user is not None:
            params["user"] = user
    return params


# Next step in conversion: introduce "levels"
def ps_convert_from_singlekeys(old_params):
    params = {}
    params.update(ps_convert_from_tuple(old_params))
    if "warnmin" in params:
        params["levels"] = (
            params.pop("warnmin", 1),
            params.pop("okmin", 1),
            params.pop("warnmax", 99999),
            params.pop("okmax", 99999),
        )
    return params


def ps_convert_inventorized_from_singlekeys(old_params):
    params = ps_convert_from_singlekeys(old_params)
    if 'user' in params:
        del params['user']
    if 'process' in params:
        del params['process']
    return params


# Rule for disovered process checks
register_check_parameters(
    RulespecGroupCheckParametersApplications,
    "ps",
    _("State and count of processes"),
    Transform(
        Dictionary(elements=process_level_elements + [(
            'icon',
            UserIconOrAction(
                title=_("Add custom icon or action"),
                help=_("You can assign icons or actions to the found services in the status GUI."),
            ))]),
        forth=ps_convert_inventorized_from_singlekeys,
    ),
    TextAscii(title=_("Process name as defined at discovery"),),
    "dict",
    has_inventory=True,
    register_static_check=False,
)

# Rule for static process checks
register_check_parameters(
    RulespecGroupCheckParametersApplications,
    "ps",
    _("State and count of processes"),
    Transform(
        Dictionary(
            elements=[
                (
                    "process",
                    Alternative(
                        title=_("Process Matching"),
                        style="dropdown",
                        elements=[
                            TextAscii(
                                title=_("Exact name of the process without argments"),
                                size=50,
                            ),
                            Transform(
                                RegExp(
                                    size=50,
                                    mode=RegExp.prefix,
                                ),
                                title=_("Regular expression matching command line"),
                                help=_("This regex must match the <i>beginning</i> of the complete "
                                       "command line of the process including arguments"),
                                forth=lambda x: x[1:],  # remove ~
                                back=lambda x: "~" + x,  # prefix ~
                            ),
                            FixedValue(
                                None,
                                totext="",
                                title=_("Match all processes"),
                            )
                        ],
                        match=lambda x: (not x and 2) or (x[0] == '~' and 1 or 0))),
                (
                    "user",
                    Alternative(
                        title=_("Name of operating system user"),
                        style="dropdown",
                        elements=[
                            TextAscii(title=_("Exact name of the operating system user")),
                            Transform(
                                RegExp(
                                    size=50,
                                    mode=RegExp.prefix,
                                ),
                                title=_("Regular expression matching username"),
                                help=_("This regex must match the <i>beginning</i> of the complete "
                                       "username"),
                                forth=lambda x: x[1:],  # remove ~
                                back=lambda x: "~" + x,  # prefix ~
                            ),
                            FixedValue(
                                None,
                                totext="",
                                title=_("Match all users"),
                            )
                        ],
                        match=lambda x: (not x and 2) or (x[0] == '~' and 1 or 0))),
                ('icon',
                 UserIconOrAction(
                     title=_("Add custom icon or action"),
                     help=_(
                         "You can assign icons or actions to the found services in the status GUI."
                     ),
                 )),
            ] + process_level_elements,
            # required_keys = [ "process" ],
        ),
        forth=ps_convert_from_singlekeys,
    ),
    TextAscii(
        title=_("Process Name"),
        help=_("This name will be used in the description of the service"),
        allow_empty=False,
        regex="^[a-zA-Z_0-9 _./-]*$",
        regex_error=_("Please use only a-z, A-Z, 0-9, space, underscore, "
                      "dot, hyphen and slash for your service description"),
    ),
    "dict",
    has_inventory=False,
)
