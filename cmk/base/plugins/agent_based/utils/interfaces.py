#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections import defaultdict
from dataclasses import (
    asdict,
    dataclass,
)
import time
from typing import (
    Any,
    Dict,
    Iterable,
    List,
    Mapping,
    Optional,
    Sequence,
    Tuple,
    TypedDict,
    Union,
)

from ..agent_based_api.v0 import (
    check_levels,
    check_levels_predictive,
    get_average,
    get_rate,
    get_value_store,
    IgnoreResults,
    IgnoreResultsError,
    Metric,
    regex,
    render,
    Result,
    Service,
    state,
    type_defs,
)


class SingleInterfaceDiscoveryParams(TypedDict):
    item_appearance: str
    pad_portnumbers: bool


MatchingConditions = Dict[str, List[str]]


class DiscoveryParams(TypedDict, total=False):
    discovery_single: Tuple[bool, Union[Mapping, SingleInterfaceDiscoveryParams]]
    grouping: Tuple[bool, Iterable[Mapping[str, str]]]
    matching_conditions: Tuple[bool, MatchingConditions]


DISCOVERY_DEFAULT_PARAMETERS: DiscoveryParams = {
    'matching_conditions': (
        False,
        {
            'porttypes': [
                '6',
                '32',
                '62',
                '117',
                '127',
                '128',
                '129',
                '180',
                '181',
                '182',
                '205',
                '229',
            ],
            'portstates': ['1'],
        },
    ),
    'discovery_single': (
        True,
        {
            'item_appearance': 'index',
            'pad_portnumbers': True,
        },
    ),
}

CHECK_DEFAULT_PARAMETERS = {
    "errors": (0.01, 0.1),
}

discovery_monitor_speed = True
discovery_monitor_state = True


@dataclass
class PreInterface:
    index: Union[str, Tuple[str, str]]
    descr: str
    type: str
    speed: Union[str, float]
    oper_status: Union[str, Tuple[str, str]]
    in_octets: float
    in_ucast: float
    in_mcast: float
    in_bcast: float
    in_discards: float
    in_errors: float
    out_octets: float
    out_ucast: float
    out_mcast: float
    out_bcast: float
    out_discards: float
    out_errors: float
    out_qlen: float
    alias: str
    phys_address: Union[Iterable[int], str]
    oper_status_name: Optional[str] = None
    speed_as_text: str = ''
    group: Optional[str] = None
    node: Optional[str] = None


class Interface(PreInterface):
    index: str
    speed: float
    oper_status: str
    oper_status_name: str


Section = Sequence[Interface]


def saveint(i: Any) -> int:
    try:
        return int(i)
    except (TypeError, ValueError):
        return 0


def finalize_interface(pre_interface: PreInterface) -> Interface:
    # Windows NICs sends pairs of ifOperStatus and its Windows-Name instead
    # of just the ifOperStatus
    if isinstance(pre_interface.oper_status, tuple):
        pre_interface.oper_status, pre_interface.oper_status_name = pre_interface.oper_status
    else:
        pre_interface.oper_status_name = statename(pre_interface.oper_status)

    if isinstance(pre_interface.index, tuple):
        pre_interface.group, pre_interface.index = pre_interface.index

    # Some devices (e.g. NetApp ONTAP) can report "auto" as speed
    if pre_interface.speed == "auto":
        pre_interface.speed_as_text = pre_interface.speed  # type: ignore[assignment]

    # Fix bug in TP Link switches
    pre_interface.speed = saveint(pre_interface.speed)
    if pre_interface.speed > 9 * 1000 * 1000 * 1000 * 1000:
        pre_interface.speed /= 10000

    pre_interface.descr = cleanup_if_strings(pre_interface.descr)
    pre_interface.alias = cleanup_if_strings(pre_interface.alias)

    return Interface(**asdict(pre_interface))


# Remove 0 bytes from strings. They lead to problems e.g. here:
# On windows hosts the labels of network interfaces in oid
# iso.3.6.1.2.1.2.2.1.2.1 are given as hex strings with tailing
# 0 byte. When this string is part of the data which is sent to
# the nagios pipe all chars after the 0 byte are stripped of.
# Stupid fix: Remove all 0 bytes. Hope this causes no problems.
def cleanup_if_strings(s: str) -> str:
    if s and s != '':
        return "".join([c for c in s if c != chr(0)]).strip()
    return s


# This variant of int() lets the string if its not
# convertable. Useful for parsing dict-like things, where
# some of the values are int.
def tryint(x: Any) -> Any:
    try:
        return int(x)
    except (TypeError, ValueError):
        return x


# Name of state (lookup SNMP enum)
def statename(st: str) -> str:
    names = {
        '1': 'up',
        '2': 'down',
        '3': 'testing',
        '4': 'unknown',
        '5': 'dormant',
        '6': 'not present',
        '7': 'lower layer down',
        '8': 'degraded',
        '9': 'admin down',
    }
    return names.get(st, st)


def render_mac_address(phys_address: Union[Iterable[int], str]) -> str:
    if isinstance(phys_address, str):
        mac_bytes = (ord(x) for x in phys_address)
    else:
        mac_bytes = (x for x in phys_address)
    return (":".join(["%02s" % hex(m)[2:] for m in mac_bytes]).replace(' ', '0')).upper()


def item_matches(
    item: str,
    ifIndex: str,
    ifAlias: str,
    ifDescr: str,
) -> bool:
    return item.lstrip("0") == ifIndex \
            or (item == "0" * len(item) and saveint(ifIndex) == 0) \
            or item == ifAlias \
            or item == ifDescr \
            or item == "%s %s" % (ifAlias, ifIndex) \
            or item == "%s %s" % (ifDescr, ifIndex)


# Pads port numbers with zeroes, so that items
# nicely sort alphabetically
def pad_with_zeroes(
    section: Section,
    ifIndex: str,
    pad_portnumbers: bool,
) -> str:
    if pad_portnumbers:
        max_index = max(int(interface.index) for interface in section)
        digits = len(str(max_index))
        return ("%0" + str(digits) + "d") % int(ifIndex)
    return ifIndex


LevelSpec = Tuple[Optional[str], Tuple[Optional[float], Optional[float]]]
GeneralTrafficLevels = Dict[Tuple[str, str], LevelSpec]


def get_traffic_levels(params: type_defs.Parameters) -> GeneralTrafficLevels:
    # Transform old style traffic parameters to new CascadingDropdown based data format
    new_traffic: List[Tuple[str, Tuple[str, LevelSpec]]] = []
    if 'traffic' in params and not isinstance(params['traffic'], list):
        warn, crit = params['traffic']
        if warn is None:
            new_traffic.append(('both', ('upper', (None, (None, None)))))
        elif isinstance(warn, int):
            new_traffic.append(('both', ('upper', ('abs', (warn, crit)))))
        elif isinstance(warn, float):
            new_traffic.append(('both', ('upper', ('perc', (warn, crit)))))

    if 'traffic_minimum' in params:
        warn, crit = params['traffic_minimum']
        if isinstance(warn, int):
            new_traffic.append(('both', ('lower', ('abs', (warn, crit)))))
        elif isinstance(warn, float):
            new_traffic.append(('both', ('lower', ('perc', (warn, crit)))))

    if new_traffic:
        traffic_levels = new_traffic
    else:
        traffic_levels = params.get('traffic', [])

    # Now bring the levels in a structure which is easily usable for the check
    # and also convert direction="both" to single in/out entries
    levels: GeneralTrafficLevels = {
        ('in', 'upper'): (None, (None, None)),
        ('out', 'upper'): (None, (None, None)),
        ('in', 'lower'): (None, (None, None)),
        ('out', 'lower'): (None, (None, None)),
    }
    for level in traffic_levels:
        traffic_dir = level[0]
        up_or_low = level[1][0]
        level_type = level[1][1][0]
        level_value = level[1][1][1]

        if traffic_dir == 'both':
            levels[('in', up_or_low)] = (level_type, level_value)
            levels[('out', up_or_low)] = (level_type, level_value)
        else:
            levels[(traffic_dir, up_or_low)] = (level_type, level_value)

    return levels


SpecificTrafficLevels = Dict[Union[Tuple[str, str], Tuple[str, str, str]], Any]


def get_specific_traffic_levels(
    general_traffic_levels: GeneralTrafficLevels,
    unit: str,
    ref_speed: Optional[float],
    assumed_speed_in: Optional[float],
    assumed_speed_out: Optional[float],
) -> SpecificTrafficLevels:
    traffic_levels: SpecificTrafficLevels = {}
    for (traffic_dir, up_or_low), (level_type, levels) in general_traffic_levels.items():
        if not isinstance(levels, tuple):
            traffic_levels[(traffic_dir, 'predictive')] = levels
            traffic_levels[(traffic_dir, up_or_low, 'warn')] = None
            traffic_levels[(traffic_dir, up_or_low, 'crit')] = None
            continue  # don't convert predictive levels config
        warn, crit = levels

        for what, level_value in [('warn', warn), ('crit', crit)]:
            # If the measurement unit is set to bit and the bw levels
            # are of type absolute, convert these 'bit' entries to byte
            # still reported as bytes to stay compatible with older rrd data
            if unit == 'Bit' and level_type == 'abs':
                assert isinstance(level_value, int)
                level_value = level_value // 8
            elif level_type == 'perc':
                # convert percentages to absolute values. Use either the assumed speed
                # or the reference speed. When none of both are available, ignore
                # the percentual levels
                assert isinstance(level_value, float)
                if traffic_dir == 'in' and assumed_speed_in:
                    level_value = level_value / 100.0 * assumed_speed_in / 8
                elif traffic_dir == 'out' and assumed_speed_out:
                    level_value = level_value / 100.0 * assumed_speed_out / 8
                elif ref_speed:
                    level_value = level_value / 100.0 * ref_speed
                else:
                    level_value = None

            traffic_levels[(traffic_dir, up_or_low, what)] = level_value  # bytes
    return traffic_levels


def _uses_description_and_alias(item_appearance: str) -> Tuple[bool, bool]:
    if item_appearance == 'descr':
        return True, False
    if item_appearance == 'alias':
        return False, True
    return False, False


def _compute_item(
    item_appearance: str,
    interface: Interface,
    section: Section,
    pad_portnumbers: bool,
) -> str:
    uses_description, uses_alias = _uses_description_and_alias(item_appearance)
    if uses_description and interface.descr:
        item = interface.descr
    elif uses_alias and interface.alias:
        item = interface.alias
    else:
        item = pad_with_zeroes(section, interface.index, pad_portnumbers)
    return item


def _check_regex_match_conditions(
    name: str,
    what: Optional[Iterable[str]],
) -> bool:
    if what is None:
        return True
    for r in what:
        if regex(r).match(name):
            return True
    return False


def _check_single_matching_conditions(
    interface: Interface,
    matching_conditions: MatchingConditions,
) -> bool:

    match_index = matching_conditions.get('match_index')
    match_alias = matching_conditions.get('match_alias')
    match_desc = matching_conditions.get('match_desc')
    porttypes = matching_conditions.get('porttypes')
    if porttypes is not None:
        porttypes = porttypes[:]
        porttypes.append("")  # Allow main check to set no port type (e.g. hitachi_hnas_fc_if)
    portstates = matching_conditions.get('portstates')

    return (_check_regex_match_conditions(interface.index, match_index) and
            _check_regex_match_conditions(interface.alias, match_alias) and
            _check_regex_match_conditions(interface.descr, match_desc) and
            (porttypes is None or interface.type in porttypes) and
            (portstates is None or interface.oper_status in portstates))


class GroupConfiguration(TypedDict, total=False):
    member_appearance: str
    inclusion_condition: MatchingConditions
    exclusion_conditions: Iterable[MatchingConditions]


def _check_group_matching_conditions(
    interface: Interface,
    group_name: str,
    group_configuration: GroupConfiguration,
) -> bool:

    # group defined in agent output
    if 'inclusion_condition' not in group_configuration:
        return group_name == interface.group

    # group defined in rules
    return _check_single_matching_conditions(
        interface,
        group_configuration['inclusion_condition'],
    ) and not any(
        _check_single_matching_conditions(
            interface,
            exclusion_condition,
        ) for exclusion_condition in group_configuration['exclusion_conditions'])


class DiscoveredParams(TypedDict, total=False):
    discovered_state: Iterable[str]
    discovered_speed: float
    aggregate: GroupConfiguration


def _transform_discovery_rules(params: type_defs.Parameters) -> DiscoveryParams:

    params_mutable = dict(**params)

    if 'use_alias' in params:
        params_mutable['item_appearance'] = 'alias'
    if 'use_desc' in params:
        params_mutable['item_appearance'] = 'descr'

    params_transformed: DiscoveryParams = {}
    for key in ['discovery_single', 'grouping', 'matching_conditions']:
        if key in params_mutable:
            params_transformed[key] = params_mutable[key]  # type: ignore[misc]

    if 'discovery_single' not in params_transformed:
        single_interface_discovery_settings = {}
        for key in ["item_appearance", "pad_portnumbers"]:
            if key in params_mutable:
                single_interface_discovery_settings[key] = params_mutable[key]
        if single_interface_discovery_settings:
            single_interface_discovery_settings.setdefault("item_appearance", "index")
            single_interface_discovery_settings.setdefault("pad_portnumbers", True)
            params_transformed['discovery_single'] = (True, single_interface_discovery_settings)

    if 'matching_conditions' not in params_transformed:
        params_transformed['matching_conditions'] = (True, {})
    for key in ['match_alias', 'match_desc', 'portstates', 'porttypes']:
        if key in params_mutable:
            params_transformed['matching_conditions'][1][key] = params_mutable[key]
            params_transformed['matching_conditions'] = (
                False, params_transformed['matching_conditions'][1])

    return params_transformed


def _groups_from_params(
        discovery_params: Sequence[DiscoveryParams]) -> Dict[str, GroupConfiguration]:
    groups: Dict[str, GroupConfiguration] = {}
    inclusion_importances = {}
    exclusion_conditions = []

    # First, we find all defined groups. If multiple groups with the same name are defined, the one
    # from the most specific rule wins (the one highest up in the hierarchy). We also gather all
    # exclusion conditions (setting 'Do not group interfaces').
    for rule_importance, rule in enumerate(discovery_params[::-1]):
        create_groups, group_configs = rule.get('grouping', (True, []))
        if create_groups:
            for group_config in group_configs:
                groups[group_config['group_name']] = {
                    'member_appearance': group_config['member_appearance'],
                    'inclusion_condition': rule['matching_conditions'][1],
                }
                inclusion_importances[group_config['group_name']] = rule_importance
        else:
            exclusion_conditions.append((rule['matching_conditions'][1], rule_importance))

    # Second, we add the exclusion conditions to the found groups. For each group, we only store
    # those exclusion conditions which are higher up in the hierarchy than the inclusion condition.
    for group_name, group_configuration in groups.items():
        group_configuration['exclusion_conditions'] = [
            exclusion_condition
            for exclusion_condition, exclusion_importance in exclusion_conditions
            if exclusion_importance > inclusion_importances[group_name]
        ]

    return groups


def discover_interfaces(
    params: Sequence[type_defs.Parameters],
    section: Section,
) -> type_defs.DiscoveryGenerator:
    if len(section) == 0:
        return

    rulesets = [_transform_discovery_rules(par) for par in params]

    pre_inventory = []
    n_times_item_seen: Dict[str, int] = defaultdict(int)
    interface_groups: Dict[str, GroupConfiguration] = {}

    # ==============================================================================================
    # SINGLE-INTERFACE DISCOVERY
    # ==============================================================================================
    for interface in section:
        discover_single_interface = False
        single_interface_settings = DISCOVERY_DEFAULT_PARAMETERS['discovery_single'][1]
        # find the most specific rule which applies to this interface and which has single-interface
        # discovery settings
        for ruleset in rulesets:
            if 'discovery_single' in ruleset and _check_single_matching_conditions(
                    interface,
                    ruleset['matching_conditions'][1],
            ):
                discover_single_interface, single_interface_settings = ruleset['discovery_single']
                break

        # compute item now - also for unmonitored ports - in order to see if it is unique.
        item = _compute_item(
            single_interface_settings.get(
                'item_appearance',
                DISCOVERY_DEFAULT_PARAMETERS['discovery_single'][1]['item_appearance'],
            ),
            interface,
            section,
            single_interface_settings.get(
                'pad_portnumbers',
                DISCOVERY_DEFAULT_PARAMETERS['discovery_single'][1]['pad_portnumbers'],
            ),
        )
        n_times_item_seen[item] += 1

        # discover single interface
        if discover_single_interface:
            discovered_params_single: DiscoveredParams = {}
            if discovery_monitor_state:
                discovered_params_single["discovered_state"] = [interface.oper_status]

            if discovery_monitor_speed:
                discovered_params_single["discovered_speed"] = interface.speed

            try:
                index_as_item = int(item) == int(interface.index)
            except (TypeError, ValueError):
                index_as_item = False

            pre_inventory.append(
                (item, discovered_params_single, int(interface.index), index_as_item))

        # special case: the agent output already set this interface to grouped, in this case, we do
        # not use any matching conditions but instead check if interface.group == group_name, see
        # below
        if interface.group:
            interface_groups.setdefault(interface.group, {
                "member_appearance": single_interface_settings.get(
                    'item_appearance',
                    'index',
                ),
            })

    # ==============================================================================================
    # GROUPING
    # ==============================================================================================
    interface_groups.update(_groups_from_params(rulesets))
    for group_name, group_configuration in interface_groups.items():
        groups_has_members = False
        group_oper_status = "2"  # operation status, default is down (2)
        group_speed = 0.  # total maximum speed of all interfaces in this group

        # find all interfaces matching the group to compute state and speed
        for interface in section:
            if _check_group_matching_conditions(
                    interface,
                    group_name,
                    group_configuration,
            ):
                groups_has_members = True
                # if at least one is up (1) then up is considered as valid
                group_oper_status = "1" if interface.oper_status == "1" else group_oper_status
                group_speed += interface.speed

        # only discover non-empty groups
        if groups_has_members:
            discovered_params_group: DiscoveredParams = {
                "aggregate": group_configuration,
            }

            if discovery_monitor_state:
                discovered_params_group["discovered_state"] = [group_oper_status]
            if discovery_monitor_speed:
                discovered_params_group["discovered_speed"] = group_speed

            # Note: the group interface index is always set to 1
            pre_inventory.append((group_name, discovered_params_group, 1, False))

    # Check for duplicate items (e.g. when using Alias as item and the alias is not unique)
    for item, discovered_params, index, index_as_item in pre_inventory:
        if not index_as_item and n_times_item_seen[item] > 1:
            new_item = "%s %d" % (item, index)
        else:
            new_item = item
        yield Service(
            item=new_item,
            parameters=dict(discovered_params),
        )


def _get_value_store_key(
    name: str,
    *add_to_key: str,
) -> str:
    key = name
    for to_add in add_to_key:
        key += ".%s" % to_add
    return key


GroupMembers = Dict[Optional[str], List[Dict[str, Optional[str]]]]


def _check_ungrouped_ifs(
    item: str,
    params: type_defs.Parameters,
    section: Section,
    timestamp: float,
) -> type_defs.CheckGenerator:
    """
    Check one or more ungrouped interfaces. In a non-cluster setup, only one interface will match
    the item and the results will simply be the output of check_single_interface. On a cluster,
    multiple interfaces can match. In this case, only the results from the interface with the
    highest outgoing traffic will be reported (since the corresponding node is likely the master).
    """
    last_results = None
    results_from_fastest_interface = None
    max_out_traffic = -1.
    ignore_res_error = None

    for interface in section:
        if item_matches(item, interface.index, interface.alias, interface.descr):
            try:
                last_results = list(
                    check_single_interface(
                        item,
                        params,
                        interface,
                        timestamp=timestamp,
                    ))
            except IgnoreResultsError as excpt:
                ignore_res_error = excpt
                continue
            for result in last_results:
                if isinstance(
                        result,
                        Metric,
                ) and result.name == 'out' and result.value > max_out_traffic:
                    max_out_traffic = result.value
                    results_from_fastest_interface = last_results

    if results_from_fastest_interface is not None:
        yield from results_from_fastest_interface
    # in case there were results, but they did not contain the metric for outgoing traffic, we
    # simply report the last result
    elif last_results is not None:
        yield from last_results
    elif ignore_res_error:
        raise ignore_res_error


def _check_grouped_ifs(
    item: str,
    params: type_defs.Parameters,
    section: Section,
    group_name: str,
    timestamp: float,
) -> type_defs.CheckGenerator:
    """
    Grouped interfaces are combined into a single interface, which is then passed to
    check_single_interface.
    """

    group_members: GroupMembers = {}
    matching_interfaces = []

    for interface in section:
        if_member_item = _compute_item(
            params["aggregate"]["member_appearance"],
            interface,
            section,
            item[0] == '0',
        )

        if _check_group_matching_conditions(
                interface,
                item,
                params['aggregate'],
        ):
            matching_interfaces.append((if_member_item, interface))

    # Now we're done and have all matching interfaces
    # Accumulate info over matching_interfaces
    value_store = get_value_store()

    cumulated_interface = Interface(
        index=item,
        descr=item,
        type="",
        speed=0,
        oper_status="",
        in_octets=0,
        in_ucast=0,
        in_mcast=0,
        in_bcast=0,
        in_discards=0,
        in_errors=0,
        out_octets=0,
        out_ucast=0,
        out_mcast=0,
        out_bcast=0,
        out_discards=0,
        out_errors=0,
        out_qlen=0,
        alias="",
        phys_address="",
    )

    num_up = 0
    nodes = set()
    for idx, (if_member_item, interface) in enumerate(matching_interfaces):
        nodes.add(str(interface.node))
        is_up = interface.oper_status == '1'
        if is_up:
            num_up += 1

        group_members.setdefault(interface.node, [])
        group_members[interface.node].append({
            "name": if_member_item,
            "state": interface.oper_status,
            "state_name": interface.oper_status_name,
        })

        # Only these values are packed into counters
        # We might need to enlarge this table
        # However, more values leads to more MKCounterWrapped...
        for name, counter in [
            ("in", interface.in_octets),
            ("inucast", interface.in_ucast),
            ("inmcast", interface.in_mcast),
            ("inbcast", interface.in_bcast),
            ("indisc", interface.in_discards),
            ("inerr", interface.in_errors),
            ("out", interface.out_octets),
            ("outucast", interface.out_ucast),
            ("outmcast", interface.out_mcast),
            ("outbcast", interface.out_bcast),
            ("outdisc", interface.out_discards),
            ("outerr", interface.out_errors),
        ]:
            try:
                get_rate(
                    value_store,
                    _get_value_store_key(name, str(interface.node), str(idx)),
                    timestamp,
                    saveint(counter),
                    raise_overflow=True,
                )
            except IgnoreResultsError:
                yield IgnoreResults(value='Initializing counters')
                # continue, other counters might wrap as well

        # Add interface info to group info
        if is_up:
            cumulated_interface.speed += interface.speed
        cumulated_interface.in_octets += interface.in_octets
        cumulated_interface.in_ucast += interface.in_ucast
        cumulated_interface.in_mcast += interface.in_mcast
        cumulated_interface.in_bcast += interface.in_bcast
        cumulated_interface.in_discards += interface.in_discards
        cumulated_interface.in_errors += interface.in_errors
        cumulated_interface.out_octets += interface.out_octets
        cumulated_interface.out_ucast += interface.out_ucast
        cumulated_interface.out_mcast += interface.out_mcast
        cumulated_interface.out_bcast += interface.out_bcast
        cumulated_interface.out_discards += interface.out_discards
        cumulated_interface.out_errors += interface.out_errors
        cumulated_interface.out_qlen += interface.out_qlen
        # This is the fallback ifType if None is set in the parameters
        cumulated_interface.type = interface.type

    if num_up == len(matching_interfaces):
        cumulated_interface.oper_status = "1"  # up
    elif num_up > 0:
        cumulated_interface.oper_status = "8"  # degraded
    else:
        cumulated_interface.oper_status = "2"  # down

    alias_info = []
    if len(nodes) > 1:
        alias_info.append('nodes: %s' % ', '.join(nodes))

    attrs = params["aggregate"]
    if attrs.get("iftype"):
        alias_info.append('type: %s' % attrs["iftype"])
    if attrs.get("items"):
        alias_info.append("%d grouped interfaces" % len(matching_interfaces))

    cumulated_interface.alias = ', '.join(alias_info)

    yield from check_single_interface(
        item,
        params,
        finalize_interface(cumulated_interface),
        group_members=group_members,
        group_name=group_name,
        timestamp=timestamp,
        # the discovered speed corresponds to only one of the nodes, so it cannot be used for
        # interface groups on clusters; same for state
        use_discovered_state_and_speed=section[0].node is None,
    )


def check_multiple_interfaces(
    item: str,
    params: type_defs.Parameters,
    section: Section,
    group_name: str = "Group",
    timestamp: Optional[float] = None,
) -> type_defs.CheckGenerator:

    if timestamp is None:
        timestamp = time.time()

    if 'aggregate' in params:
        yield from _check_grouped_ifs(
            item,
            params,
            section,
            group_name,
            timestamp,
        )
    else:
        yield from _check_ungrouped_ifs(
            item,
            params,
            section,
            timestamp,
        )


def _get_rate(
    value_store: type_defs.ValueStore,
    key: str,
    timestamp: float,
    value: float,
    input_is_rate: bool,
) -> float:
    if input_is_rate:
        return value
    return get_rate(
        value_store,
        key,
        timestamp,
        value,
        raise_overflow=True,
    )


def _get_map_operstates(
        defined_mapping: Iterable[Tuple[Iterable[str], int]]) -> Mapping[str, state]:
    map_operstates = {}
    for oper_states, mon_state in defined_mapping:
        for oper_state in oper_states:
            map_operstates[oper_state] = state(mon_state)
    return map_operstates


# TODO: Check what the relationship between Errors, Discards, and ucast/mcast actually is.
# One case of winperf_if appeared to indicate that in that case Errors = Discards.
def check_single_interface(
    item: str,
    params: type_defs.Parameters,
    interface: Interface,
    group_members: Optional[GroupMembers] = None,
    group_name: str = "Group",
    timestamp: Optional[float] = None,
    input_is_rate: bool = False,
    use_discovered_state_and_speed: bool = True,
) -> type_defs.CheckGenerator:

    if timestamp is None:
        timestamp = time.time()
    value_store = get_value_store()

    # Params now must be a dict. Some keys might
    # be set to None
    if use_discovered_state_and_speed:
        targetspeed = params.get("speed", params.get("discovered_speed"))
        targetstates = params.get("state", params.get("discovered_state"))
    else:
        targetspeed = params.get("speed")
        targetstates = params.get("state")
    assumed_speed_in = params.get("assumed_speed_in")
    assumed_speed_out = params.get("assumed_speed_out")
    map_operstates = _get_map_operstates(params.get("map_operstates", []))
    average = params.get("average")
    unit = "Bit" if params.get("unit") in ["Bit", "bit"] else "B"
    average_bmcast = params.get("average_bm")

    # error checking might be turned off
    err_warn, err_crit = params.get("errors", (None, None))
    err_in_warn, err_in_crit = params.get("errors_in", (err_warn, err_crit))
    err_out_warn, err_out_crit = params.get("errors_out", (err_warn, err_crit))

    # broadcast storm detection is turned off by default
    nucast_warn, nucast_crit = params.get("nucasts", (None, None))
    disc_warn, disc_crit = params.get("discards", (None, None))
    mcast_warn, mcast_crit = params.get("multicast", (None, None))
    bcast_warn, bcast_crit = params.get("broadcast", (None, None))

    # Convert the traffic related levels to a common format
    general_traffic_levels = get_traffic_levels(params)

    if group_members:
        # The detailed group info is added later on
        info_interface = group_name + " Status "
    else:
        if "infotext_format" in params:
            bracket_info = ""
            if params["infotext_format"] == "alias":
                bracket_info = interface.alias
            elif params["infotext_format"] == "description":
                bracket_info = interface.descr
            elif params["infotext_format"] == "alias_and_description":
                bracket_info = ", ".join([i for i in [interface.alias, interface.descr] if i])
            elif params["infotext_format"] == "alias_or_description":
                bracket_info = interface.alias if interface.alias else interface.descr
            elif params["infotext_format"] == "desription_or_alias":
                bracket_info = interface.descr if interface.descr else interface.alias

            if bracket_info:
                info_interface = "[%s]" % bracket_info
            else:
                info_interface = ""
        else:
            # Display port number or alias in summary_interface if that is not part
            # of the service description anyway
            if item.lstrip("0") == interface.index \
                and (item == interface.alias or interface.alias == '') \
                and (item == interface.descr or interface.descr == ''):  # description trivial
                info_interface = ""
            elif item == "%s %s" % (interface.alias,
                                    interface.index) and interface.descr != '':  # non-unique Alias
                info_interface = "[%s/%s]" % (interface.alias, interface.descr)
            elif item != interface.alias and interface.alias != '':  # alias useful
                info_interface = "[%s]" % interface.alias
            elif item != interface.descr and interface.descr != '':  # description useful
                info_interface = "[%s]" % interface.descr
            else:
                info_interface = "[%s]" % interface.index

        if info_interface:
            info_interface += " "
        if interface.node is not None:
            info_interface = "%son %s: " % (
                info_interface,
                interface.node,
            )

    mon_state = state.OK
    info_interface += "(%s)" % interface.oper_status_name
    if targetstates and (interface.oper_status != targetstates and
                         not (isinstance(targetstates,
                                         (list, tuple)) and interface.oper_status in targetstates)):
        mon_state = state.CRIT

    if map_operstates and interface.oper_status in map_operstates:
        mon_state = map_operstates[interface.oper_status]

    yield Result(
        state=mon_state,
        summary=info_interface,
    )

    if group_members:
        infos_group = []
        for group_node, members in group_members.items():
            member_info = []
            for member in members:
                member_info.append("%s (%s)" % (member["name"], member["state_name"]))

            nodeinfo = ""
            if group_node is not None and len(group_members) > 1:
                nodeinfo = " on node %s" % group_node
            infos_group.append("[%s%s]" % (", ".join(member_info), nodeinfo))

        yield Result(
            state=state.OK,
            summary='Members: %s' % ' '.join(infos_group),
        )

    if interface.phys_address:
        yield Result(
            state=state.OK,
            summary='MAC: %s' % render_mac_address(interface.phys_address),
        )

    # prepare reference speed for computing relative bandwidth usage
    speed = int(interface.speed)
    ref_speed = None
    if speed:
        ref_speed = speed / 8.0
    elif targetspeed:
        ref_speed = targetspeed / 8.0

    # Check speed settings of interface, but only if speed information
    # is available. This is not always the case.
    mon_state = state.OK
    if speed:
        info_speed = render.nicspeed(speed / 8)
        if targetspeed is not None and speed != targetspeed:
            info_speed += " (wrong speed, expected: %s)" % render.nicspeed(targetspeed / 8)
            mon_state = state.WARN
    elif targetspeed:
        info_speed = "assuming %s" % render.nicspeed(targetspeed / 8)
    elif interface.speed_as_text:
        info_speed = "speed %s" % interface.speed_as_text
    else:
        info_speed = "speed unknown"

    yield Result(
        state=mon_state,
        summary=info_speed,
    )

    # Convert the traffic levels to interface specific levels, for example where the percentage
    # levels are converted to absolute levels or assumed speeds of an interface are treated correctly
    traffic_levels = get_specific_traffic_levels(general_traffic_levels, unit, ref_speed,
                                                 assumed_speed_in, assumed_speed_out)

    # Speed in bytes
    speed_b_in = (assumed_speed_in // 8) if assumed_speed_in else ref_speed
    speed_b_out = (assumed_speed_out // 8) if assumed_speed_out else ref_speed

    #
    # All internal values within this check after this point are bytes, not bits!
    #

    # When the interface is reported as down, there is no need to try to handle,
    # the performance counters. Most devices do reset the counter values to zero,
    # but we spotted devices, which do report error packes even for down interfaces.
    # To deal with it, we simply skip over all performance counter checks for down
    # interfaces.
    if str(interface.oper_status) == "2":
        return

    # Performance counters
    rates = []
    caught_ignore_results_error = False
    metrics = []
    for name, counter, warn, crit, mmin, mmax in [
        ("in", interface.in_octets, traffic_levels[('in', 'upper', 'warn')],
         traffic_levels[('in', 'upper', 'crit')], 0, speed_b_in),
        ("inmcast", interface.in_mcast, mcast_warn, mcast_crit, None, None),
        ("inbcast", interface.in_bcast, bcast_warn, bcast_crit, None, None),
        ("inucast", interface.in_ucast, None, None, None, None),
        ("innucast", saveint(interface.in_mcast) + saveint(interface.in_bcast), nucast_warn,
         nucast_crit, None, None),
        ("indisc", interface.in_discards, disc_warn, disc_crit, None, None),
        ("inerr", interface.in_errors, err_in_warn, err_in_crit, None, None),
        ("out", interface.out_octets, traffic_levels[('out', 'upper', 'warn')],
         traffic_levels[('out', 'upper', 'crit')], 0, speed_b_out),
        ("outmcast", interface.out_mcast, mcast_warn, mcast_crit, None, None),
        ("outbcast", interface.out_bcast, bcast_warn, bcast_crit, None, None),
        ("outucast", interface.out_ucast, None, None, None, None),
        ("outnucast", saveint(interface.out_mcast) + saveint(interface.out_bcast), nucast_warn,
         nucast_crit, None, None),
        ("outdisc", interface.out_discards, disc_warn, disc_crit, None, None),
        ("outerr", interface.out_errors, err_out_warn, err_out_crit, None, None),
    ]:
        try:
            rate = _get_rate(
                value_store,
                _get_value_store_key(name, str(interface.node)),
                timestamp,
                counter,
                input_is_rate,
            )
            rates.append(rate)
            metrics.append(Metric(
                name,
                rate,
                levels=(warn, crit),
                boundaries=(mmin, mmax),
            ))
        except IgnoreResultsError:
            caught_ignore_results_error = True
            # continue, other counters might wrap as well

    # if at least one counter wrapped, we do not handle the counters at all
    if caught_ignore_results_error:
        # If there is a threshold on the bandwidth, we cannot proceed
        # further (the check would be flapping to green on a wrap)
        if any(traffic_levels.values()):
            raise IgnoreResultsError("Initializing counters")
        return

    yield from metrics
    yield Metric(
        'outqlen',
        interface.out_qlen,
    )

    if unit == 'Bit':
        bandwidth_renderer = lambda v: render.nicspeed(v * 8)
    else:
        bandwidth_renderer = render.iobandwidth

    # loop over incoming and outgoing traffic
    for what, traffic, mrate, brate, urate, nurate, discrate, errorrate, speed in [
        ("in", rates[0], rates[1], rates[2], rates[3], rates[4], rates[5], rates[6], speed_b_in),
        ("out", rates[7], rates[8], rates[9], rates[10], rates[11], rates[12], rates[13],
         speed_b_out)
    ]:
        if (what, 'predictive') in traffic_levels:
            levels_predictive = traffic_levels[(what, 'predictive')]
            bw_warn, bw_crit = None, None
            predictive = True
        else:
            bw_warn = traffic_levels[(what, 'upper', 'warn')]
            bw_crit = traffic_levels[(what, 'upper', 'crit')]
            bw_warn_min = traffic_levels[(what, 'lower', 'warn')]
            bw_crit_min = traffic_levels[(what, 'lower', 'crit')]
            levels_uppper = bw_warn, bw_crit
            levels_lower = bw_warn_min, bw_crit_min
            predictive = False

        # handle computation of average
        if average:
            traffic = get_average(
                value_store,
                "%s.%s.avg" % (what, item),
                timestamp,
                traffic,
                average,
            )  # apply levels to average traffic
            dsname = "%s_avg_%d" % (what, average)
            title = "%s average %dmin" % (what.title(), average)
            yield Metric(
                dsname,
                traffic,
                levels=(bw_warn, bw_crit),
                boundaries=(0, speed),
            )
        else:
            dsname = what
            title = what.title()

        # Check bandwidth thresholds incl. prediction
        if predictive:
            result = list(
                check_levels_predictive(
                    traffic,
                    levels=levels_predictive,
                    metric_name=dsname,
                    render_func=bandwidth_renderer,
                    label=title,
                ))
            if len(result) == 3:
                yield result[2]  # reference curve for predictive levels
        else:
            result = list(
                check_levels(
                    traffic,
                    levels_upper=levels_uppper,
                    levels_lower=levels_lower,
                    metric_name=dsname,
                    render_func=bandwidth_renderer,
                    label=title,
                ))
        next_result = result[0]

        if speed:
            perc_used = 100.0 * traffic / speed
            assumed_info = ""
            if assumed_speed_in or assumed_speed_out:
                assumed_info = "/" + bandwidth_renderer(speed)
            assert isinstance(next_result, Result)
            next_result = Result(
                state=next_result.state,
                summary=next_result.summary + " (%.1f%%%s)" % (perc_used, assumed_info),
            )

        yield next_result

        # check error, broadcast, multicast and non-unicast packets and discards
        pacrate = urate + nurate + errorrate
        if pacrate > 0.0:  # any packets transmitted?
            for value, params_warn, params_crit, text in [
                (errorrate, err_warn, err_crit, "errors"),
                (mrate, mcast_warn, mcast_crit, "multicast"),
                (brate, bcast_warn, bcast_crit, "broadcast"),
            ]:

                calc_avg = False

                infotxt = "%s-%s" % (what, text)
                if average_bmcast is not None and text != "errors":
                    calc_avg = True
                    value = get_average(
                        value_store,
                        "%s.%s.%s.avg" % (what, text, item),
                        timestamp,
                        value,
                        average_bmcast,
                    )

                perc_value = 100.0 * value / pacrate
                if perc_value > 0:
                    if isinstance(params_crit, float):  # percentual levels
                        if calc_avg:
                            assert average_bmcast is not None
                            infotxt += " average %dmin" % average_bmcast
                        yield from check_levels(
                            perc_value,
                            levels_upper=(params_warn, params_crit),
                            metric_name=dsname if text == "errors" else text,
                            render_func=render.percent,
                            label=infotxt,
                        )
                    elif isinstance(params_crit, int):  # absolute levels
                        infotxt += " packets"
                        if calc_avg:
                            assert average_bmcast is not None
                            infotxt += " average %dmin" % average_bmcast
                        yield from check_levels(
                            perc_value,
                            levels_upper=(params_warn, params_crit),
                            metric_name=dsname,
                            render_func=lambda x: "%d" % x,
                            label=infotxt,
                        )

        for _txt, _rate, _warn, _crit in [("non-unicast packets", nurate, nucast_warn, nucast_crit),
                                          ("discards", discrate, disc_warn, disc_crit)]:

            if _crit is not None and _warn is not None:
                yield from check_levels(
                    _rate,
                    levels_upper=(_warn, _crit),
                    metric_name=_txt,
                    render_func=lambda x: "%.2f/s" % x,
                    label="%s %s" % (what, _txt),
                )
