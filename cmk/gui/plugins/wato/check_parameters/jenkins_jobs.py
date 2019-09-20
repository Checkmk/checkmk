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
    Integer,
    MonitoringState,
    TextAscii,
    Tuple,
)

from cmk.gui.plugins.wato import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersApplications,
)


def _parameter_valuespec_jenkins_jobs():
    return Dictionary(elements=[
        ("jenkins_job_score",
         Tuple(
             title=_("Job score"),
             elements=[
                 Integer(title=_("Warning below"), unit="%"),
                 Integer(title=_("Critical below"), unit="%"),
             ],
         )),
        ("jenkins_time_since",
         Tuple(
             title=_("Time since last successful build"),
             elements=[
                 Age(title=_("Warning if older than")),
                 Age(title=_("Critical if older than")),
             ],
         )),
        ('jenkins_build_duration',
         Tuple(
             title=_("Duration of last build"),
             elements=[
                 Age(title=_("Warning at")),
                 Age(title=_("Critical at")),
             ],
         )),
        ("job_state",
         Dictionary(
             title=_('Override check state based on job state'),
             elements=[
                 ("aborted",
                  MonitoringState(title=_("State when job state is aborted"), default_value=0)),
                 ("aborted_anime",
                  MonitoringState(title=_("State when job state is aborted_anime"),
                                  default_value=0)),
                 ("blue", MonitoringState(title=_("State when job state is blue"),
                                          default_value=0)),
                 ("blue_anime",
                  MonitoringState(title=_("State when job state is blue_anime"), default_value=0)),
                 ("disabled",
                  MonitoringState(title=_("State when job state is disabled"), default_value=0)),
                 ("disabled_anime",
                  MonitoringState(title=_("State when job state is disabled_anime"),
                                  default_value=0)),
                 ("grey", MonitoringState(title=_("State when job state is grey"),
                                          default_value=0)),
                 ("grey_anime",
                  MonitoringState(title=_("State when job state is grey_anime"), default_value=0)),
                 ("notbuilt",
                  MonitoringState(title=_("State when job state is notbuilt"), default_value=0)),
                 ("notbuilt_anime",
                  MonitoringState(title=_("State when job state is notbuilt_anime"),
                                  default_value=0)),
                 ("red", MonitoringState(title=_("State when job state is red"), default_value=2)),
                 ("red_anime",
                  MonitoringState(title=_("State when job state is red_anime"), default_value=0)),
                 ("yellow",
                  MonitoringState(title=_("State when job state is yellow"), default_value=1)),
                 ("yellow_anime",
                  MonitoringState(title=_("State when job state is yellow_anime"),
                                  default_value=0)),
             ],
         )),
        ("build_result",
         Dictionary(
             title=_('Override check state based on last build result'),
             elements=[
                 ("success",
                  MonitoringState(title=_("State when last build result is: success"),
                                  default_value=0)),
                 ("unstable",
                  MonitoringState(title=_("State when last build result is: unstable"),
                                  default_value=1)),
                 ("failure",
                  MonitoringState(title=_("State when last build result is: failed"),
                                  default_value=2)),
                 ("aborted",
                  MonitoringState(title=_("State when last build result is: aborted"),
                                  default_value=0)),
                 ("null",
                  MonitoringState(title=_("State when last build result is: module not built"),
                                  default_value=1)),
                 ("none",
                  MonitoringState(title=_("State when build result is: running"), default_value=0)),
             ],
         )),
    ],)


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="jenkins_jobs",
        group=RulespecGroupCheckParametersApplications,
        item_spec=lambda: TextAscii(title=_("Job name")),
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_jenkins_jobs,
        title=lambda: _("Jenkins jobs"),
    ))
