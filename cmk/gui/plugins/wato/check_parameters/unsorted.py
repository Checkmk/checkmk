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

import re
import cmk.utils.defines as defines

from cmk.gui.plugins.wato.active_checks import check_icmp_params

from cmk.gui.exceptions import MKUserError
from cmk.gui.i18n import _
from cmk.gui.valuespec import (
    Dictionary,
    Tuple,
    Integer,
    TextAscii,
    DropdownChoice,
    Checkbox,
    RegExp,
    Alternative,
    ListChoice,
    Transform,
    ListOf,
    ListOfStrings,
    FixedValue,
    DualListChoice,
    RadioChoice,
    TextUnicode,
    RegExpUnicode,
)
from cmk.gui.plugins.wato import (
    RulespecGroupCheckParametersApplications,
    RulespecGroupCheckParametersDiscovery,
    RulespecGroupCheckParametersNetworking,
    RulespecGroupCheckParametersStorage,
    register_rule,
    UserIconOrAction,
)
from cmk.gui.plugins.wato.check_parameters.ps import process_level_elements

# TODO: Sort all rules and check parameters into the figlet header sections.
# Beware: there are dependencies, so sometimes the order matters.  All rules
# that are not yet handles are in the last section: in "Unsorted".  Move rules
# from there into their appropriate sections until "Unsorted" is empty.
# Create new rules directly in the correct secions.

#   .--Networking----------------------------------------------------------.
#   |        _   _      _                      _    _                      |
#   |       | \ | | ___| |___      _____  _ __| | _(_)_ __   __ _          |
#   |       |  \| |/ _ \ __\ \ /\ / / _ \| '__| |/ / | '_ \ / _` |         |
#   |       | |\  |  __/ |_ \ V  V / (_) | |  |   <| | | | | (_| |         |
#   |       |_| \_|\___|\__| \_/\_/ \___/|_|  |_|\_\_|_| |_|\__, |         |
#   |                                                       |___/          |
#   '----------------------------------------------------------------------'

register_rule(
    RulespecGroupCheckParametersNetworking,
    "ping_levels",
    Dictionary(
        title=_("PING and host check parameters"),
        help=_("This rule sets the parameters for the host checks (via <tt>check_icmp</tt>) "
               "and also for PING checks on ping-only-hosts. For the host checks only the "
               "critical state is relevant, the warning levels are ignored."),
        elements=check_icmp_params,
    ),
    match="dict")

#.
#   .--Inventory-----------------------------------------------------------.
#   |            ___                      _                                |
#   |           |_ _|_ ____   _____ _ __ | |_ ___  _ __ _   _              |
#   |            | || '_ \ \ / / _ \ '_ \| __/ _ \| '__| | | |             |
#   |            | || | | \ V /  __/ | | | || (_) | |  | |_| |             |
#   |           |___|_| |_|\_/ \___|_| |_|\__\___/|_|   \__, |             |
#   |                                                   |___/              |
#   '----------------------------------------------------------------------'


# In version 1.2.4 the check parameters for the resulting ps check
# where defined in the dicovery rule. We moved that to an own rule
# in the classical check parameter style. In order to support old
# configuration we allow reading old discovery rules and ship these
# settings in an optional sub-dictionary.
def convert_inventory_processes(old_dict):
    new_dict = {"default_params": {}}
    for key, value in old_dict.items():
        if key in [
                'levels',
                'handle_count',
                'cpulevels',
                'cpu_average',
                'virtual_levels',
                'resident_levels',
        ]:
            new_dict["default_params"][key] = value
        elif key != "perfdata":
            new_dict[key] = value

    # New cpu rescaling load rule
    if old_dict.get('cpu_rescale_max') is None:
        new_dict['cpu_rescale_max'] = True

    return new_dict


def forbid_re_delimiters_inside_groups(pattern, varprefix):
    # Used as input validation in PS check wato config
    group_re = r'\(.*?\)'
    for match in re.findall(group_re, pattern):
        for char in ['\\b', '$', '^']:
            if char in match:
                raise MKUserError(
                    varprefix,
                    _('"%s" is not allowed inside the regular expression group %s. '
                      'Bounding characters inside groups will vanish after discovery, '
                      'because processes are instanced for every matching group. '
                      'Thus enforce delimiters outside the group.') % (char, match))


register_rule(
    RulespecGroupCheckParametersDiscovery,
    varname="inventory_processes_rules",
    title=_('Process Discovery'),
    help=_(
        "This ruleset defines criteria for automatically creating checks for running processes "
        "based upon what is running when the service discovery is done. These services will be "
        "created with default parameters. They will get critical when no process is running and "
        "OK otherwise. You can parameterize the check with the ruleset <i>State and count of processes</i>."
    ),
    valuespec=Transform(
        Dictionary(
            elements=[
                ('descr',
                 TextAscii(
                     title=_('Process Name'),
                     style="dropdown",
                     allow_empty=False,
                     help=
                     _('<p>The process name may contain one or more occurances of <tt>%s</tt>. If you do this, then the pattern must be a regular '
                       'expression and be prefixed with ~. For each <tt>%s</tt> in the description, the expression has to contain one "group". A group '
                       'is a subexpression enclosed in brackets, for example <tt>(.*)</tt> or <tt>([a-zA-Z]+)</tt> or <tt>(...)</tt>. When the inventory finds a process '
                       'matching the pattern, it will substitute all such groups with the actual values when creating the check. That way one '
                       'rule can create several checks on a host.</p>'
                       '<p>If the pattern contains more groups then occurrances of <tt>%s</tt> in the service description then only the first matching '
                       'subexpressions  are used for the  service descriptions. The matched substrings corresponding to the remaining groups '
                       'are copied into the regular expression, nevertheless.</p>'
                       '<p>As an alternative to <tt>%s</tt> you may also use <tt>%1</tt>, <tt>%2</tt>, etc. '
                       'These will be replaced by the first, second, ... matching group. This allows you to reorder things.</p>'
                      ),
                 )),
                (
                    'match',
                    Alternative(
                        title=_("Process Matching"),
                        style="dropdown",
                        elements=[
                            TextAscii(
                                title=_("Exact name of the process without argments"),
                                label=_("Executable:"),
                                size=50,
                            ),
                            Transform(
                                RegExp(
                                    size=50,
                                    mode=RegExp.prefix,
                                    validate=forbid_re_delimiters_inside_groups,
                                ),
                                title=_("Regular expression matching command line"),
                                label=_("Command line:"),
                                help=
                                _("This regex must match the <i>beginning</i> of the complete "
                                  "command line of the process including arguments.<br>"
                                  "When using groups, matches will be instantiated "
                                  "during process discovery. e.g. (py.*) will match python, python_dev "
                                  "and python_test and discover 3 services. At check time, because "
                                  "python is a substring of python_test and python_dev it will aggregate"
                                  "all process that start with python. If that is not the intended behavior "
                                  "please use a delimiter like '$' or '\\b' around the group, e.g. (py.*)$"
                                 ),
                                forth=lambda x: x[1:],  # remove ~
                                back=lambda x: "~" + x,  # prefix ~
                            ),
                            FixedValue(
                                None,
                                totext="",
                                title=_("Match all processes"),
                            )
                        ],
                        match=lambda x: (not x and 2) or (x[0] == '~' and 1 or 0),
                        default_value='/usr/sbin/foo')),
                ('user',
                 Alternative(
                     title=_('Name of the User'),
                     style="dropdown",
                     elements=[
                         FixedValue(
                             None,
                             totext="",
                             title=_("Match all users"),
                         ),
                         TextAscii(
                             title=_('Exact name of the user'),
                             label=_("User:"),
                         ),
                         FixedValue(
                             False,
                             title=_('Grab user from found processess'),
                             totext='',
                         ),
                     ],
                     help=
                     _('<p>The user specification can either be a user name (string). The inventory will then trigger only if that user matches '
                       'the user the process is running as and the resulting check will require that user. Alternatively you can specify '
                       '"grab user". If user is not selected the created check will not check for a specific user.</p>'
                       '<p>Specifying "grab user" makes the created check expect the process to run as the same user as during inventory: the user '
                       'name will be hardcoded into the check. In that case if you put %u into the service description, that will be replaced '
                       'by the actual user name during inventory. You need that if your rule might match for more than one user - your would '
                       'create duplicate services with the same description otherwise.</p><p>Windows users are specified by the namespace followed by '
                       'the actual user name. For example "\\\\NT AUTHORITY\\NETWORK SERVICE" or "\\\\CHKMKTEST\\Administrator".</p>'
                      ),
                 )),
                ('icon',
                 UserIconOrAction(
                     title=_("Add custom icon or action"),
                     help=_(
                         "You can assign icons or actions to the found services in the status GUI."
                     ),
                 )),
                ("cpu_rescale_max",
                 RadioChoice(
                     title=_("CPU rescale maximum load"),
                     help=_("CPU utilization is delivered by the Operating "
                            "System as a per CPU core basis. Thus each core contributes "
                            "with a 100% at full utilization, producing a maximum load "
                            "of N*100% (N=number of cores). For simplicity this maximum "
                            "can be rescaled down, making 100% the maximum and thinking "
                            "in terms of total CPU utilization."),
                     default_value=True,
                     orientation="vertical",
                     choices=[
                         (True, _("100% is all cores at full load")),
                         (False,
                          _("<b>N</b> * 100% as each core contributes with 100% at full load")),
                     ])),
                ('default_params',
                 Dictionary(
                     title=_("Default parameters for detected services"),
                     help=
                     _("Here you can select default parameters that are being set "
                       "for detected services. Note: the preferred way for setting parameters is to use "
                       "the rule set <a href='wato.py?varname=checkgroup_parameters%3Apsmode=edit_ruleset'> "
                       "State and Count of Processes</a> instead. "
                       "A change there will immediately be active, while a change in this rule "
                       "requires a re-discovery of the services."),
                     elements=process_level_elements,
                 )),
            ],
            required_keys=["descr", "cpu_rescale_max"],
        ),
        forth=convert_inventory_processes,
    ),
    match='all',
)

register_rule(
    RulespecGroupCheckParametersDiscovery,
    varname="inv_domino_tasks_rules",
    title=_('Lotus Domino Task Discovery'),
    help=_("This rule controls the discovery of tasks on Lotus Domino systems. "
           "Any changes later on require a host re-discovery"),
    valuespec=Dictionary(
        elements=[
            ('descr',
             TextAscii(
                 title=_('Service Description'),
                 allow_empty=False,
                 help=
                 _('<p>The service description may contain one or more occurances of <tt>%s</tt>. In this '
                   'case, the pattern must be a regular expression prefixed with ~. For each '
                   '<tt>%s</tt> in the description, the expression has to contain one "group". A group '
                   'is a subexpression enclosed in brackets, for example <tt>(.*)</tt> or '
                   '<tt>([a-zA-Z]+)</tt> or <tt>(...)</tt>. When the inventory finds a task '
                   'matching the pattern, it will substitute all such groups with the actual values when '
                   'creating the check. In this way one rule can create several checks on a host.</p>'
                   '<p>If the pattern contains more groups than occurrences of <tt>%s</tt> in the service '
                   'description, only the first matching subexpressions are used for the service '
                   'descriptions. The matched substrings corresponding to the remaining groups '
                   'are nevertheless copied into the regular expression.</p>'
                   '<p>As an alternative to <tt>%s</tt> you may also use <tt>%1</tt>, <tt>%2</tt>, etc. '
                   'These expressions will be replaced by the first, second, ... matching group, allowing '
                   'you to reorder things.</p>'),
             )),
            (
                'match',
                Alternative(
                    title=_("Task Matching"),
                    elements=[
                        TextAscii(
                            title=_("Exact name of the task"),
                            size=50,
                        ),
                        Transform(
                            RegExp(
                                size=50,
                                mode=RegExp.prefix,
                            ),
                            title=_("Regular expression matching command line"),
                            help=_("This regex must match the <i>beginning</i> of the task"),
                            forth=lambda x: x[1:],  # remove ~
                            back=lambda x: "~" + x,  # prefix ~
                        ),
                        FixedValue(
                            None,
                            totext="",
                            title=_("Match all tasks"),
                        )
                    ],
                    match=lambda x: (not x and 2) or (x[0] == '~' and 1 or 0),
                    default_value='foo')),
            ('levels',
             Tuple(
                 title=_('Levels'),
                 help=
                 _("Please note that if you specify and also if you modify levels here, the change is "
                   "activated only during an inventory.  Saving this rule is not enough. This is due to "
                   "the nature of inventory rules."),
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
                         default_value=1,
                     ),
                     Integer(
                         title=_("Critical above"),
                         unit=_("processes"),
                         default_value=1,
                     ),
                 ],
             )),
        ],
        required_keys=['match', 'levels', 'descr'],
    ),
    match='all',
)

register_rule(
    RulespecGroupCheckParametersDiscovery,
    varname="inventory_sap_values",
    title=_('SAP R/3 Single Value Inventory'),
    valuespec=Dictionary(
        elements=[
            (
                'match',
                Alternative(
                    title=_("Node Path Matching"),
                    elements=[
                        TextAscii(
                            title=_("Exact path of the node"),
                            size=100,
                        ),
                        Transform(
                            RegExp(
                                size=100,
                                mode=RegExp.prefix,
                            ),
                            title=_("Regular expression matching the path"),
                            help=_("This regex must match the <i>beginning</i> of the complete "
                                   "path of the node as reported by the agent"),
                            forth=lambda x: x[1:],  # remove ~
                            back=lambda x: "~" + x,  # prefix ~
                        ),
                        FixedValue(
                            None,
                            totext="",
                            title=_("Match all nodes"),
                        )
                    ],
                    match=lambda x: (not x and 2) or (x[0] == '~' and 1 or 0),
                    default_value=
                    'SAP CCMS Monitor Templates/Dialog Overview/Dialog Response Time/ResponseTime')
            ),
            ('limit_item_levels',
             Integer(
                 title=_("Limit Path Levels for Service Names"),
                 unit=_('path levels'),
                 minvalue=1,
                 help=
                 _("The service descriptions of the inventorized services are named like the paths "
                   "in SAP. You can use this option to let the inventory function only use the last "
                   "x path levels for naming."),
             ))
        ],
        optional_keys=['limit_item_levels'],
    ),
    match='all',
)

register_rule(
    RulespecGroupCheckParametersDiscovery,
    varname="sap_value_groups",
    title=_('SAP Value Grouping Patterns'),
    help=_('The check <tt>sap.value</tt> normally creates one service for each SAP value. '
           'By defining grouping patterns, you can switch to the check <tt>sap.value-groups</tt>. '
           'That check monitors a list of SAP values at once.'),
    valuespec=ListOf(
        Tuple(
            help=_("This defines one value grouping pattern"),
            show_titles=True,
            orientation="horizontal",
            elements=[
                TextAscii(title=_("Name of group"),),
                Tuple(
                    show_titles=True,
                    orientation="vertical",
                    elements=[
                        RegExpUnicode(
                            title=_("Include Pattern"),
                            mode=RegExp.prefix,
                        ),
                        RegExpUnicode(
                            title=_("Exclude Pattern"),
                            mode=RegExp.prefix,
                        )
                    ],
                ),
            ],
        ),
        add_label=_("Add pattern group"),
    ),
    match='all',
)

register_rule(
    RulespecGroupCheckParametersDiscovery,
    varname="inventory_heartbeat_crm_rules",
    title=_("Heartbeat CRM Discovery"),
    valuespec=Dictionary(
        elements=[
            ("naildown_dc",
             Checkbox(
                 title=_("Naildown the DC"),
                 label=_("Mark the currently distinguished controller as preferred one"),
                 help=_(
                     "Nails down the DC to the node which is the DC during discovery. The check "
                     "will report CRITICAL when another node becomes the DC during later checks."))
            ),
            ("naildown_resources",
             Checkbox(
                 title=_("Naildown the resources"),
                 label=_("Mark the nodes of the resources as preferred one"),
                 help=_(
                     "Nails down the resources to the node which is holding them during discovery. "
                     "The check will report CRITICAL when another holds the resource during later checks."
                 ))),
        ],
        help=_('This rule can be used to control the discovery for Heartbeat CRM checks.'),
        optional_keys=[],
    ),
    match='dict',
)

register_rule(
    RulespecGroupCheckParametersDiscovery,
    varname="inventory_df_rules",
    title=_("Discovery parameters for filesystem checks"),
    valuespec=Dictionary(
        elements=[
            ("include_volume_name", Checkbox(title=_("Include Volume name in item"))),
            ("ignore_fs_types",
             ListChoice(
                 title=_("Filesystem types to ignore"),
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
        ],),
    match="dict",
)

register_rule(
    RulespecGroupCheckParametersDiscovery,
    varname="inventory_fujitsu_ca_ports",
    title=_("Discovery of Fujtsu storage CA ports"),
    valuespec=Dictionary(
        elements=[
            ("indices", ListOfStrings(title=_("CA port indices"))),
            ("modes",
             DualListChoice(
                 title=_("CA port modes"),
                 choices=[
                     ("CA", _("CA")),
                     ("RA", _("RA")),
                     ("CARA", _("CARA")),
                     ("Initiator", _("Initiator")),
                 ],
                 row=4,
                 size=30,
             )),
        ],),
    match="dict",
)

#.
#   .--Applications--------------------------------------------------------.
#   |          _                _ _           _   _                        |
#   |         / \   _ __  _ __ | (_) ___ __ _| |_(_) ___  _ __  ___        |
#   |        / _ \ | '_ \| '_ \| | |/ __/ _` | __| |/ _ \| '_ \/ __|       |
#   |       / ___ \| |_) | |_) | | | (_| (_| | |_| | (_) | | | \__ \       |
#   |      /_/   \_\ .__/| .__/|_|_|\___\__,_|\__|_|\___/|_| |_|___/       |
#   |              |_|   |_|                                               |
#   '----------------------------------------------------------------------'

register_rule(
    RulespecGroupCheckParametersApplications,
    varname="logwatch_rules",
    title=_('Logwatch Patterns'),
    valuespec=Transform(
        Dictionary(
            elements=[
                ("reclassify_patterns",
                 ListOf(
                     Tuple(
                         help=_("This defines one logfile pattern rule"),
                         show_titles=True,
                         orientation="horizontal",
                         elements=[
                             DropdownChoice(
                                 title=_("State"),
                                 choices=[
                                     ('C', _('CRITICAL')),
                                     ('W', _('WARNING')),
                                     ('O', _('OK')),
                                     ('I', _('IGNORE')),
                                 ],
                             ),
                             RegExpUnicode(
                                 title=_("Pattern (Regex)"),
                                 size=40,
                                 mode=RegExp.infix,
                             ),
                             TextUnicode(
                                 title=_("Comment"),
                                 size=40,
                             ),
                         ]),
                     title=_("Reclassify state matching regex pattern"),
                     help=
                     _('<p>You can define one or several patterns (regular expressions) in each logfile pattern rule. '
                       'These patterns are applied to the selected logfiles to reclassify the '
                       'matching log messages. The first pattern which matches a line will '
                       'be used for reclassifying a message. You can use the '
                       '<a href="wato.py?mode=pattern_editor">Logfile Pattern Analyzer</a> '
                       'to test the rules you defined here.</p>'
                       '<p>Select "Ignore" as state to get the matching logs deleted. Other states will keep the '
                       'log entries but reclassify the state of them.</p>'),
                     add_label=_("Add pattern"),
                 )),
                ("reclassify_states",
                 Dictionary(
                     title=_("Reclassify complete state"),
                     help=_(
                         "This setting allows you to convert all incoming states to another state. "
                         "The option is applied before the state conversion via regexes. So the regex values can "
                         "modify the state even further."),
                     elements=[
                         ("c_to",
                          DropdownChoice(
                              title=_("Change CRITICAL State to"),
                              choices=[
                                  ('C', _('CRITICAL')),
                                  ('W', _('WARNING')),
                                  ('O', _('OK')),
                                  ('I', _('IGNORE')),
                                  ('.', _('Context Info')),
                              ],
                              default_value="C",
                          )),
                         ("w_to",
                          DropdownChoice(
                              title=_("Change WARNING State to"),
                              choices=[
                                  ('C', _('CRITICAL')),
                                  ('W', _('WARNING')),
                                  ('O', _('OK')),
                                  ('I', _('IGNORE')),
                                  ('.', _('Context Info')),
                              ],
                              default_value="W",
                          )),
                         ("o_to",
                          DropdownChoice(
                              title=_("Change OK State to"),
                              choices=[
                                  ('C', _('CRITICAL')),
                                  ('W', _('WARNING')),
                                  ('O', _('OK')),
                                  ('I', _('IGNORE')),
                                  ('.', _('Context Info')),
                              ],
                              default_value="O",
                          )),
                         ("._to",
                          DropdownChoice(
                              title=_("Change Context Info to"),
                              choices=[
                                  ('C', _('CRITICAL')),
                                  ('W', _('WARNING')),
                                  ('O', _('OK')),
                                  ('I', _('IGNORE')),
                                  ('.', _('Context Info')),
                              ],
                              default_value=".",
                          )),
                     ],
                     optional_keys=False,
                 )),
            ],
            optional_keys=["reclassify_states"],
        ),
        forth=lambda x: isinstance(x, dict) and x or {"reclassify_patterns": x}),
    itemtype='item',
    itemname='Logfile',
    itemhelp=_("Put the item names of the logfiles here. For example \"System$\" "
               "to select the service \"LOG System\". You can use regular "
               "expressions which must match the beginning of the logfile name."),
    match='all',
)

#.
#   .--Unsorted--(Don't create new stuff here!)----------------------------.
#   |              _   _                      _           _                |
#   |             | | | |_ __  ___  ___  _ __| |_ ___  __| |               |
#   |             | | | | '_ \/ __|/ _ \| '__| __/ _ \/ _` |               |
#   |             | |_| | | | \__ \ (_) | |  | ||  __/ (_| |               |
#   |              \___/|_| |_|___/\___/|_|   \__\___|\__,_|               |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |  All these rules have not been moved into their according sections.  |
#   |  Please move them as you come along - but beware of dependecies!     |
#   |  Remove this section as soon as it's empty.                          |
#   '----------------------------------------------------------------------'

register_rule(
    RulespecGroupCheckParametersStorage,
    varname="filesystem_groups",
    title=_('Filesystem grouping patterns'),
    help=_('Normally the filesystem checks (<tt>df</tt>, <tt>hr_fs</tt> and others) '
           'will create a single service for each filesystem. '
           'By defining grouping '
           'patterns you can handle groups of filesystems like one filesystem. '
           'For each group you can define one or several patterns. '
           'The filesystems matching one of the patterns '
           'will be monitored like one big filesystem in a single service.'),
    valuespec=ListOf(
        Tuple(
            show_titles=True,
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
    ),
    match='all',
)

register_rule(
    RulespecGroupCheckParametersStorage,
    varname="fileinfo_groups",
    title=_('File Grouping Patterns'),
    help=_('The check <tt>fileinfo</tt> monitors the age and size of '
           'a single file. Each file information that is sent '
           'by the agent will create one service. By defining grouping '
           'patterns you can switch to the check <tt>fileinfo.groups</tt>. '
           'That check monitors a list of files at once. You can set levels '
           'not only for the total size and the age of the oldest/youngest '
           'file but also on the count. You can define one or several '
           'patterns for a group containing <tt>*</tt> and <tt>?</tt>, for example '
           '<tt>/var/log/apache/*.log</tt>. Please see Python\'s fnmatch for more '
           'information regarding globbing patterns and special characters. '
           'If the pattern begins with a tilde then this pattern is interpreted as '
           'a regular expression instead of as a filename globbing pattern and '
           '<tt>*</tt> and <tt>?</tt> are treated differently. '
           'For files contained in a group '
           'the discovery will automatically create a group service instead '
           'of single services for each file. This rule also applies when '
           'you use manually configured checks instead of inventorized ones. '
           'Furthermore, the current time/date in a configurable format '
           'may be included in the include pattern. The syntax is as follows: '
           '$DATE:format-spec$ or $YESTERDAY:format-spec$, where format-spec '
           'is a list of time format directives of the unix date command. '
           'Example: $DATE:%Y%m%d$ is todays date, e.g. 20140127. A pattern '
           'of /var/tmp/backups/$DATE:%Y%m%d$.txt would search for .txt files '
           'with todays date  as name in the directory /var/tmp/backups. '
           'The YESTERDAY syntax simply subtracts one day from the reference time.'),
    valuespec=ListOf(
        Tuple(
            help=_("This defines one file grouping pattern."),
            show_titles=True,
            orientation="horizontal",
            elements=[
                TextAscii(
                    title=_("Name of group"),
                    size=10,
                ),
                Transform(
                    Tuple(
                        show_titles=True,
                        orientation="vertical",
                        elements=[
                            TextAscii(title=_("Include Pattern"), size=40),
                            TextAscii(title=_("Exclude Pattern"), size=40),
                        ],
                    ),
                    forth=lambda params: isinstance(params, str) and (params, '') or params),
            ],
        ),
        add_label=_("Add pattern group"),
    ),
    match='all',
)

register_rule(
    RulespecGroupCheckParametersStorage,
    "diskstat_inventory",
    ListChoice(
        title=_("Discovery mode for Disk IO check"),
        help=_("This rule controls which and how many checks will be created "
               "for monitoring individual physical and logical disks. "
               "Note: the option <i>Create a summary for all read, one for "
               "write</i> has been removed. Some checks will still support "
               "this settings, but it will be removed there soon."),
        choices=[
            ("summary", _("Create a summary over all physical disks")),
            # This option is still supported by some checks, but is deprecated and
            # we fade it out...
            # ( "legacy",   _("Create a summary for all read, one for write") ),
            ("physical", _("Create a separate check for each physical disk")),
            ("lvm", _("Create a separate check for each LVM volume (Linux)")),
            ("vxvm", _("Creata a separate check for each VxVM volume (Linux)")),
            ("diskless", _("Creata a separate check for each partition (XEN)")),
        ],
        default_value=['summary'],
    ),
    match="first")


def transform_if_groups_forth(params):
    for param in params:
        if param.get("name"):
            param["group_name"] = param["name"]
            del param["name"]
        if param.get("include_items"):
            param["items"] = param["include_items"]
            del param["include_items"]
        if param.get("single") is not None:
            if param["single"]:
                param["group_presence"] = "instead"
            else:
                param["group_presence"] = "separate"
            del param["single"]
    return params


vs_elements_if_groups_matches = [
    ("iftype",
     Transform(
         DropdownChoice(
             title=_("Select interface port type"),
             choices=defines.interface_port_types(),
             help=_("Only interfaces with the given port type are put into this group. "
                    "For example 53 (propVirtual)."),
         ),
         forth=str,
         back=int,
     )),
    ("items",
     ListOfStrings(
         title=_("Restrict interface items"),
         help=_("Only interface with these item names are put into this group."),
     )),
]

vs_elements_if_groups_group = [
    ("group_name",
     TextAscii(
         title=_("Group name"),
         help=_("Name of group in service description"),
         allow_empty=False,
     )),
    ("group_presence",
     DropdownChoice(
         title=_("Group interface presence"),
         help=_("Determine whether the group interface is created as an "
                "separate service or not. In second case the choosen interface "
                "services disapear."),
         choices=[
             ("separate", _("List grouped interfaces separately")),
             ("instead", _("List grouped interfaces instead")),
         ],
         default_value="instead",
     )),
]

register_rule(
    RulespecGroupCheckParametersNetworking,
    varname="if_groups",
    title=_('Network interface groups'),
    help=_(
        'Normally the Interface checks create a single service for interface. '
        'By defining if-group patterns multiple interfaces can be combined together. '
        'A single service is created for this interface group showing the total traffic amount '
        'of its members. You can configure if interfaces which are identified as group interfaces '
        'should not show up as single service. You can restrict grouped interfaces by iftype and the '
        'item name of the single interface.'),
    valuespec=Transform(
        Alternative(
            style="dropdown",
            elements=[
                ListOf(
                    title=_("Groups on single host"),
                    add_label=_("Add pattern"),
                    valuespec=Dictionary(
                        elements=vs_elements_if_groups_group + vs_elements_if_groups_matches,
                        required_keys=["group_name", "group_presence"]),
                ),
                ListOf(
                    magic="@!!",
                    title=_("Groups on cluster"),
                    add_label=_("Add pattern"),
                    valuespec=Dictionary(
                        elements=vs_elements_if_groups_group +
                        [("node_patterns",
                          ListOf(
                              title=_("Patterns for each node"),
                              add_label=_("Add pattern"),
                              valuespec=Dictionary(
                                  elements=[("node_name", TextAscii(title=_("Node name")))] +
                                  vs_elements_if_groups_matches,
                                  required_keys=["node_name"]),
                              allow_empty=False,
                          ))],
                        optional_keys=[])),
            ],
        ),
        forth=transform_if_groups_forth),
    match='all',
)

register_rule(
    RulespecGroupCheckParametersDiscovery,
    varname="winperf_msx_queues_inventory",
    title=_('MS Exchange Message Queues Discovery'),
    help=_(
        'Per default the offsets of all Windows performance counters are preconfigured in the check. '
        'If the format of your counters object is not compatible then you can adapt the counter '
        'offsets manually.'),
    valuespec=ListOf(
        Tuple(
            orientation="horizontal",
            elements=[
                TextAscii(
                    title=_("Name of Counter"),
                    help=_("Name of the Counter to be monitored."),
                    size=50,
                    allow_empty=False,
                ),
                Integer(
                    title=_("Offset"),
                    help=_("The offset of the information relative to counter base"),
                    allow_empty=False,
                ),
            ]),
        movable=False,
        add_label=_("Add Counter")),
    match='all',
)

register_rule(
    RulespecGroupCheckParametersStorage,
    varname="inventory_multipath_rules",
    title=_("Linux Multipath Inventory"),
    valuespec=Dictionary(
        elements=[
            ("use_alias",
             Checkbox(
                 title=_("Use the multipath alias as service name, if one is set"),
                 label=_("use alias"),
                 help=_(
                     "If a multipath device has an alias then you can use it for specifying "
                     "the device instead of the UUID. The alias will then be part of the service "
                     "description. The UUID will be displayed in the plugin output."))),
        ],
        help=_(
            "This rule controls whether the UUID or the alias is used in the service description during "
            "discovery of Multipath devices on Linux."),
    ),
    match='dict',
)

register_rule(
    RulespecGroupCheckParametersApplications,
    varname="logwatch_groups",
    title=_('Logfile Grouping Patterns'),
    help=_('The check <tt>logwatch</tt> normally creates one service for each logfile. '
           'By defining grouping patterns you can switch to the check <tt>logwatch.groups</tt>. '
           'If the pattern begins with a tilde then this pattern is interpreted as a regular '
           'expression instead of as a filename globbing pattern and  <tt>*</tt> and <tt>?</tt> '
           'are treated differently. '
           'That check monitors a list of logfiles at once. This is useful if you have '
           'e.g. a folder with rotated logfiles where the name of the current logfile'
           'also changes with each rotation'),
    valuespec=ListOf(
        Tuple(
            help=_("This defines one logfile grouping pattern"),
            show_titles=True,
            orientation="horizontal",
            elements=[
                TextAscii(title=_("Name of group"),),
                Tuple(
                    show_titles=True,
                    orientation="vertical",
                    elements=[
                        TextAscii(title=_("Include Pattern")),
                        TextAscii(title=_("Exclude Pattern"))
                    ],
                ),
            ],
        ),
        add_label=_("Add pattern group"),
    ),
    match='all',
)

register_rule(
    RulespecGroupCheckParametersNetworking,
    "if_disable_if64_hosts",
    title=_("Hosts forced to use <tt>if</tt> instead of <tt>if64</tt>"),
    help=_("A couple of switches with broken firmware report that they "
           "support 64 bit counters but do not output any actual data "
           "in those counters. Listing those hosts in this rule forces "
           "them to use the interface check with 32 bit counters instead."))
