#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Mapping

from cmk.gui import ifaceoper
from cmk.gui.exceptions import MKUserError
from cmk.gui.i18n import _
from cmk.gui.plugins.wato.check_parameters.interface_utils import vs_interface_traffic
from cmk.gui.plugins.wato.utils import (
    BinaryHostRulespec,
    CheckParameterRulespecWithItem,
    HostRulespec,
    rulespec_registry,
    RulespecGroupCheckParametersDiscovery,
    RulespecGroupCheckParametersNetworking,
)
from cmk.gui.valuespec import (
    Alternative,
    CascadingDropdown,
    Dictionary,
    DictionaryEntry,
    DropdownChoice,
    DualListChoice,
    FixedValue,
    Integer,
    Labels,
    ListChoice,
    ListOf,
    ListOfStrings,
    Migrate,
    MonitoringState,
    Optional,
    OptionalDropdownChoice,
    Percentage,
    RegExp,
    TextInput,
    Transform,
    Tuple,
)


def _transform_discards(v: tuple[float, float] | Mapping[str, object]) -> Mapping[str, object]:
    if isinstance(v, dict):
        return v

    (warn, crit) = v
    # old discards abs levels have been float but target is int, so cast to int
    return {"both": ("abs", (int(warn), int(crit)))}


def _vs_item_appearance(title, help_txt):
    return DropdownChoice(
        title=title,
        choices=[
            ("index", _("Use index")),
            ("descr", _("Use description")),
            ("alias", _("Use alias")),
        ],
        default_value="index",
        help=help_txt
        + _(
            "<br> <br>  "
            "<b>Important note</b>: When changing this option, the services "
            "need to be removed and rediscovered to apply the changes. "
            "Otherwise there is a risk of mismatch between the discovered "
            "and checked services."
        ),
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
                            "item_appearance",
                            _vs_item_appearance(
                                _("Appearance of network interface"),
                                _(
                                    "This option makes checkmk use either the interface description, "
                                    "alias or port number as item."
                                ),
                            ),
                        ),
                        (
                            "pad_portnumbers",
                            DropdownChoice(
                                choices=[
                                    (True, _("Pad port numbers with zeros")),
                                    (False, _("Do not pad")),
                                ],
                                title=_("Port numbers"),
                                help=_(
                                    "If this option is activated, checkmk will pad port numbers of "
                                    "network interfaces with zeroes so that the descriptions of all "
                                    "ports of a host or switch have the same length and thus are "
                                    "sorted correctly in the GUI."
                                ),
                            ),
                        ),
                        (
                            "labels",
                            Labels(
                                world=Labels.World.CONFIG,
                                label_source=Labels.Source.RULESET,
                                help=_("Create service labels that get discovered by this rule."),
                                title=_("Generate service labels for discovered interfaces"),
                            ),
                        ),
                    ],
                    optional_keys=["labels"],
                ),
            ),
            (
                False,
                _("Do not discover single interfaces"),
                FixedValue(
                    value={},
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
            "Normally, the interface checks create a single service for each interface. By defining "
            "interface groups, multiple interfaces can be combined together. For each group, a "
            "single service is created. These services report the total traffic amount summed over "
            "all group members."
        ),
        choices=[
            (
                False,
                _("Do not group interfaces"),
                FixedValue(
                    value={"group_items": []},
                    totext="",
                ),
            ),
            (
                True,
                _("Create the following interface groups"),
                Dictionary(
                    elements=[
                        (
                            "group_items",
                            ListOf(
                                valuespec=Dictionary(
                                    elements=[
                                        (
                                            "group_name",
                                            TextInput(
                                                title=_("Group name"),
                                                help=_("Name of group in service name"),
                                                allow_empty=False,
                                            ),
                                        ),
                                        (
                                            "member_appearance",
                                            _vs_item_appearance(
                                                _("Appearance of group members in service output"),
                                                _(
                                                    "When listing the group members in the output of the service "
                                                    "monitoring the group, this option makes checkmk use either "
                                                    "the interface description, alias or port number."
                                                ),
                                            ),
                                        ),
                                    ],
                                    optional_keys=False,
                                ),
                                title=_("Interface groups"),
                                add_label=_("Add pattern"),
                                allow_empty=False,
                            ),
                        ),
                        (
                            "labels",
                            Labels(
                                world=Labels.World.CONFIG,
                                label_source=Labels.Source.RULESET,
                                help=_(
                                    "Create service labels for all groups "
                                    "that result from this rule."
                                ),
                                title=_("Generate service labels for created groups"),
                            ),
                        ),
                    ],
                    optional_keys=["labels"],
                ),
            ),
        ],
        sorted=False,
    )


def _vs_regex_matching(match_obj):
    return ListOfStrings(
        title=_("Match interface %s (regex)") % match_obj,
        help=_(
            "Apply this rule only to interfaces whose %s matches one of the configured regular "
            "expressions. The match is done on the beginning of the %s."
        )
        % (match_obj, match_obj),
        orientation="horizontal",
        valuespec=RegExp(
            size=32,
            mode=RegExp.prefix,
        ),
    )


def _note_for_admin_state_options():
    return _(
        # xgettext: no-python-format
        "Note: The admin state is in general only available for the 64-bit SNMP interface check. "
        "Additionally, you have to specifically configure Checkmk to fetch this information, "
        "otherwise, using this option will have no effect. To make Checkmk fetch the admin status, "
        "activate the section <tt>if64adm</tt> via the rule "
        "<a href='wato.py?mode=edit_ruleset&varname=snmp_exclude_sections'>Include or exclude SNMP "
        "sections</a>. Note that this will lead to an increase in SNMP traffic of approximately "
        "5%."
    )


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
            "overwritten by rules further up."
        ),
        choices=[
            (
                True,
                _("Match all interfaces"),
                FixedValue(
                    value={},
                    totext="",
                ),
            ),
            (
                False,
                _("Specify matching conditions"),
                Dictionary(
                    elements=[
                        (
                            "porttypes",
                            DualListChoice(
                                title=_("Match port types"),
                                help=_(
                                    "Apply this rule only to interfaces whose port type is listed "
                                    "below."
                                ),
                                choices=ifaceoper.interface_port_types(),
                                rows=40,
                                default_value=[
                                    "6",
                                    "32",
                                    "62",
                                    "117",
                                    "127",
                                    "128",
                                    "129",
                                    "180",
                                    "181",
                                    "182",
                                    "205",
                                    "229",
                                ],
                            ),
                        ),
                        (
                            "portstates",
                            ListChoice(
                                title=_("Match port states"),
                                help=_(
                                    "Apply this rule only to interfaces whose port state is listed "
                                    "below."
                                ),
                                choices=ifaceoper.interface_oper_states(),
                                toggle_all=True,
                                default_value=["1"],
                            ),
                        ),
                        (
                            "admin_states",
                            ListChoice(
                                title=_("Match admin states (SNMP with 64-bit counters only)"),
                                help=(
                                    _(
                                        "Apply this rule only to interfaces whose admin state "
                                        "(<tt>ifAdminStatus</tt>) is listed below."
                                    )
                                    + " "
                                    + _note_for_admin_state_options()
                                ),
                                choices=_admin_states(),
                                toggle_all=True,
                                default_value=["1", "2", "3"],
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
                    ],
                ),
            ),
        ],
        sorted=False,
    )


def _validate_valuespec_inventory_if_rules(value, varprefix):
    if "grouping" not in value and "discovery_single" not in value:
        raise MKUserError(
            varprefix,
            _(
                "Please configure at least either the discovery of single interfaces or the grouping"
            ),
        )


def _valuespec_inventory_if_rules() -> Dictionary:
    return Dictionary(
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
            "error. The reason is that such a rule would have no effect."
        ),
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
        optional_keys=["discovery_single", "grouping"],
        default_keys=["discovery_single"],
        validate=_validate_valuespec_inventory_if_rules,
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupCheckParametersDiscovery,
        match_type="all",
        name="inventory_if_rules",
        valuespec=_valuespec_inventory_if_rules,
    )
)

vs_elements_if_groups_matches: list[DictionaryEntry] = [
    (
        "iftype",
        Transform(
            valuespec=DropdownChoice[int](
                title=_("Select interface port type"),
                choices=ListChoice.dict_choices(ifaceoper.interface_port_types()),
                help=_(
                    "Only interfaces with the given port type are put into this group. "
                    "For example 53 (propVirtual)."
                ),
            ),
            to_valuespec=str,
            from_valuespec=int,
        ),
    ),
    (
        "items",
        ListOfStrings(
            title=_("Restrict interface items"),
            help=_("Only interface with these item names are put into this group."),
        ),
    ),
]

vs_elements_if_groups_group: list[DictionaryEntry] = [
    (
        "group_name",
        TextInput(
            title=_("Group name"),
            help=_("Name of group in service name"),
            allow_empty=False,
        ),
    ),
    (
        "group_presence",
        DropdownChoice[str](
            title=_("Group interface presence"),
            help=_(
                "Determine whether the group interface is created as an "
                "separate service or not. In second case the choosen interface "
                "services disapear."
            ),
            choices=[
                ("separate", _("List grouped interfaces separately")),
                ("instead", _("List grouped interfaces instead")),
            ],
            default_value="instead",
        ),
    ),
]


def _valuespec_if_groups() -> Alternative:
    node_name_elements: list[DictionaryEntry] = [("node_name", TextInput(title=_("Node name")))]
    return Alternative(
        title=_("Network interface groups"),
        help=_(
            "Normally the Interface checks create a single service for interface. "
            "By defining if-group patterns multiple interfaces can be combined together. "
            "A single service is created for this interface group showing the total traffic amount "
            "of its members. You can configure if interfaces which are identified as group interfaces "
            "should not show up as single service. You can restrict grouped interfaces by iftype and the "
            "item name of the single interface."
        ),
        elements=[
            ListOf(
                valuespec=Dictionary(
                    elements=vs_elements_if_groups_group + vs_elements_if_groups_matches,
                    required_keys=["group_name", "group_presence"],
                ),
                title=_("Groups on single host"),
                add_label=_("Add pattern"),
            ),
            ListOf(
                valuespec=Dictionary(
                    elements=vs_elements_if_groups_group
                    + [
                        (
                            "node_patterns",
                            ListOf(
                                title=_("Patterns for each node"),
                                add_label=_("Add pattern"),
                                valuespec=Dictionary(
                                    elements=node_name_elements + vs_elements_if_groups_matches,
                                    required_keys=["node_name"],
                                ),
                                allow_empty=False,
                            ),
                        )
                    ],
                    optional_keys=[],
                ),
                magic="@!!",
                title=_("Groups on cluster"),
                add_label=_("Add pattern"),
            ),
        ],
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupCheckParametersNetworking,
        is_deprecated=True,
        match_type="all",
        name="if_groups",
        valuespec=_valuespec_if_groups,
    )
)


def _help_if_disable_if64_hosts():
    return _(
        "A couple of switches with broken firmware report that they support 64 bit "
        "counters but do not output any actual data in those counters. Listing those "
        "hosts in this rule forces them to use the interface check with 32 bit counters "
        "instead."
    )


rulespec_registry.register(
    BinaryHostRulespec(
        group=RulespecGroupCheckParametersNetworking,
        help_func=_help_if_disable_if64_hosts,
        name="if_disable_if64_hosts",
        title=lambda: _("Hosts forced to use 'if' instead of 'if64'"),
        is_deprecated=True,
    )
)


def _vs_packet_levels(
    title: str | None = None,
    percent_levels: tuple[float, float] = (0.0, 0.0),
    percent_detail: str = "",
    abs_detail: str = "",
) -> CascadingDropdown:
    return CascadingDropdown(
        orientation="horizontal",
        title=title,
        choices=[
            (
                "perc",
                _("Percentual levels") + percent_detail,
                Tuple(
                    orientation="float",
                    show_titles=False,
                    elements=[
                        Percentage(
                            label=_("Warning at"),
                            default_value=percent_levels[0],
                        ),
                        Percentage(
                            label=_("Critical at"),
                            default_value=percent_levels[1],
                        ),
                    ],
                ),
            ),
            (
                "abs",
                _("Absolute levels") + abs_detail,
                Tuple(
                    orientation="float",
                    show_titles=False,
                    elements=[
                        Integer(label=_("Warning at")),
                        Integer(label=_("Critical at")),
                    ],
                ),
            ),
        ],
    )


def _item_spec_if():
    return TextInput(title=_("Port"), allow_empty=False)


PERC_ERROR_LEVELS = (0.01, 0.1)
PERC_DISCARD_LEVELS = (10.0, 20.0)
PERC_PKG_LEVELS = (10.0, 20.0)


def _vs_alternative_levels(
    title: str,
    help: str,
    percent_levels: tuple[float, float] = (0.0, 0.0),
    percent_detail: str = "",
    abs_detail: str = "",
) -> Alternative:
    return Alternative(
        title=title,
        help=help,
        elements=[
            Dictionary(
                title="Provide one set of levels for in and out",
                elements=[
                    (
                        "both",
                        _vs_packet_levels(
                            title="Levels",
                            percent_levels=percent_levels,
                            percent_detail=percent_detail,
                            abs_detail=abs_detail,
                        ),
                    )
                ],
                optional_keys=False,
            ),
            Dictionary(
                title="Provide separate levels for in and out",
                elements=[
                    (
                        "in",
                        _vs_packet_levels(
                            title="In levels",
                            percent_levels=percent_levels,
                            percent_detail=percent_detail,
                            abs_detail=abs_detail,
                        ),
                    ),
                    (
                        "out",
                        _vs_packet_levels(
                            title="Out levels",
                            percent_levels=percent_levels,
                            percent_detail=percent_detail,
                            abs_detail=abs_detail,
                        ),
                    ),
                ],
                optional_keys=False,
            ),
        ],
    )


def _vs_state_mappings() -> CascadingDropdown:
    return CascadingDropdown(
        choices=[
            (
                "independent_mappings",
                _("Map operational and admin state independently"),
                Dictionary(
                    elements=[
                        (
                            "map_operstates",
                            ListOf(
                                valuespec=Tuple(
                                    orientation="horizontal",
                                    elements=[
                                        ListChoice(
                                            choices=ifaceoper.interface_oper_states(),
                                            allow_empty=False,
                                        ),
                                        MonitoringState(),
                                    ],
                                ),
                                title=_("Map operational states"),
                                help=_(
                                    "Map the operational state (<tt>ifOperStatus</tt>) to a monitoring state."
                                ),
                            ),
                        ),
                        (
                            "map_admin_states",
                            ListOf(
                                valuespec=Tuple(
                                    orientation="horizontal",
                                    elements=[
                                        ListChoice(
                                            choices=_admin_states(),
                                            allow_empty=False,
                                        ),
                                        MonitoringState(),
                                    ],
                                ),
                                title=_("Map admin states (SNMP with 64-bit counters only)"),
                                help=(
                                    _(
                                        "Map the admin state (<tt>ifAdminStatus</tt>) to a monitoring state."
                                    )
                                    + " "
                                    + _note_for_admin_state_options()
                                ),
                            ),
                        ),
                    ],
                ),
            ),
            (
                "combined_mappings",
                _("Map combinations of operational and admin state"),
                ListOf(
                    valuespec=Tuple(
                        orientation="horizontal",
                        elements=[
                            DropdownChoice(
                                choices=[
                                    (
                                        str(key),
                                        f"{key} - {value}",
                                    )
                                    for key, value in ifaceoper.interface_oper_states().items()
                                ],
                                title=_("Operational state"),
                            ),
                            DropdownChoice(
                                choices=[
                                    (
                                        str(key),
                                        f"{key} - {value}",
                                    )
                                    for key, value in _admin_states().items()
                                ],
                                title=_("Admin state"),
                            ),
                            MonitoringState(title=_("Monitoring state")),
                        ],
                    ),
                    help=(
                        _(
                            "Map combinations of the operational state (<tt>ifOperStatus</tt>) and the "
                            "admin state (<tt>ifAdminStatus</tt>) to a monitoring state. Here, you can "
                            "for example configure that an interface which is down <i>and</i> admin "
                            "down should be considered OK. Such a setting will only apply to "
                            "interfaces matching the operational <i>and</i> the admin state. For "
                            "example, an interface which is down but admin up would not be affected."
                        )
                        + " "
                        + _note_for_admin_state_options()
                    ),
                ),
            ),
        ],
        title=_("Mapping of operational and admin state to monitoring state"),
        sorted=False,
    )


def _parameter_valuespec_if() -> Dictionary:
    return Dictionary(
        ignored_keys=[
            "aggregate",
            "discovered_oper_status",
            "discovered_admin_status",
            "discovered_speed",
            "item_appearance",
        ],  # Created by discovery
        elements=[
            (
                "errors",
                _vs_alternative_levels(
                    title=_("Levels for error rates"),
                    help=_(
                        "These levels make the check go warning or critical whenever the "
                        "<b>percentual error rate</b> or the <b>absolute error rate</b> of the monitored interface reaches "
                        "the given bounds. The percentual error rate is computed by "
                        "the formula <b>(errors / (unicast + non-unicast + errors))*100</b> "
                    ),
                    percent_levels=PERC_ERROR_LEVELS,
                    percent_detail=_(" (in relation to all packets (successful + error))"),
                    abs_detail=_(" (in errors per second)"),
                ),
            ),
            (
                "speed",
                OptionalDropdownChoice(
                    title=_("Operating speed"),
                    help=_(
                        "If you use this parameter then the check goes warning if the "
                        "interface is not operating at the expected speed (e.g. it "
                        "is working with 100Mbit/s instead of 1Gbit/s.<b>Note:</b> "
                        "some interfaces do not provide speed information. In such cases "
                        "this setting is used as the assumed speed when it comes to "
                        "traffic monitoring (see below)."
                    ),
                    choices=[
                        (None, _("ignore speed")),
                        (10000000, "10 Mbit/s"),
                        (100000000, "100 Mbit/s"),
                        (1000000000, "1 Gbit/s"),
                        (10000000000, "10 Gbit/s"),
                    ],
                    otherlabel=_("specify manually ->"),
                    explicit=Integer(
                        title=_("Other speed in bits per second"),
                        label=_("Bits per second"),
                    ),
                ),
            ),
            (
                "state",
                Optional(
                    valuespec=ListChoice(
                        title=_("Allowed operational states:"),
                        choices=ifaceoper.interface_oper_states(),
                        allow_empty=False,
                    ),
                    title=_("Operational state"),
                    help=_(
                        "If you activate the monitoring of the operational state "
                        "(<tt>ifOperStatus</tt>), the check will go critical if the current "
                        "state of the interface does not match one of the expected states."
                    ),
                    label=_("Ignore the operational state"),
                    none_label=_("ignore"),
                    negate=True,
                ),
            ),
            (
                "admin_state",
                Optional(
                    valuespec=ListChoice(
                        title=_("Allowed admin states:"),
                        choices=_admin_states(),
                        allow_empty=False,
                    ),
                    title=_("Admin state (SNMP with 64-bit counters only)"),
                    help=(
                        _(
                            "If you activate the monitoring of the admin state "
                            "(<tt>ifAdminStatus</tt>), the check will go critical if the "
                            "current state of the interface does not match one of the expected "
                            "states."
                        )
                        + " "
                        + _note_for_admin_state_options()
                    ),
                    label=_("Ignore the admin state"),
                    none_label=_("ignore"),
                    negate=True,
                ),
            ),
            (
                "state_mappings",
                _vs_state_mappings(),
            ),
            (
                "assumed_speed_in",
                OptionalDropdownChoice(
                    title=_("Assumed input speed"),
                    help=_(
                        "If the automatic detection of the link speed does not work "
                        "or the switch's capabilities are throttled because of the network setup "
                        "you can set the assumed speed here."
                    ),
                    choices=[
                        (None, _("ignore speed")),
                        (10000000, "10 Mbit/s"),
                        (100000000, "100 Mbit/s"),
                        (1000000000, "1 Gbit/s"),
                        (10000000000, "10 Gbit/s"),
                    ],
                    otherlabel=_("specify manually ->"),
                    default_value=16000000,
                    explicit=Integer(
                        title=_("Other speed in bits per second"),
                        label=_("Bits per second"),
                        size=12,
                    ),
                ),
            ),
            (
                "assumed_speed_out",
                OptionalDropdownChoice(
                    title=_("Assumed output speed"),
                    help=_(
                        "If the automatic detection of the link speed does not work "
                        "or the switch's capabilities are throttled because of the network setup "
                        "you can set the assumed speed here."
                    ),
                    choices=[
                        (None, _("ignore speed")),
                        (10000000, "10 Mbit/s"),
                        (100000000, "100 Mbit/s"),
                        (1000000000, "1 Gbit/s"),
                        (10000000000, "10 Gbit/s"),
                    ],
                    otherlabel=_("specify manually ->"),
                    default_value=1500000,
                    explicit=Integer(
                        title=_("Other speed in bits per second"),
                        label=_("Bits per second"),
                        size=12,
                    ),
                ),
            ),
            (
                "unit",
                DropdownChoice(
                    title=_("Measurement unit"),
                    help=_("Here you can specifiy the measurement unit of the network interface"),
                    default_value="byte",
                    choices=[
                        ("bit", _("Bits")),
                        ("byte", _("Bytes")),
                    ],
                ),
            ),
            (
                "infotext_format",
                DropdownChoice(
                    title=_("Change infotext in check output"),
                    help=_(
                        "This setting allows you to modify the information text which is displayed between "
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
                    ],
                ),
            ),
            (
                "traffic",
                ListOf(
                    valuespec=CascadingDropdown(
                        title=_("Direction"),
                        orientation="horizontal",
                        choices=[
                            ("both", _("In / Out"), vs_interface_traffic()),
                            ("in", _("In"), vs_interface_traffic()),
                            ("out", _("Out"), vs_interface_traffic()),
                        ],
                    ),
                    title=_("Used bandwidth (minimum or maximum traffic)"),
                    help=_(
                        "Setting levels on the used bandwidth is optional. If you do set "
                        "levels you might also consider using averaging."
                    ),
                ),
            ),
            (
                "total_traffic",
                Dictionary(
                    title=_("Activate total bandwidth metric (sum of in and out)"),
                    help=_(
                        "By activating this item, the sum of incoming and outgoing traffic will "
                        "be monitored via a separate metric. Setting levels on the used total bandwidth "
                        "is optional. If you set levels you might also consider using averaging."
                    ),
                    elements=[
                        (
                            "levels",
                            ListOf(
                                valuespec=vs_interface_traffic(),
                                title=_("Provide levels"),
                                help=_(
                                    "Levels on the total bandwidth will act the same way as they do for "
                                    "in/out bandwidth."
                                ),
                            ),
                        ),
                    ],
                    optional_keys=["levels"],
                ),
            ),
            (
                "average",
                Integer(
                    title=_("Average values for used bandwidth"),
                    help=_(
                        "By activating the computation of averages, the levels on "
                        "traffic and speed are applied to the averaged value. That "
                        "way you can make the check react only on long-time changes, "
                        "not on one-minute events."
                    ),
                    unit=_("minutes"),
                    minvalue=1,
                    default_value=15,
                ),
            ),
            (
                "nucasts",
                Migrate(
                    valuespec=_vs_alternative_levels(
                        title=_("Non-Unicast packet rates"),
                        help=_(
                            "Setting levels on non-unicast packet rates is optional. This may help "
                            "to detect broadcast storms and other unwanted traffic."
                        ),
                        percent_levels=PERC_PKG_LEVELS,
                        percent_detail=_(" (in relation to all successful packets)"),
                        abs_detail=_(" (in packets per second)"),
                    ),
                    migrate=_transform_discards,
                ),
            ),
            (
                "unicast",
                _vs_alternative_levels(
                    title=_("Unicast packet rates"),
                    help=_(
                        "These levels make the check go warning or critical whenever the "
                        "<b>percentual packet rate</b> or the <b>absolute packet "
                        "rate</b> of the monitored interface reaches the given "
                        "bounds. The percentual packet rate is computed by "
                        "the formula <b>(unicast / (unicast + non-unicast))*100</b>"
                    ),
                    percent_levels=PERC_PKG_LEVELS,
                    percent_detail=_(" (in relation to all successful packets)"),
                    abs_detail=_(" (in packets per second)"),
                ),
            ),
            (
                "multicast",
                _vs_alternative_levels(
                    title=_("Multicast packet rates"),
                    help=_(
                        "These levels make the check go warning or critical whenever the "
                        "<b>percentual packet rate</b> or the <b>absolute packet "
                        "rate</b> of the monitored interface reaches the given "
                        "bounds. The percentual packet rate is computed by "
                        "the formula <b>(multicast / (unicast + non-unicast))*100</b>"
                    ),
                    percent_levels=PERC_PKG_LEVELS,
                    percent_detail=_(" (in relation to all successful packets)"),
                    abs_detail=_(" (in packets per second)"),
                ),
            ),
            (
                "broadcast",
                _vs_alternative_levels(
                    title=_("Broadcast packet rates"),
                    help=_(
                        "These levels make the check go warning or critical whenever the "
                        "<b>percentual packet rate</b> or the <b>absolute packet "
                        "rate</b> of the monitored interface reaches the given "
                        "bounds. The percentual packet rate is computed by "
                        "the formula <b>(broadcast / (unicast + non-unicast))*100</b>"
                    ),
                    percent_levels=PERC_PKG_LEVELS,
                    percent_detail=_(" (in relation to all successful packets)"),
                    abs_detail=_(" (in packets per second)"),
                ),
            ),
            (
                "discards",
                Migrate(
                    valuespec=_vs_alternative_levels(
                        title=_("Levels for discards rates"),
                        help=_(
                            "These levels make the check go warning or critical whenever the "
                            "<b>percentual discards rate</b> or the <b>absolute discards rate</b> of the monitored interface reaches "
                            "the given bounds. The percentual discards rate is computed by "
                            "the formula <b>(discards / (unicast + non-unicast + discards))*100</b> "
                        ),
                        percent_levels=PERC_DISCARD_LEVELS,
                        percent_detail=_(" (in relation to all packets (successful + discard))"),
                        abs_detail=_(" (in discards per second)"),
                    ),
                    migrate=_transform_discards,
                ),
            ),
            (
                "average_bm",
                Integer(
                    title=_("Average values for broadcast and multicast packet rates"),
                    help=_(
                        "By activating the computation of averages, the levels on "
                        "broad- and multicast packet rates are applied to "
                        "the averaged value. That way you can make the check react only on long-time "
                        "changes, not on one-minute events."
                    ),
                    unit=_("minutes"),
                    minvalue=1,
                    default_value=15,
                ),
            ),
            (
                "match_same_speed",
                DropdownChoice(
                    title=_("Speed of interface groups (Netapp only)"),
                    help=_(
                        "Choose the behaviour for different interface speeds in "
                        'interface groups. The default is "Check and WARN". This '
                        "feature is currently only supported by the check "
                        "netapp_api_if."
                    ),
                    choices=[
                        ("check_and_warn", _("Check and WARN")),
                        ("check_and_crit", _("Check and CRIT")),
                        ("check_and_display", _("Check and display only")),
                        ("dont_show_and_check", _("Don't show and check")),
                    ],
                ),
            ),
            (
                "home_port",
                DropdownChoice(
                    title=_("Is-Home state (Netapp only)"),
                    help=_(
                        "Choose the behaviour when the current port is not the "
                        "home port of the respective interface. The default is "
                        '"Check and Display". This feature is currently only '
                        "supported by the check netapp_api_if."
                    ),
                    choices=[
                        ("check_and_warn", _("Check and WARN")),
                        ("check_and_crit", _("Check and CRIT")),
                        ("check_and_display", _("Check and display only")),
                        ("dont_show_and_check", _("Don't show home port info")),
                    ],
                ),
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="interfaces",
        group=RulespecGroupCheckParametersNetworking,
        item_spec=_item_spec_if,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_if,
        title=lambda: _("Network interfaces and switch ports"),
    )
)
