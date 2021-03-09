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
    DropdownChoice,
    ListOfIntegers,
    ListOfStrings,
    Transform,
)

from cmk.gui.plugins.wato import (
    CheckParameterRulespecWithoutItem,
    rulespec_registry,
    RulespecGroupCheckParametersApplications,
)


def transform_ssh_config(choice):
    """
    In the sshd_config the options without-password and
    prohibit-password are equivalent. Therefore, we
    transform the old Check_MK option without-password
    to the new option key-based which represents both values.
    """
    if choice == "without-password":
        return "key-based"
    return choice


def _parameter_valuespec_sshd_config():
    return Dictionary(elements=[
        ("PermitRootLogin",
         Transform(DropdownChoice(
             title=_("Permit root login"),
             choices=[
                 ('yes', _('yes')),
                 ('key-based', _('without-password/prohibit-password (Key based)')),
                 ('forced-commands-only', _('forced-commands-only')),
                 ('no', _('no')),
             ],
             default_value="key-based",
         ),
                   forth=transform_ssh_config)),
        ("Protocol",
         DropdownChoice(
             title=_("Allowed protocols"),
             choices=[
                 ('1', _('Version 1')),
                 ('2', _('Version 2')),
                 ('1,2', _('Version 1 and 2')),
             ],
             default_value="2",
         )),
        ("Port",
         ListOfIntegers(
             title=_("Allowed Ports"),
             minvalue=0,
             maxvalue=65535,
             orientation="horizontal",
             default_value=[22],
         )),
        ("PasswordAuthentication",
         DropdownChoice(
             title=_("Allow password authentication"),
             help=_("Specifies whether password authentication is allowed"),
             choices=[
                 ('yes', _('Yes')),
                 ('no', _('No')),
             ],
             default_value="no",
         )),
        ("PermitEmptyPasswords",
         DropdownChoice(
             title=_("Permit empty passwords"),
             help=_("If password authentication is used this option "
                    "specifies wheter the server allows login to accounts "
                    "with empty passwords"),
             choices=[
                 ('yes', _('Yes')),
                 ('no', _('No')),
             ],
             default_value="no",
         )),
        ("ChallengeResponseAuthentication",
         DropdownChoice(
             title=_("Allow challenge-response authentication"),
             choices=[
                 ('yes', _('Yes')),
                 ('no', _('No')),
             ],
             default_value="no",
         )),
        ("X11Forwarding",
         DropdownChoice(
             title=_("Permit X11 forwarding"),
             choices=[
                 ('yes', _('Yes')),
                 ('no', _('No')),
             ],
             default_value="no",
         )),
        ("UsePAM",
         DropdownChoice(
             title=_("Use pluggable authentication module"),
             choices=[
                 ('yes', _('Yes')),
                 ('no', _('No')),
             ],
             default_value="no",
         )),
        ("Ciphers", ListOfStrings(
            title=_("Allowed Ciphers"),
            orientation="horizontal",
        )),
    ],)


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="sshd_config",
        group=RulespecGroupCheckParametersApplications,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_sshd_config,
        title=lambda: _("SSH daemon configuration"),
    ))
