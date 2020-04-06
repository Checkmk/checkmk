#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.valuespec import (
    Dictionary,
    ListChoice,
    ListOf,
    Transform,
    CascadingDropdown,
    DropdownChoice,
    TextAscii,
    TextOrRegExpUnicode,
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
            ("include_volume_name",
             Transform(
                 CascadingDropdown(
                     title=_("Service description format"),
                     choices=
                     [(False, _("Name of mount point")),
                      (True, _("Name of volume and name of mount point"),
                       DropdownChoice(
                           label=_("Filesystem grouping"),
                           choices=[
                               ('mountpoint', _('Grouping pattern applies to mount point only')),
                               ('volume_name_and_mountpoint',
                                _('Grouping pattern applies to volume name and mount point')),
                           ],
                           help=_(
                               "Specifies how the <a href='wato.py?mode=edit_ruleset&varname=filesystem_groups'>Filesystem grouping patterns</a> "
                               "feature processes this filesystem."),
                       ))]),
                 forth=lambda x: (True, "mountpoint") if x is True else x,
             )),
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
                 TextOrRegExpUnicode(),
                 title=_("Mountpoints to never ignore"),
                 help=_(
                     u"Regardless of filesystem type, these mountpoints will always be discovered."
                     u"Regular expressions are supported."))),
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
        Tuple(
            show_titles=True,
            orientation="horizontal",
            elements=[
                TextAscii(title=_("Name of group"),),
                TextAscii(
                    title=_("Pattern for item (using * and ?)"),
                    help=
                    _("You can specify one or several globbing patterns containing "
                      "<tt>*</tt> and <tt>?</tt>, for example <tt>/spool/tmpspace*</tt>. "
                      "The filesystems matching the patterns will be monitored "
                      "like one big filesystem in a single service. Depending on the configuration in the "
                      "<a href='wato.py?mode=edit_ruleset&varname=inventory_df_rules'>Discovery parameters "
                      " for filesystem checks</a>, the pattern matches the mount point or "
                      "the combination of volume and mount point"),
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
