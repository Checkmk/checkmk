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
    Dictionary,
    Integer,
    Float,
    Tuple,
)

from cmk.gui.plugins.wato import (
    CheckParameterRulespecWithoutItem,
    rulespec_registry,
    RulespecGroupCheckParametersApplications,
)


@rulespec_registry.register
class RulespecCheckgroupParametersSkype(CheckParameterRulespecWithoutItem):
    @property
    def group(self):
        return RulespecGroupCheckParametersApplications

    @property
    def check_group_name(self):
        return "skype"

    @property
    def title(self):
        return _("Skype for Business")

    @property
    def match_type(self):
        return "dict"

    @property
    def parameter_valuespec(self):
        return Dictionary(elements=[
            ('failed_search_requests',
             Dictionary(
                 title=_("Failed search requests"),
                 elements=[
                     ("upper",
                      Tuple(elements=[
                          Float(title=_("Warning at"), unit=_("per second"), default_value=1.0),
                          Float(title=_("Critical at"), unit=_("per second"), default_value=2.0),
                      ],)),
                 ],
                 optional_keys=[],
             )),
            ('failed_locations_requests',
             Dictionary(
                 title=_("Failed Get Locations Requests"),
                 elements=[
                     ("upper",
                      Tuple(elements=[
                          Float(title=_("Warning at"), unit=_("per second"), default_value=1.0),
                          Float(title=_("Critical at"), unit=_("per second"), default_value=2.0),
                      ],)),
                 ],
                 optional_keys=[],
             )),
            ('failed_file_requests',
             Dictionary(
                 title=_("Failed requests to Adressbook files"),
                 elements=[("upper",
                            Tuple(elements=[
                                Float(title=_("Warning at"),
                                      unit=_("per second"),
                                      default_value=1.0),
                                Float(title=_("Critical at"),
                                      unit=_("per second"),
                                      default_value=2.0),
                            ],))],
                 optional_keys=[],
             )),
            ('join_failures',
             Dictionary(
                 title=_("Failures of the join launcher service"),
                 elements=[("upper",
                            Tuple(elements=[
                                Integer(title=_("Warning at"), default_value=1),
                                Integer(title=_("Critical at"), default_value=2),
                            ],))],
                 optional_keys=[],
             )),
            ('failed_validate_cert',
             Dictionary(
                 title=_("Failed certificate validations"),
                 elements=[("upper",
                            Tuple(elements=[
                                Integer(title=_("Warning at"), default_value=1),
                                Integer(title=_("Critical at"), default_value=2),
                            ],))],
                 optional_keys=[],
             )),
            ('timedout_ad_requests',
             Dictionary(
                 title=_("Timed out Active Directory Requests"),
                 elements=[
                     ("upper",
                      Tuple(elements=[
                          Float(title=_("Warning at"), unit=_("per second"), default_value=0.01),
                          Float(title=_("Critical at"), unit=_("per second"), default_value=0.02),
                      ],)),
                 ],
                 optional_keys=[],
             )),
            ('5xx_responses',
             Dictionary(
                 title=_("HTTP 5xx Responses"),
                 elements=[
                     ("upper",
                      Tuple(elements=[
                          Float(title=_("Warning at"), unit=_("per second"), default_value=1.0),
                          Float(title=_("Critical at"), unit=_("per second"), default_value=2.0),
                      ],)),
                 ],
                 optional_keys=[],
             )),
            ('asp_requests_rejected',
             Dictionary(
                 title=_("ASP Requests Rejected"),
                 elements=[
                     ("upper",
                      Tuple(elements=[
                          Integer(title=_("Warning at"), default_value=1),
                          Integer(title=_("Critical at"), default_value=2),
                      ],)),
                 ],
                 optional_keys=[],
             )),
        ],)
