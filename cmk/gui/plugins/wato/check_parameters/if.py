#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Any, List, Tuple as _Tuple, Union

from cmk.gui.exceptions import MKUserError
from cmk.gui.i18n import _
from cmk.gui.valuespec import (
    Alternative,
    CascadingDropdown,
    Dictionary,
    DictionaryEntry,
    DropdownChoice,
    DualListChoice,
    FixedValue,
    Integer,
    ListChoice,
    ListOf,
    ListOfStrings,
    MonitoringState,
    Optional,
    OptionalDropdownChoice,
    Percentage,
    RegExp,
    TextAscii,
    Transform,
    Tuple,
    defines,
)
from cmk.gui.plugins.wato import (
    RulespecGroupCheckParametersDiscovery,
    RulespecGroupCheckParametersNetworking,
    rulespec_registry,
    HostRulespec,
    BinaryHostRulespec,
    CheckParameterRulespecWithItem,
)
from cmk.gui.plugins.wato.check_parameters.utils import vs_interface_traffic


def transform_if(v):
    new_traffic: List[_Tuple[str, _Tuple[str, _Tuple[str, _Tuple[Union[int, float], Any]]]]] = []

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

    if "errors" in v:
        error_levels = v.pop("errors")
        v["errors_in"] = error_levels
        v["errors_out"] = error_levels

    # Up to and including v1.6, port state '9' was used to represent an ifAdminStatus of 2. From
    # v1.7 onwards, ifAdminStatus is handled completely separately from the port state. Note that
    # a unique transform is unfortunately not possible here. For example, translating
    # {'state': [1, 2, 9]}
    # into
    # {'state': [1, 2], 'admin_state': [2]}
    # might be too restrictive, since now, only ports with ifAdminStatus=2 are OK, whereas before,
    # also ports with ifAdminStatus=1 could have been OK.
    states = v.get('state', [])
    try:
        states.remove('9')
        removed_port_state_9 = True
    # AttributeError --> states = None --> means 'ignore the interface status'
    except (ValueError, AttributeError):
        removed_port_state_9 = False
    # if only port state 9 was selected, a unique transform is possible
    if removed_port_state_9 and v.get('state') == []:
        del v['state']
        v['admin_state'] = ['2']

    # map_operstates can be transformed uniquely
    map_operstates = v.get('map_operstates', [])
    mon_state_9 = None
    for oper_states, mon_state in map_operstates:
        if '9' in oper_states:
            mon_state_9 = mon_state
            oper_states.remove('9')
    if map_operstates:
        v['map_operstates'] = [
            mapping_oper_states for mapping_oper_states in map_operstates if mapping_oper_states
        ]
        if not v['map_operstates']:
            del v['map_operstates']
    if mon_state_9:
        v['map_admin_states'] = [(['2'], mon_state_9)]

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


def _vs_item_appearance(title, help_txt):
    return DropdownChoice(
        title=title,
        choices=[
            ('index', _('Use index')),
            ('descr', _('Use description')),
            ('alias', _('Use alias')),
        ],
        default_value='index',
        help=help_txt,
    )


def _vs_single_discovery():
    return CascadingDropdown(
        title=_("Configure discovery of single interfaces"),
        choices=[
            (
                True,
                _("Discover single interfaces"),
                Dictionary(
                    elements=[
                        (
                            'item_appearance',
                            _vs_item_appearance(
                                _("Appearance of network interface"),
                                _("This option makes checkmk use either the interface description, "
                                  "alias or port number as item."),
                            ),
                        ),
                        (
                            "pad_portnumbers",
                            DropdownChoice(
                                choices=[
                                    (True, _('Pad port numbers with zeros')),
                                    (False, _('Do not pad')),
                                ],
                                title=_("Port numbers"),
                                help=_(
                                    "If this option is activated, checkmk will pad port numbers of "
                                    "network interfaces with zeroes so that the descriptions of all "
                                    "ports of a host or switch have the same length and thus are "
                                    "sorted correctly in the GUI."),
                            ),
                        ),
                    ],
                    optional_keys=False,
                ),
            ),
            (
                False,
                _("Do not discover single interfaces"),
                FixedValue(
                    {},
                    totext="",
                ),
            ),
        ],
        sorted=False,
    )


def _vs_grouping():
    return CascadingDropdown(
        title=_("Configure grouping of interfaces"),
        help=_(
            'Normally, the interface checks create a single service for each interface. By defining '
            'interface groups, multiple interfaces can be combined together. For each group, a '
            'single service is created. This services reports the total traffic amount summed over '
            'all group members.'),
        choices=[
            (
                False,
                _("Do not group interfaces"),
                FixedValue(
                    [],
                    totext="",
                ),
            ),
            (
                True,
                _("Create the following interface groups"),
                ListOf(
                    title=_("Interface groups"),
                    add_label=_("Add pattern"),
                    valuespec=Dictionary(
                        elements=[
                            (
                                "group_name",
                                TextAscii(
                                    title=_("Group name"),
                                    help=_("Name of group in service description"),
                                    allow_empty=False,
                                ),
                            ),
                            (
                                'member_appearance',
                                _vs_item_appearance(
                                    _("Appearance of group members in service output"),
                                    _("When listing the group members in the output of the service "
                                      "monitoring the group, this option makes checkmk use either "
                                      "the interface description, alias or port number."),
                                ),
                            ),
                        ],
                        optional_keys=False,
                    ),
                    allow_empty=False,
                ),
            ),
        ],
        sorted=False,
    )


def _vs_regex_matching(match_obj):
    return ListOfStrings(
        title=_("Match interface %s (regex)" % match_obj),
        help=_("Apply this rule only to interfaces whose %s matches one of the configured regular "
               "expressions. The match is done on the beginning of the %s." %
               (match_obj, match_obj)),
        orientation="horizontal",
        valuespec=RegExp(
            size=32,
            mode=RegExp.prefix,
        ),
    )


def _note_for_admin_state_options():
    return _(
        "Note: The admin state is in general only available for the 64-bit SNMP interface check. "
        "Additionally, you have to specifically configure Checkmk to fetch this information, "
        "otherwise, using this option will have no effect. To make Checkmk fetch the admin status, "
        "activate the section <tt>if64adm</tt> via the rule "
        "<a href='wato.py?mode=edit_ruleset&varname=snmp_exclude_sections'>Include or exclude SNMP "
        "sections</a>. Note that this will lead to an increase in SNMP traffic of approximately "
        "5%.")


def _admin_states():
    return {
        1: _("up"),
        2: _("down"),
        3: _("testing"),
    }


def _vs_matching_conditions():
    return CascadingDropdown(
        title=_("Conditions for this rule to apply"),
        help=_(
            "Here, you can define conditions for applying this rule. These conditions are evaluated "
            "on a per-interface basis. When discovering an interface, checkmk will first find all "
            "rules whose conditions match this interface. Then, these rules are merged together, "
            "whereby rules from subfolders overwrite rules from the main directory. Within a "
            "directory, the order of the rules matters, i.e., rules further below in the list are "
            "overwritten by rules further up."),
        choices=[
            (
                True,
                _("Match all interfaces"),
                FixedValue(
                    {},
                    totext="",
                ),
            ),
            (
                False,
                _("Specify matching conditions"),
                Dictionary(elements=[
                    (
                        "porttypes",
                        DualListChoice(
                            title=_("Match port types"),
                            help=_("Apply this rule only to interfaces whose port type is listed "
                                   "below."),
                            choices=defines.interface_port_types(),
                            rows=40,
                            default_value=[
                                '6', '32', '62', '117', '127', '128', '129', '180', '181', '182',
                                '205', '229'
                            ],
                        ),
                    ),
                    (
                        "portstates",
                        ListChoice(
                            title=_("Match port states"),
                            help=_("Apply this rule only to interfaces whose port state is listed "
                                   "below."),
                            choices=defines.interface_oper_states(),
                            toggle_all=True,
                            default_value=['1'],
                        ),
                    ),
                    (
                        "admin_states",
                        ListChoice(
                            title=_("Match admin states (SNMP with 64-bit counters only)"),
                            help=_("Apply this rule only to interfaces whose admin state "
                                   "(<tt>ifAdminStatus</tt>) is listed below. " +
                                   _note_for_admin_state_options()),
                            choices=_admin_states(),
                            toggle_all=True,
                            default_value=['1', '2', '3'],
                        ),
                    ),
                    (
                        "match_index",
                        _vs_regex_matching("index"),
                    ),
                    (
                        "match_alias",
                        _vs_regex_matching("alias"),
                    ),
                    (
                        "match_desc",
                        _vs_regex_matching("description"),
                    ),
                ],),
            ),
        ],
        sorted=False,
    )


def _transform_discovery_if_rules(params):

    use_alias = params.pop('use_alias', None)
    if use_alias:
        params['item_appearance'] = 'alias'
    use_desc = params.pop('use_desc', None)
    if use_desc:
        params['item_appearance'] = 'descr'

    # Up to v1.6, the host rulespec inventory_if_rules had the option to activate the discovery of
    # the check rmon_stats under this key. However, rmon_stats does honor any of the other options
    # offered by inventory_if_rules. Therefore, in v1.7, the activation of the discovery of
    # rmon_stats has been moved to a separate host rulespec (rmon_discovery).
    params.pop('rmon', None)

    single_interface_discovery_settings = {}
    for key in ["item_appearance", "pad_portnumbers"]:
        if key in params:
            single_interface_discovery_settings[key] = params.pop(key)
    if single_interface_discovery_settings:
        single_interface_discovery_settings.setdefault("item_appearance", "index")
        single_interface_discovery_settings.setdefault("pad_portnumbers", True)
        params['discovery_single'] = (True, single_interface_discovery_settings)

    if 'matching_conditions' not in params:
        params['matching_conditions'] = (True, {})
    for key in ['match_alias', 'match_desc', 'portstates', 'porttypes']:
        if key in params:
            params['matching_conditions'][1][key] = params.pop(key)
            params['matching_conditions'] = (False, params['matching_conditions'][1])

    # Up to and including v1.6, port state '9' was used to represent an ifAdminStatus of 2. From
    # v1.7 onwards, ifAdminStatus is handled completely separately from the port state. Note that
    # a unique transform is unfortunately not possible here. For example, translating
    # {'portstates': [1, 2, 9]}
    # into
    # {'portstates': [1, 2], 'admin_states': [2]}
    # might be too restrictive, since we now restrict to ports with ifAdminStatus=2, whereas before,
    # also ports with for example ifAdminStatus=1 could have matched.
    matching_conditions_spec = params['matching_conditions'][1]
    try:
        matching_conditions_spec.get('portstates', []).remove('9')
        removed_port_state_9 = True
    except ValueError:
        removed_port_state_9 = False
    # if only port state 9 was selected, a unique transform is possible
    if removed_port_state_9 and matching_conditions_spec.get('portstates') == []:
        del matching_conditions_spec['portstates']
        matching_conditions_spec['admin_states'] = ['2']

    return params


def _validate_valuespec_inventory_if_rules(value, varprefix):
    if 'grouping' not in value and 'discovery_single' not in value:
        raise MKUserError(
            varprefix,
            _("Please configure at least either the discovery of single interfaces or the grouping"
             ),
        )


def _valuespec_inventory_if_rules():
    return Transform(
        Dictionary(
            title=_("Network interface and switch port discovery"),
            help=_(
                "Configure the discovery of services monitoring network interfaces and switch "
                "ports. Note that this rule is a somewhat special case compared to most other "
                "rules in checkmk. Usually, the conditions for applying a rule are configured "
                "exclusively below in the section 'Conditions'. However, here, you can define "
                "additional conditions using the options offered by 'Conditions for this rule to "
                "apply'. These conditions are evaluated on a per-interface basis and allow for "
                "configuring the discovery of the corresponding services very finely. For example, "
                "you can make checkmk discover only interfaces whose alias matches the regex 'eth' "
                "or exclude certain port types or states from being discoverd. Note that saving a "
                "rule which has only conditions specified is not allowed and will result in an "
                "error. The reason is that such a rule would have no effect."),
            elements=[
                (
                    "discovery_single",
                    _vs_single_discovery(),
                ),
                (
                    "grouping",
                    _vs_grouping(),
                ),
                (
                    "matching_conditions",
                    _vs_matching_conditions(),
                ),
            ],
            optional_keys=['discovery_single', 'grouping'],
            default_keys=['discovery_single'],
            validate=_validate_valuespec_inventory_if_rules,
        ),
        forth=_transform_discovery_if_rules,
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupCheckParametersDiscovery,
        match_type="list",
        name="inventory_if_rules",
        valuespec=_valuespec_inventory_if_rules,
    ))

vs_elements_if_groups_matches: List[DictionaryEntry] = [
    ("iftype",
     Transform(
         DropdownChoice(
             title=_("Select interface port type"),
             choices=ListChoice.dict_choices(defines.interface_port_types()),
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


def _valuespec_if_groups():
    node_name_elements: List[DictionaryEntry] = [("node_name", TextAscii(title=_("Node name")))]
    return Transform(Alternative(
        title=_('Network interface groups'),
        help=
        _('Normally the Interface checks create a single service for interface. '
          'By defining if-group patterns multiple interfaces can be combined together. '
          'A single service is created for this interface group showing the total traffic amount '
          'of its members. You can configure if interfaces which are identified as group interfaces '
          'should not show up as single service. You can restrict grouped interfaces by iftype and the '
          'item name of the single interface.'),
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
                                              valuespec=Dictionary(elements=node_name_elements +
                                                                   vs_elements_if_groups_matches,
                                                                   required_keys=["node_name"]),
                                              allow_empty=False,
                                          ))],
                                        optional_keys=[])),
        ],
    ),
                     forth=transform_if_groups_forth)


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupCheckParametersNetworking,
        is_deprecated=True,
        match_type="all",
        name="if_groups",
        valuespec=_valuespec_if_groups,
    ))


def _help_if_disable_if64_hosts():
    return _("A couple of switches with broken firmware report that they support 64 bit "
             "counters but do not output any actual data in those counters. Listing those "
             "hosts in this rule forces them to use the interface check with 32 bit counters "
             "instead.")


rulespec_registry.register(
    BinaryHostRulespec(
        group=RulespecGroupCheckParametersNetworking,
        help_func=_help_if_disable_if64_hosts,
        name="if_disable_if64_hosts",
        title=lambda: _("Hosts forced to use 'if' instead of 'if64'"),
        is_deprecated=True,
    ))


def _vs_if_errors(title):
    return Alternative(
        title=_("Levels for %s error rates" % title),
        help=_(
            "These levels make the check go warning or critical whenever the "
            "<b>percentual {0} error rate</b> or the <b>absolute {0} error rate</b> of the monitored interface reaches "
            "the given bounds. The percentual {0} error rate is computed by dividing number of "
            "errors by the total number of packets (successful plus errors).".format(title)),
        elements=[
            Tuple(title=_("Percentual levels for %s error rates" % title),
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
            Tuple(title=_("Absolute levels for %s error rates" % title),
                  elements=[
                      Integer(title=_("Warning at"), unit=_("errors")),
                      Integer(title=_("Critical at"), unit=_("errors"))
                  ])
        ])


def _item_spec_if():
    return TextAscii(title=_("port specification"), allow_empty=False)


def _parameter_valuespec_if():
    # Transform old traffic related levels which used "traffic" and "traffic_minimum"
    # keys where each was configured with an Alternative valuespec
    return Transform(
        Dictionary(
            ignored_keys=[
                "aggregate",
                "discovered_oper_status",
                "discovered_admin_status",
                "discovered_speed",
            ],  # Created by discovery
            elements=[
                ("errors_in", _vs_if_errors("IN")),
                ("errors_out", _vs_if_errors("OUT")),
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
                 Optional(ListChoice(title=_("Allowed operational states:"),
                                     choices=defines.interface_oper_states()),
                          title=_("Operational state"),
                          help=_(
                              "If you activate the monitoring of the operational state "
                              "(<tt>ifOperStatus</tt>), the check will go critical if the current "
                              "state of the interface does not match one of the expected states."),
                          label=_("Ignore the operational state"),
                          none_label=_("ignore"),
                          negate=True)),
                ("map_operstates",
                 ListOf(
                     Tuple(orientation="horizontal",
                           elements=[
                               ListChoice(choices=defines.interface_oper_states()),
                               MonitoringState()
                           ]),
                     title=_('Map operational states'),
                     help=_(
                         'Map the operational state (<tt>ifOperStatus</tt>) to a monitoring state.')
                 )),
                ("admin_state",
                 Optional(
                     ListChoice(title=_("Allowed admin states:"), choices=_admin_states()),
                     title=_("Admin state (SNMP with 64-bit counters only)"),
                     help=_("If you activate the monitoring of the admin state "
                            "(<tt>ifAdminStatus</tt>), the check will go critical if the "
                            "current state of the interface does not match one of the expected "
                            "states. " + _note_for_admin_state_options()),
                     label=_("Ignore the admin state"),
                     none_label=_("ignore"),
                     negate=True)),
                ("map_admin_states",
                 ListOf(
                     Tuple(orientation="horizontal",
                           elements=[ListChoice(choices=_admin_states()),
                                     MonitoringState()]),
                     title=_('Map admin states (SNMP with 64-bit counters only)'),
                     help=_("Map the admin state (<tt>ifAdminStatus</tt>) to a monitoring state. " +
                            _note_for_admin_state_options()),
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
                 DropdownChoice(
                     title=_("Measurement unit"),
                     help=_("Here you can specifiy the measurement unit of the network interface"),
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
                ("average",
                 Integer(
                     title=_("Average values for used bandwidth"),
                     help=_("By activating the computation of averages, the levels on "
                            "traffic and speed are applied to the averaged value. That "
                            "way you can make the check react only on long-time changes, "
                            "not on one-minute events."),
                     unit=_("minutes"),
                     minvalue=1,
                     default_value=15,
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
                ("multicast",
                 Alternative(title=_("Multicast packet rates"),
                             help=_(
                                 "These levels make the check go warning or critical whenever the "
                                 "<b>percentual packet rate</b> or the <b>absolute packet "
                                 "rate</b> of the monitored interface reaches the given "
                                 "bounds. The percentual packet rate is computed by "
                                 "dividing the number of multicast packets by the number "
                                 "of unicast packets."),
                             elements=[
                                 Tuple(title=_("Percentual levels for multicast packets"),
                                       elements=[
                                           Percentage(title=_("Warning at"),
                                                      unit=_("percent packets"),
                                                      default_value=10.0,
                                                      display_format='%.3f'),
                                           Percentage(title=_("Critical at"),
                                                      unit=_("percent packets"),
                                                      default_value=20.0,
                                                      display_format='%.3f')
                                       ]),
                                 Tuple(title=_("Absolute levels for multicast packets"),
                                       elements=[
                                           Integer(title=_("Warning at"), unit=_("pkts / sec")),
                                           Integer(title=_("Critical at"), unit=_("pkts / sec"))
                                       ])
                             ])),
                ("broadcast",
                 Alternative(title=_("Broadcast packet rates"),
                             help=_(
                                 "These levels make the check go warning or critical whenever the "
                                 "<b>percentual packet rate</b> or the <b>absolute packet "
                                 "rate</b> of the monitored interface reaches the given "
                                 "bounds. The percentual packet rate is computed by "
                                 "dividing the number of broadcast packets by the number "
                                 "of unicast packets."),
                             elements=[
                                 Tuple(title=_("Percentual levels for broadcast packets"),
                                       elements=[
                                           Percentage(title=_("Warning at"),
                                                      unit=_("percent packets"),
                                                      default_value=10.0,
                                                      display_format='%.3f'),
                                           Percentage(title=_("Critical at"),
                                                      unit=_("percent packets"),
                                                      default_value=20.0,
                                                      display_format='%.3f')
                                       ]),
                                 Tuple(title=_("Absolute levels for broadcast packets"),
                                       elements=[
                                           Integer(title=_("Warning at"), unit=_("pkts / sec")),
                                           Integer(title=_("Critical at"), unit=_("pkts / sec"))
                                       ])
                             ])),
                ("average_bm",
                 Integer(
                     title=_("Average values for broad- and multicast packet rates"),
                     help=_(
                         "By activating the computation of averages, the levels on "
                         "broad- and multicast packet rates are applied to "
                         "the averaged value. That way you can make the check react only on long-time "
                         "changes, not on one-minute events."),
                     unit=_("minutes"),
                     minvalue=1,
                     default_value=15,
                 )),
                ("discards",
                 Tuple(title=_("Absolute levels for discards rates"),
                       elements=[
                           Integer(title=_("Warning at"), unit=_("discards")),
                           Integer(title=_("Critical at"), unit=_("discards"))
                       ])),
                ("match_same_speed",
                 DropdownChoice(title=_("Speed of interface groups (Netapp only)"),
                                help=_("Choose the behaviour for different interface speeds in "
                                       "interface groups. The default is \"Check and WARN\". This "
                                       "feature is currently only supported by the check "
                                       "netapp_api_if."),
                                choices=[
                                    ("check_and_warn", _("Check and WARN")),
                                    ("check_and_crit", _("Check and CRIT")),
                                    ("check_and_display", _("Check and display only")),
                                    ("dont_show_and_check", _("Don't show and check")),
                                ])),
                ("home_port",
                 DropdownChoice(title=_("Is-Home state (Netapp only)"),
                                help=_("Choose the behaviour when the current port is not the "
                                       "home port of the respective interface. The default is "
                                       "\"Check and Display\". This feature is currently only "
                                       "supported by the check netapp_api_if."),
                                choices=[
                                    ("check_and_warn", _("Check and WARN")),
                                    ("check_and_crit", _("Check and CRIT")),
                                    ("check_and_display", _("Check and display only")),
                                    ("dont_show_and_check", _("Don't show home port info")),
                                ])),
            ],
        ),
        forth=transform_if,
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="if",
        group=RulespecGroupCheckParametersNetworking,
        item_spec=_item_spec_if,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_if,
        title=lambda: _("Network interfaces and switch ports"),
    ))


def _parameter_valuespec_k8s_if():
    return Dictionary(elements=[
        ("errors",
         Alternative(
             title=_("Levels for error rates"),
             help=_(
                 "These levels make the check go warning or critical whenever the "
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


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="k8s_if",
        group=RulespecGroupCheckParametersNetworking,
        item_spec=lambda: TextAscii(title=_("port specification"), allow_empty=False),
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_k8s_if,
        title=lambda: _("Kubernetes Network interfaces"),
    ))
