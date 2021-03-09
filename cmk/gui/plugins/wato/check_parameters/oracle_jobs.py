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
    Dictionary,
    DropdownChoice,
    MonitoringState,
    TextAscii,
    Tuple,
)

from cmk.gui.plugins.wato import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersApplications,
)


def _item_spec_oracle_jobs():
    return TextAscii(
        title=_("Scheduler Job Name"),
        help=_("Here you can set explicit Scheduler-Jobs by defining them via SID, Job-Owner "
               "and Job-Name, separated by a dot, for example <tt>TUX12C.SYS.PURGE_LOG</tt>"),
        regex=r'.+\..+',
        allow_empty=False)


def _parameter_valuespec_oracle_jobs():
    return Dictionary(
        help=_("A scheduler job is an object in an ORACLE database which could be "
               "compared to a cron job on Unix. "),
        elements=[
            ("run_duration",
             Tuple(
                 title=_("Maximum run duration for last execution"),
                 help=_("Here you can define an upper limit for the run duration of "
                        "last execution of the job."),
                 elements=[
                     Age(title=_("warning at")),
                     Age(title=_("critical at")),
                 ],
             )),
            ("disabled",
             DropdownChoice(
                 title=_("Job State"),
                 help=_("The state of the job is ignored per default."),
                 totext="",
                 choices=[
                     (True, _("Ignore the state of the Job")),
                     (False, _("Consider the state of the job")),
                 ],
             )),
            ("status_disabled_jobs",
             MonitoringState(
                 title=_("Status of service in case of disabled job"),
                 default_value=0,
             )),
            ("status_missing_jobs",
             MonitoringState(
                 title=_("Status of service in case of missing job"),
                 default_value=2,
             )),
            ("missinglog",
             MonitoringState(
                 default_value=1,
                 title=_("State in case of Job has no log information"),
                 help=_("It is possible that a job has no log informations. This also means "
                        "that the job has no last running state as this is obtained from the log. "
                        "The last run state is ignored when no log information is found."),
             )),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="oracle_jobs",
        group=RulespecGroupCheckParametersApplications,
        item_spec=_item_spec_oracle_jobs,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_oracle_jobs,
        title=lambda: _("Oracle Scheduler Job"),
    ))
