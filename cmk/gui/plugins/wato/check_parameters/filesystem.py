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
    Checkbox,
    Dictionary,
    ListChoice,
    ListOf,
    TextAscii,
    TextUnicode,
    Tuple,
)

from cmk.gui.plugins.wato import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersDiscovery,
    RulespecGroupCheckParametersStorage,
    HostRulespec,
)
from cmk.gui.plugins.wato.check_parameters.utils import vs_filesystem


def _valuespec_inventory_df_rules():
    return Dictionary(
        title=_("Discovery parameters for filesystem checks"),
        elements=[
            ("include_volume_name", Checkbox(title=_("Include Volume name in item"))),
            ("ignore_fs_types",
             ListChoice(title=_("Filesystem types to ignore"),
                        choices=[
                            ("tmpfs", "tmpfs"),
                            ("nfs", "nfs"),
                            ("smbfs", "smbfs"),
                            ("cifs", "cifs"),
                            ("iso9660", "iso9660"),
                        ],
                        default_value=["tmpfs", "nfs", "smbfs", "cifs", "iso9660"])),
            ("never_ignore_mountpoints",
             ListOf(
                 TextUnicode(),
                 title=_(u"Mountpoints to never ignore"),
                 help=_(
                     u"Regardless of filesystem type, these mountpoints will always be discovered."
                     u"Globbing or regular expressions are currently not supported."),
             )),
        ],
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupCheckParametersDiscovery,
        match_type="dict",
        name="inventory_df_rules",
        valuespec=_valuespec_inventory_df_rules,
    ))


def _valuespec_filesystem_groups():
    return ListOf(
        Tuple(show_titles=True,
              orientation="horizontal",
              elements=[
                  TextAscii(title=_("Name of group"),),
                  TextAscii(
                      title=_("Pattern for mount point (using * and ?)"),
                      help=_("You can specify one or several patterns containing "
                             "<tt>*</tt> and <tt>?</tt>, for example <tt>/spool/tmpspace*</tt>. "
                             "The filesystems matching the patterns will be monitored "
                             "like one big filesystem in a single service."),
                  ),
              ]),
        add_label=_("Add pattern"),
        title=_('Filesystem grouping patterns'),
        help=_('Normally the filesystem checks (<tt>df</tt>, <tt>hr_fs</tt> and others) '
               'will create a single service for each filesystem. '
               'By defining grouping '
               'patterns you can handle groups of filesystems like one filesystem. '
               'For each group you can define one or several patterns. '
               'The filesystems matching one of the patterns '
               'will be monitored like one big filesystem in a single service.'),
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupCheckParametersStorage,
        match_type="all",
        name="filesystem_groups",
        valuespec=_valuespec_filesystem_groups,
    ))


def _item_spec_filesystem():
    return TextAscii(
        title=_("Mount point"),
        help=_("For Linux/UNIX systems, specify the mount point, for Windows systems "
               "the drive letter uppercase followed by a colon and a slash, e.g. <tt>C:/</tt>"),
        allow_empty=False)


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="filesystem",
        group=RulespecGroupCheckParametersStorage,
        item_spec=_item_spec_filesystem,
        match_type="dict",
        parameter_valuespec=vs_filesystem,
        title=lambda: _("Filesystems (used space and growth)"),
    ))
