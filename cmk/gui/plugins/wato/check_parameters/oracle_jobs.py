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


@rulespec_registry.register
class RulespecCheckgroupParametersOracleJobs(CheckParameterRulespecWithItem):
    @property
    def group(self):
        return RulespecGroupCheckParametersApplications

    @property
    def check_group_name(self):
        return "oracle_jobs"

    @property
    def title(self):
        return _("Oracle Scheduler Job")

    @property
    def match_type(self):
        return "dict"

    @property
    def parameter_valuespec(self):
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
                     title="Status of service in case of disabled job", default_value=0)),
                ("status_missing_jobs",
                 MonitoringState(
                     title=_("Status of service in case of missing job."),
                     default_value=2,
                 )),
            ],
        )

    @property
    def item_spec(self):
        return TextAscii(
            title=_("Scheduler Job Name"),
            help=_("Here you can set explicit Scheduler-Jobs by defining them via SID, Job-Owner "
                   "and Job-Name, separated by a dot, for example <tt>TUX12C.SYS.PURGE_LOG</tt>"),
            regex=r'.+\..+',
            allow_empty=False)
