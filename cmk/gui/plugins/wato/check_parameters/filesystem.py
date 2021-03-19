#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Dict, List
from cmk.gui.i18n import _
from cmk.gui.valuespec import (
    Dictionary,
    ListChoice,
    ListOf,
    ListOfStrings,
    Transform,
    CascadingDropdown,
    DropdownChoice,
    TextAscii,
    TextOrRegExpUnicode,
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
        title=_("Filesystem discovery"),
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
                     "Regardless of filesystem type, these mountpoints will always be discovered."
                     "Regular expressions are supported."))),
        ],
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupCheckParametersDiscovery,
        match_type="dict",
        name="inventory_df_rules",
        valuespec=_valuespec_inventory_df_rules,
    ))


def _transform_filesystem_groups(grouping):
    """
    Old format:
    [(group_name, include_pattern), (group_name, include_pattern), ...]
    New format:
    [{group_name: name,
      patterns_include: [include_pattern, include_pattern, ...],
      patterns_exclude: [exclude_pattern, exclude_pattern, ...]},
     {group_name: name,
      patterns_include: [include_pattern, include_pattern, ...],
      patterns_exclude: [exclude_pattern, exclude_pattern, ...]},
     ...]
    """
    if not grouping or isinstance(grouping[0], dict):
        return grouping

    grouping_dict: Dict[str, List[str]] = {}
    for group_name, pattern_inclde in grouping:
        grouping_dict.setdefault(group_name, []).append(pattern_inclde)

    return [{
        'group_name': group_name,
        'patterns_include': patterns_include,
        'patterns_exclude': [],
    } for group_name, patterns_include in grouping_dict.items()]


def _valuespec_filesystem_groups():
    return Transform(
        ListOf(
            Dictionary(
                optional_keys=False,
                elements=[
                    ('group_name', TextAscii(title=_("Group name"),)),
                    (
                        'patterns_include',
                        ListOfStrings(
                            title=_("Inclusion patterns"),
                            orientation='horizontal',
                            help=_("You can specify one or several globbing patterns containing "
                                   "<tt>*</tt>, <tt>?</tt> and <tt>[...]</tt>, for example "
                                   "<tt>/spool/tmpspace*</tt>. The filesystems matching the "
                                   "patterns will be grouped together and monitored as one big "
                                   "filesystem in a single service. Note that specifically for "
                                   "the check <tt>df</tt>, the pattern matches either the mount "
                                   "point or the combination of volume and mount point, "
                                   "depending on the configuration in "
                                   "<a href='wato.py?mode=edit_ruleset&varname=inventory_df_rules'>"
                                   "Filesystem discovery</a>.")),
                    ),
                    (
                        'patterns_exclude',
                        ListOfStrings(
                            title=_("Exclusion patterns"),
                            orientation='horizontal',
                            help=_("You can specify one or several globbing patterns containing "
                                   "<tt>*</tt>, <tt>?</tt> and <tt>[...]</tt>, for example "
                                   "<tt>/spool/tmpspace*</tt>. The filesystems matching the "
                                   "patterns will excluded from grouping and monitored "
                                   "individually. Note that specifically for the check "
                                   "<tt>df</tt>, the pattern matches either the mount point or "
                                   "the combination of volume and mount point, depending on the "
                                   "configuration in "
                                   "<a href='wato.py?mode=edit_ruleset&varname=inventory_df_rules'>"
                                   "Filesystem discovery</a>.")),
                    ),
                ],
            ),
            add_label=_("Add group"),
            title=_('Filesystem grouping patterns'),
            help=_(
                'By default, the filesystem checks (<tt>df</tt>, <tt>hr_fs</tt> and others) will '
                'create a single service for each filesystem. By defining grouping patterns, you '
                'can handle groups of filesystems like one filesystem. For each group, you can '
                'define one or several include and exclude patterns. The filesystems matching one '
                'of the include patterns will be monitored like one big filesystem in a single '
                'service. The filesystems matching one of the exclude patterns will be excluded '
                'from the group and monitored individually.'),
        ),
        forth=_transform_filesystem_groups,
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
