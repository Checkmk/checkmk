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
    Alternative,
    CascadingDropdown,
    defines,
    Dictionary,
    DropdownChoice,
    DualListChoice,
    Integer,
    ListChoice,
    ListOf,
    ListOfStrings,
    MonitoringState,
    Optional,
    OptionalDropdownChoice,
    Percentage,
    RadioChoice,
    RegExp,
    TextAscii,
    Transform,
    Tuple,
)
from cmk.gui.plugins.wato import (
    RulespecGroupCheckParametersDiscovery,
    RulespecGroupCheckParametersNetworking,
    rulespec_registry,
    ABCHostValueRulespec,
    ABCBinaryHostRulespec,
    CheckParameterRulespecWithItem,
)
from cmk.gui.plugins.wato.check_parameters.utils import vs_interface_traffic


def transform_if(v):
    new_traffic = []

    if 'traffic' in v and not isinstance(v['traffic'], list):
        warn, crit = v['traffic']
        if isinstance(warn, int):
            new_traffic.append(('both', ('upper', ('abs', (warn, crit)))))
        elif isinstance(warn, float):
            new_traffic.append(('both', ('upper', ('perc', (warn, crit)))))

    if 'traffic_minimum' in v:
        warn, crit = v['traffic_minimum']
        if isinstance(warn, int):
            new_traffic.append(('both', ('lower', ('abs', (warn, crit)))))
        elif isinstance(warn, float):
            new_traffic.append(('both', ('lower', ('perc', (warn, crit)))))
        del v['traffic_minimum']

    if new_traffic:
        v['traffic'] = new_traffic

    return v


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


def _transform_discovery_if_rules(params):
    use_alias = params.pop('use_alias', None)
    if use_alias:
        params['item_appearance'] = 'alias'
    use_desc = params.pop('use_desc', None)
    if use_desc:
        params['item_appearance'] = 'descr'
    return params


@rulespec_registry.register
class RulespecInventoryIfRules(ABCHostValueRulespec):
    @property
    def group(self):
        return RulespecGroupCheckParametersDiscovery

    @property
    def name(self):
        return "inventory_if_rules"

    @property
    def match_type(self):
        return "list"

    @property
    def valuespec(self):
        return Transform(
            Dictionary(
                title=_("Network Interface and Switch Port Discovery"),
                elements=[
                    ('item_appearance',
                     DropdownChoice(
                         title=_("Appearance of network interface"),
                         help=_(
                             "This option lets Check_MK use either the interface description, alias or "
                             " port number as item. The port number is the fallback/default."
                             "used anyway."),
                         choices=[
                             ('descr', _('Use description')),
                             ('alias', _('Use alias')),
                             ('index', _('Use index')),
                         ],
                         default_value='index',
                     )),
                    ("pad_portnumbers",
                     DropdownChoice(
                         choices=[
                             (True, _('Pad port numbers with zeros')),
                             (False, _('Do not pad')),
                         ],
                         title=_("Port numbers"),
                         help=_(
                             "If this option is activated then Check_MK will pad port numbers of "
                             "network interfaces with zeroes so that all port descriptions from "
                             "all ports of a host or switch have the same length and thus sort "
                             "currectly in the GUI. In versions prior to 1.1.13i3 there was no "
                             "padding. You can switch back to the old behaviour by disabling this "
                             "option. This will retain the old service descriptions and the old "
                             "performance data."),
                     )),
                    ("match_alias",
                     ListOfStrings(
                         title=_("Match interface alias (regex)"),
                         help=
                         _("Only discover interfaces whose alias matches one of the configured "
                           "regular expressions. The match is done on the beginning of the alias. "
                           "This allows you to select interfaces based on the alias without having "
                           "the alias be part of the service description."),
                         orientation="horizontal",
                         valuespec=RegExp(
                             size=32,
                             mode=RegExp.prefix,
                         ),
                     )),
                    ("match_desc",
                     ListOfStrings(
                         title=_("Match interface description (regex)"),
                         help=
                         _("Only discover interfaces whose the description matches one of the configured "
                           "regular expressions. The match is done on the beginning of the description. "
                           "This allows you to select interfaces based on the description without having "
                           "the alias be part of the service description."),
                         orientation="horizontal",
                         valuespec=RegExp(
                             size=32,
                             mode=RegExp.prefix,
                         ),
                     )),
                    ("portstates",
                     ListChoice(
                         title=_("Network interface port states to discover"),
                         help=
                         _("When doing discovery on switches or other devices with network interfaces "
                           "then only ports found in one of the configured port states will be added to the monitoring. "
                           "Note: the state <i>admin down</i> is in fact not an <tt>ifOperStatus</tt> but represents the "
                           "<tt>ifAdminStatus</tt> of <tt>down</tt> - a port administratively switched off. If you check this option "
                           "then an alternate version of the check is being used that fetches the <tt>ifAdminState</tt> in addition. "
                           "This will add about 5% of additional SNMP traffic."),
                         choices=defines.interface_oper_states(),
                         toggle_all=True,
                         default_value=['1'],
                     )),
                    ("porttypes",
                     DualListChoice(
                         title=_("Network interface port types to discover"),
                         help=
                         _("When doing discovery on switches or other devices with network interfaces "
                           "then only ports of the specified types will be created services for."),
                         choices=defines.interface_port_types(),
                         custom_order=True,
                         rows=40,
                         toggle_all=True,
                         default_value=[
                             '6', '32', '62', '117', '127', '128', '129', '180', '181', '182',
                             '205', '229'
                         ],
                     )),
                    ("rmon",
                     DropdownChoice(
                         choices=[
                             (True,
                              _("Create extra service with RMON statistics data (if available for the device)"
                               )),
                             (False, _('Do not create extra services')),
                         ],
                         title=_("Collect RMON statistics data"),
                         help=
                         _("If you enable this option, for every RMON capable switch port an additional service will "
                           "be created which is always OK and collects RMON data. This will give you detailed information "
                           "about the distribution of packet sizes transferred over the port. Note: currently "
                           "this extra RMON check does not honor the inventory settings for switch ports. In a future "
                           "version of Check_MK RMON data may be added to the normal interface service and not add "
                           "an additional service."),
                     )),
                ],
                help=_('This rule can be used to control the inventory for network ports. '
                       'You can configure the port types and port states for inventory '
                       'and the use of alias or description as service name.'),
            ),
            forth=_transform_discovery_if_rules,
        )


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


@rulespec_registry.register
class RulespecIfGroups(ABCHostValueRulespec):
    @property
    def group(self):
        return RulespecGroupCheckParametersNetworking

    @property
    def name(self):
        return "if_groups"

    @property
    def match_type(self):
        return "all"

    @property
    def valuespec(self):
        return Transform(Alternative(
            title=_('Network interface groups'),
            help=
            _('Normally the Interface checks create a single service for interface. '
              'By defining if-group patterns multiple interfaces can be combined together. '
              'A single service is created for this interface group showing the total traffic amount '
              'of its members. You can configure if interfaces which are identified as group interfaces '
              'should not show up as single service. You can restrict grouped interfaces by iftype and the '
              'item name of the single interface.'),
            style="dropdown",
            elements=[
                ListOf(
                    title=_("Groups on single host"),
                    add_label=_("Add pattern"),
                    valuespec=Dictionary(elements=vs_elements_if_groups_group +
                                         vs_elements_if_groups_matches,
                                         required_keys=["group_name", "group_presence"]),
                ),
                ListOf(magic="@!!",
                       title=_("Groups on cluster"),
                       add_label=_("Add pattern"),
                       valuespec=Dictionary(elements=vs_elements_if_groups_group +
                                            [("node_patterns",
                                              ListOf(
                                                  title=_("Patterns for each node"),
                                                  add_label=_("Add pattern"),
                                                  valuespec=Dictionary(elements=[
                                                      ("node_name", TextAscii(title=_("Node name")))
                                                  ] + vs_elements_if_groups_matches,
                                                                       required_keys=["node_name"]),
                                                  allow_empty=False,
                                              ))],
                                            optional_keys=[])),
            ],
        ),
                         forth=transform_if_groups_forth)


@rulespec_registry.register
class RulespecIfDisableIf64Hosts(ABCBinaryHostRulespec):
    @property
    def group(self):
        return RulespecGroupCheckParametersNetworking

    @property
    def name(self):
        return "if_disable_if64_hosts"

    @property
    def title(self):
        return _("Hosts forced to use <tt>if</tt> instead of <tt>if64</tt>")

    @property
    def help(self):
        return _("A couple of switches with broken firmware report that they support 64 bit "
                 "counters but do not output any actual data in those counters. Listing those "
                 "hosts in this rule forces them to use the interface check with 32 bit counters "
                 "instead.")


@rulespec_registry.register
class RulespecCheckgroupParametersIf(CheckParameterRulespecWithItem):
    @property
    def group(self):
        return RulespecGroupCheckParametersNetworking

    @property
    def check_group_name(self):
        return "if"

    @property
    def title(self):
        return _("Network interfaces and switch ports")

    @property
    def match_type(self):
        return "dict"

    @property
    def parameter_valuespec(self):
        # Transform old traffic related levels which used "traffic" and "traffic_minimum"
        # keys where each was configured with an Alternative valuespec
        return Transform(
            Dictionary(
                ignored_keys=["aggregate"],  # Created by discovery when using interface grouping
                elements=[
                    ("errors",
                     Alternative(
                         title=_("Levels for error rates"),
                         help=
                         _("These levels make the check go warning or critical whenever the "
                           "<b>percentual error rate</b> or the <b>absolute error rate</b> of the monitored interface reaches "
                           "the given bounds. The percentual error rate is computed by dividing number of "
                           "errors by the total number of packets (successful plus errors)."),
                         elements=[
                             Tuple(title=_("Percentual levels for error rates"),
                                   elements=[
                                       Percentage(title=_("Warning at"),
                                                  unit=_("percent errors"),
                                                  default_value=0.01,
                                                  display_format='%.3f'),
                                       Percentage(title=_("Critical at"),
                                                  unit=_("percent errors"),
                                                  default_value=0.1,
                                                  display_format='%.3f')
                                   ]),
                             Tuple(title=_("Absolute levels for error rates"),
                                   elements=[
                                       Integer(title=_("Warning at"), unit=_("errors")),
                                       Integer(title=_("Critical at"), unit=_("errors"))
                                   ])
                         ])),
                    ("speed",
                     OptionalDropdownChoice(
                         title=_("Operating speed"),
                         help=_("If you use this parameter then the check goes warning if the "
                                "interface is not operating at the expected speed (e.g. it "
                                "is working with 100Mbit/s instead of 1Gbit/s.<b>Note:</b> "
                                "some interfaces do not provide speed information. In such cases "
                                "this setting is used as the assumed speed when it comes to "
                                "traffic monitoring (see below)."),
                         choices=[
                             (None, _("ignore speed")),
                             (10000000, "10 Mbit/s"),
                             (100000000, "100 Mbit/s"),
                             (1000000000, "1 Gbit/s"),
                             (10000000000, "10 Gbit/s"),
                         ],
                         otherlabel=_("specify manually ->"),
                         explicit=Integer(title=_("Other speed in bits per second"),
                                          label=_("Bits per second")))),
                    ("state",
                     Optional(
                         ListChoice(title=_("Allowed states:"),
                                    choices=defines.interface_oper_states()),
                         title=_("Operational state"),
                         help=
                         _("If you activate the monitoring of the operational state (<tt>ifOperStatus</tt>) "
                           "the check will get warning or critical if the current state "
                           "of the interface does not match one of the expected states. Note: the status 9 (<i>admin down</i>) "
                           "is only visible if you activate this status during switch port inventory or if you manually "
                           "use the check plugin <tt>if64adm</tt> instead of <tt>if64</tt>."),
                         label=_("Ignore the operational state"),
                         none_label=_("ignore"),
                         negate=True)),
                    ("map_operstates",
                     ListOf(
                         Tuple(orientation="horizontal",
                               elements=[
                                   DropdownChoice(choices=defines.interface_oper_states()),
                                   MonitoringState()
                               ]),
                         title=_('Map operational states'),
                     )),
                    ("assumed_speed_in",
                     OptionalDropdownChoice(
                         title=_("Assumed input speed"),
                         help=_(
                             "If the automatic detection of the link speed does not work "
                             "or the switch's capabilities are throttled because of the network setup "
                             "you can set the assumed speed here."),
                         choices=[
                             (None, _("ignore speed")),
                             (10000000, "10 Mbit/s"),
                             (100000000, "100 Mbit/s"),
                             (1000000000, "1 Gbit/s"),
                             (10000000000, "10 Gbit/s"),
                         ],
                         otherlabel=_("specify manually ->"),
                         default_value=16000000,
                         explicit=Integer(title=_("Other speed in bits per second"),
                                          label=_("Bits per second"),
                                          size=10))),
                    ("assumed_speed_out",
                     OptionalDropdownChoice(
                         title=_("Assumed output speed"),
                         help=_(
                             "If the automatic detection of the link speed does not work "
                             "or the switch's capabilities are throttled because of the network setup "
                             "you can set the assumed speed here."),
                         choices=[
                             (None, _("ignore speed")),
                             (10000000, "10 Mbit/s"),
                             (100000000, "100 Mbit/s"),
                             (1000000000, "1 Gbit/s"),
                             (10000000000, "10 Gbit/s"),
                         ],
                         otherlabel=_("specify manually ->"),
                         default_value=1500000,
                         explicit=Integer(title=_("Other speed in bits per second"),
                                          label=_("Bits per second"),
                                          size=12))),
                    ("unit",
                     RadioChoice(
                         title=_("Measurement unit"),
                         help=_(
                             "Here you can specifiy the measurement unit of the network interface"),
                         default_value="byte",
                         choices=[
                             ("bit", _("Bits")),
                             ("byte", _("Bytes")),
                         ],
                     )),
                    ("infotext_format",
                     DropdownChoice(
                         title=_("Change infotext in check output"),
                         help=
                         _("This setting allows you to modify the information text which is displayed between "
                           "the two brackets in the check output. Please note that this setting does not work for "
                           "grouped interfaces, since the additional information of grouped interfaces is different"
                          ),
                         choices=[
                             ("alias", _("Show alias")),
                             ("description", _("Show description")),
                             ("alias_and_description", _("Show alias and description")),
                             ("alias_or_description", _("Show alias if set, else description")),
                             ("desription_or_alias", _("Show description if set, else alias")),
                             ("hide", _("Hide infotext")),
                         ])),
                    ("traffic",
                     ListOf(
                         CascadingDropdown(title=_("Direction"),
                                           orientation="horizontal",
                                           choices=[
                                               ('both', _("In / Out"), vs_interface_traffic()),
                                               ('in', _("In"), vs_interface_traffic()),
                                               ('out', _("Out"), vs_interface_traffic()),
                                           ]),
                         title=_("Used bandwidth (minimum or maximum traffic)"),
                         help=_("Setting levels on the used bandwidth is optional. If you do set "
                                "levels you might also consider using averaging."),
                     )),
                    (
                        "nucasts",
                        Tuple(
                            title=_("Non-unicast packet rates"),
                            help=_(
                                "Setting levels on non-unicast packet rates is optional. This may help "
                                "to detect broadcast storms and other unwanted traffic."),
                            elements=[
                                Integer(title=_("Warning at"), unit=_("pkts / sec")),
                                Integer(title=_("Critical at"), unit=_("pkts / sec")),
                            ]),
                    ),
                    ("discards",
                     Tuple(title=_("Absolute levels for discards rates"),
                           elements=[
                               Integer(title=_("Warning at"), unit=_("discards")),
                               Integer(title=_("Critical at"), unit=_("discards"))
                           ])),
                    ("average",
                     Integer(
                         title=_("Average values"),
                         help=_("By activating the computation of averages, the levels on "
                                "errors and traffic are applied to the averaged value. That "
                                "way you can make the check react only on long-time changes, "
                                "not on one-minute events."),
                         unit=_("minutes"),
                         minvalue=1,
                         default_value=15,
                     )),
                    ("match_same_speed",
                     DropdownChoice(title=_("Speed of interface groups (Netapp only)"),
                                    help=_(
                                        "Choose the behaviour for different interface speeds in "
                                        "interface groups. The default is \"Check and WARN\". This "
                                        "feature is currently only supported by the check "
                                        "netapp_api_if."),
                                    choices=[
                                        ("check_and_warn", _("Check and WARN")),
                                        ("check_and_crit", _("Check and CRIT")),
                                        ("check_and_display", _("Check and display only")),
                                        ("dont_show_and_check", _("Don't show and check")),
                                    ])),
                ],
            ),
            forth=transform_if,
        )

    @property
    def item_spec(self):
        return TextAscii(title=_("port specification"), allow_empty=False)


@rulespec_registry.register
class RulespecCheckgroupParametersK8SIf(CheckParameterRulespecWithItem):
    @property
    def group(self):
        return RulespecGroupCheckParametersNetworking

    @property
    def check_group_name(self):
        return "k8s_if"

    @property
    def title(self):
        return _("Kubernetes Network interfaces")

    @property
    def match_type(self):
        return "dict"

    @property
    def parameter_valuespec(self):
        return Dictionary(elements=[
            ("errors",
             Alternative(
                 title=_("Levels for error rates"),
                 help=
                 _("These levels make the check go warning or critical whenever the "
                   "<b>percentual error rate</b> or the <b>absolute error rate</b> of the monitored interface reaches "
                   "the given bounds. The percentual error rate is computed by dividing number of "
                   "errors by the total number of packets (successful plus errors)."),
                 elements=[
                     Tuple(title=_("Percentual levels for error rates"),
                           elements=[
                               Percentage(title=_("Warning at"),
                                          unit=_("percent errors"),
                                          default_value=0.01,
                                          display_format='%.3f'),
                               Percentage(title=_("Critical at"),
                                          unit=_("percent errors"),
                                          default_value=0.1,
                                          display_format='%.3f')
                           ]),
                     Tuple(title=_("Absolute levels for error rates"),
                           elements=[
                               Integer(title=_("Warning at"), unit=_("errors")),
                               Integer(title=_("Critical at"), unit=_("errors"))
                           ])
                 ])),
            ("discards",
             Tuple(
                 title=_("Absolute levels for discards rates"),
                 elements=[
                     Integer(title=_("Warning at"), unit=_("discards")),
                     Integer(title=_("Critical at"), unit=_("discards"))
                 ],
             )),
        ],)

    @property
    def item_spec(self):
        return TextAscii(title=_("port specification"), allow_empty=False)
