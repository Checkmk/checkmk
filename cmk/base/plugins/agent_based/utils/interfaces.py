#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import time
from collections import defaultdict
from dataclasses import asdict, dataclass
from functools import partial
from typing import (
    Any,
    Callable,
    Collection,
    Container,
    Dict,
    Iterable,
    List,
    Literal,
    Mapping,
    MutableMapping,
    Optional,
    Sequence,
    Set,
    Tuple,
    TypedDict,
    Union,
)

from ..agent_based_api.v1 import (
    check_levels,
    check_levels_predictive,
    get_average,
    get_rate,
    get_value_store,
    GetRateError,
    IgnoreResults,
    Metric,
    regex,
    render,
    Result,
    Service,
    ServiceLabel,
    State,
    type_defs,
)

ServiceLabels = Dict[str, str]


class SingleInterfaceDiscoveryParams(TypedDict, total=False):
    item_appearance: str
    pad_portnumbers: bool
    labels: ServiceLabels


MatchingConditions = Mapping[str, List[str]]


class DiscoveryDefaultParams(TypedDict, total=False):
    discovery_single: Tuple[bool, SingleInterfaceDiscoveryParams]
    matching_conditions: Tuple[bool, MatchingConditions]


DISCOVERY_DEFAULT_PARAMETERS: DiscoveryDefaultParams = {
    "matching_conditions": (
        False,
        {
            "porttypes": [
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
            "portstates": ["1"],
        },
    ),
    "discovery_single": (
        True,
        {
            "item_appearance": "index",
            "pad_portnumbers": True,
        },
    ),
}

CHECK_DEFAULT_PARAMETERS = {
    "errors": {
        "both": ("perc", (0.01, 0.1)),
    },
}


@dataclass
class Attributes:
    index: str
    descr: str
    alias: str
    type: str
    speed: float = 0
    oper_status: str = ""
    out_qlen: float = 0
    phys_address: Union[Iterable[int], str] = ""
    oper_status_name: str = ""
    speed_as_text: str = ""
    group: Optional[str] = None
    node: Optional[str] = None
    admin_status: Optional[str] = None
    extra_info: Optional[str] = None

    def __post_init__(self) -> None:
        self.finalize()

    def finalize(self) -> None:
        if not self.oper_status_name:
            self.oper_status_name = statename(self.oper_status)

        # Fix bug in TP Link switches
        if self.speed > 9 * 1000 * 1000 * 1000 * 1000:
            self.speed /= 10000

        self.descr = cleanup_if_strings(self.descr)
        self.alias = cleanup_if_strings(self.alias)

    @property
    def oper_status_up(self) -> str:
        return "1"

    @property
    def is_up(self) -> bool:
        return self.oper_status == self.oper_status_up

    @property
    def id_for_value_store(self) -> str:
        return f"{self.index}.{self.descr}.{self.alias}.{self.node}"


@dataclass
class Counters:
    in_octets: float = 0
    in_mcast: float = 0
    in_bcast: float = 0
    in_ucast: float = 0
    in_disc: float = 0
    in_err: float = 0
    out_octets: float = 0
    out_mcast: float = 0
    out_bcast: float = 0
    out_ucast: float = 0
    out_disc: float = 0
    out_err: float = 0


@dataclass
class InterfaceWithCounters:
    attributes: Attributes
    counters: Counters


@dataclass(frozen=True)
class _Rates:
    intraffic: float | None
    inmcast: float | None
    inbcast: float | None
    inucast: float | None
    indisc: float | None
    inerr: float | None
    outtraffic: float | None
    outmcast: float | None
    outbcast: float | None
    outucast: float | None
    outdisc: float | None
    outerr: float | None


@dataclass(frozen=True)
class Rates:
    in_octets: float | None = None
    in_mcast: float | None = None
    in_bcast: float | None = None
    in_ucast: float | None = None
    in_disc: float | None = None
    in_err: float | None = None
    out_octets: float | None = None
    out_mcast: float | None = None
    out_bcast: float | None = None
    out_ucast: float | None = None
    out_disc: float | None = None
    out_err: float | None = None


@dataclass
class InterfaceWithRates:
    attributes: Attributes
    rates: Rates
    get_rate_errors: Sequence[tuple[str, GetRateError]]

    @classmethod
    def from_interface_with_counters(
        cls,
        iface_counters: InterfaceWithCounters,
        *,
        timestamp: float,
        value_store: MutableMapping[str, Any],
    ) -> "InterfaceWithRates":
        return cls(
            iface_counters.attributes,
            *cls._compute_rates(
                iface_counters,
                timestamp=timestamp,
                value_store=value_store,
            ),
        )

    @classmethod
    def _compute_rates(
        cls,
        iface_counters: InterfaceWithCounters,
        *,
        timestamp: float,
        value_store: MutableMapping[str, Any],
    ) -> tuple[Rates, Sequence[tuple[str, GetRateError]]]:
        rates: MutableMapping[str, float | None] = {}
        rate_errors = []
        for rate_name, counter_value in (
            ("in_octets", (counters := iface_counters.counters).in_octets),
            ("in_ucast", counters.in_ucast),
            ("in_mcast", counters.in_mcast),
            ("in_bcast", counters.in_bcast),
            ("in_disc", counters.in_disc),
            ("in_err", counters.in_err),
            ("out_octets", counters.out_octets),
            ("out_ucast", counters.out_ucast),
            ("out_mcast", counters.out_mcast),
            ("out_bcast", counters.out_bcast),
            ("out_disc", counters.out_disc),
            ("out_err", counters.out_err),
        ):
            try:
                rates[rate_name] = get_rate(
                    value_store=value_store,
                    key=f"{rate_name}.{iface_counters.attributes.id_for_value_store}",
                    time=timestamp,
                    value=counter_value,
                    raise_overflow=True,
                )
            except GetRateError as get_rate_error:
                rates[rate_name] = None
                rate_errors.append((rate_name, get_rate_error))
        return Rates(**rates), rate_errors


@dataclass(frozen=True)
class Average:
    value: float
    backlog: int

    def __add__(self, other: "Average") -> "Average":
        if self.backlog == other.backlog:
            return Average(
                value=self.value + other.value,
                backlog=self.backlog,
            )
        raise ValueError("Attempting to add two averages with different backlogs")


@dataclass(frozen=True)
class RateWithAverage:
    rate: float
    average: Average | None

    def __add__(self, other: "RateWithAverage") -> "RateWithAverage":
        return RateWithAverage(
            rate=self.rate + other.rate,
            average=self.average + other.average
            if (self.average is not None and other.average is not None)
            else None,
        )


@dataclass(frozen=True)
class RatesWithAverages:
    in_octets: RateWithAverage | None = None
    in_mcast: RateWithAverage | None = None
    in_bcast: RateWithAverage | None = None
    in_nucast: RateWithAverage | None = None
    in_ucast: RateWithAverage | None = None
    in_disc: RateWithAverage | None = None
    in_err: RateWithAverage | None = None
    out_octets: RateWithAverage | None = None
    out_mcast: RateWithAverage | None = None
    out_bcast: RateWithAverage | None = None
    out_nucast: RateWithAverage | None = None
    out_ucast: RateWithAverage | None = None
    out_disc: RateWithAverage | None = None
    out_err: RateWithAverage | None = None
    total_octets: RateWithAverage | None = None


@dataclass
class InterfaceWithRatesAndAverages:
    attributes: Attributes
    rates_with_averages: RatesWithAverages
    get_rate_errors: Sequence[tuple[str, GetRateError]]

    @classmethod
    def from_interface_with_counters_or_rates(
        cls,
        iface: InterfaceWithCounters | InterfaceWithRates,
        *,
        timestamp: float,
        value_store: MutableMapping[str, Any],
        params: Mapping[str, Any],
    ) -> "InterfaceWithRatesAndAverages":
        iface_rates = (
            iface
            if isinstance(iface, InterfaceWithRates)
            else InterfaceWithRates.from_interface_with_counters(
                iface,
                timestamp=timestamp,
                value_store=value_store,
            )
        )
        averages = cls._compute_averages(
            iface_rates,
            timestamp=timestamp,
            value_store=value_store,
            average_backlog_octets=params.get("average"),
            average_backlog_bmcast=params.get("average_bm"),
        )
        return cls(
            attributes=iface.attributes,
            rates_with_averages=RatesWithAverages(
                **{
                    rate_name: None
                    if rate is None
                    else RateWithAverage(
                        rate=rate,
                        average=averages.get(rate_name),
                    )
                    for rate_name, rate in asdict(iface_rates.rates).items()
                },
                in_nucast=cls._add_rates_and_averages(
                    *(
                        None
                        if (rate := getattr(iface_rates.rates, rate_name)) is None
                        else RateWithAverage(
                            rate,
                            averages.get(rate_name),
                        )
                        for rate_name in ("in_mcast", "in_bcast")
                    ),
                ),
                out_nucast=cls._add_rates_and_averages(
                    *(
                        None
                        if (rate := getattr(iface_rates.rates, rate_name)) is None
                        else RateWithAverage(
                            rate,
                            averages.get(rate_name),
                        )
                        for rate_name in ("out_mcast", "out_bcast")
                    ),
                ),
                total_octets=cls._add_rates_and_averages(
                    *(
                        None
                        if (rate := getattr(iface_rates.rates, rate_name)) is None
                        else RateWithAverage(
                            rate,
                            averages.get(rate_name),
                        )
                        for rate_name in ("in_octets", "out_octets")
                    ),
                ),
            ),
            get_rate_errors=iface_rates.get_rate_errors,
        )

    @staticmethod
    def _compute_averages(
        iface_rates: InterfaceWithRates,
        *,
        timestamp: float,
        value_store: MutableMapping[str, Any],
        average_backlog_octets: int | None,
        average_backlog_bmcast: int | None,
    ) -> Mapping[str, Average]:
        return {
            rate_name: Average(
                value=get_average(
                    value_store=value_store,
                    key=f"{rate_name}.{iface_rates.attributes.id_for_value_store}.average",
                    time=timestamp,
                    value=rate,
                    backlog_minutes=average_backlog,
                ),
                backlog=average_backlog,
            )
            for average_backlog, rate_names in (
                (
                    average_backlog_octets,
                    (
                        "in_octets",
                        "out_octets",
                    ),
                ),
                (
                    average_backlog_bmcast,
                    (
                        "in_mcast",
                        "in_bcast",
                        "out_mcast",
                        "out_bcast",
                    ),
                ),
            )
            for rate_name in rate_names
            if average_backlog is not None
            and (rate := getattr(iface_rates.rates, rate_name)) is not None
        }

    @staticmethod
    def _add_rates_and_averages(
        r0: RateWithAverage | None,
        /,
        *rs: RateWithAverage | None,
    ) -> RateWithAverage | None:
        if r0 is None:
            return None
        rate_with_avg = r0
        for r in rs:
            if r is None:
                return None
            rate_with_avg = rate_with_avg + r
        return rate_with_avg


Section = Sequence[InterfaceWithCounters]


def saveint(i: Any) -> int:
    try:
        return int(i)
    except (TypeError, ValueError):
        return 0


def mac_address_from_hexstring(hexstr: str) -> str:
    r"""
    >>> mac_address_from_hexstring('2e:27:06:b8:41:04')
    ".'\x06¸A\x04"
    >>> mac_address_from_hexstring('')
    ''
    """
    if hexstr:
        return "".join(chr(int(x, 16)) for x in hexstr.split(":"))
    return ""


# Remove 0 bytes from strings. They lead to problems e.g. here:
# On windows hosts the labels of network interfaces in oid
# iso.3.6.1.2.1.2.2.1.2.1 are given as hex strings with tailing
# 0 byte. When this string is part of the data which is sent to
# the nagios pipe all chars after the 0 byte are stripped of.
# Stupid fix: Remove all 0 bytes. Hope this causes no problems.
def cleanup_if_strings(s: str) -> str:
    if s and s != "":
        s = "".join([c for c in s if c != chr(0)]).strip()
    return s.replace("\n", " ")


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
        "1": "up",
        "2": "down",
        "3": "testing",
        "4": "unknown",
        "5": "dormant",
        "6": "not present",
        "7": "lower layer down",
        "8": "degraded",
    }
    return names.get(st, st)


def render_mac_address(phys_address: Union[Iterable[int], str]) -> str:
    if isinstance(phys_address, str):
        mac_bytes = (ord(x) for x in phys_address)
    else:
        mac_bytes = (x for x in phys_address)
    return (":".join(["%02s" % hex(m)[2:] for m in mac_bytes]).replace(" ", "0")).upper()


def item_matches(
    item: str,
    ifIndex: str,
    ifAlias: str,
    ifDescr: str,
) -> bool:
    return (
        item.lstrip("0") == ifIndex
        or (item == "0" * len(item) and saveint(ifIndex) == 0)
        or item == ifAlias
        or item == ifDescr
        or item == "%s %s" % (ifAlias, ifIndex)
        or item == "%s %s" % (ifDescr, ifIndex)
    )


# Pads port numbers with zeroes, so that items
# nicely sort alphabetically
def _pad_with_zeroes(
    section: Section,
    ifIndex: str,
    pad_portnumbers: bool,
) -> str:
    if pad_portnumbers:
        max_index = max(int(interface.attributes.index) for interface in section)
        digits = len(str(max_index))
        return ("%0" + str(digits) + "d") % int(ifIndex)
    return ifIndex


LevelSpec = Tuple[Optional[str], Tuple[Optional[float], Optional[float]]]
GeneralTrafficLevels = Dict[Tuple[str, str], LevelSpec]


def get_traffic_levels(params: Mapping[str, Any]) -> GeneralTrafficLevels:
    traffic_levels = params.get("traffic", [])
    traffic_levels += [("total", vs) for vs in params.get("total_traffic", {}).get("levels", [])]

    # Now bring the levels in a structure which is easily usable for the check
    # and also convert direction="both" to single in/out entries
    levels: GeneralTrafficLevels = {
        ("in", "upper"): (None, (None, None)),
        ("out", "upper"): (None, (None, None)),
        ("in", "lower"): (None, (None, None)),
        ("out", "lower"): (None, (None, None)),
        ("total", "lower"): (None, (None, None)),
        ("total", "upper"): (None, (None, None)),
    }
    for level in traffic_levels:
        traffic_dir = level[0]
        up_or_low = level[1][0]
        level_type = level[1][1][0]
        level_value = level[1][1][1]

        if traffic_dir == "both":
            levels[("in", up_or_low)] = (level_type, level_value)
            levels[("out", up_or_low)] = (level_type, level_value)
        else:
            levels[(traffic_dir, up_or_low)] = (level_type, level_value)

    return levels


GeneralPacketLevels = Dict[str, Dict[str, Optional[Tuple[float, float]]]]


def _get_packet_levels(
    params: Mapping[str, Any]
) -> Tuple[GeneralPacketLevels, GeneralPacketLevels]:
    DIRECTIONS = ("in", "out")
    PACKET_TYPES = ("errors", "multicast", "broadcast", "unicast")

    def none_levels() -> Dict[str, Dict[str, Optional[Any]]]:
        return {name: {direction: None for direction in DIRECTIONS} for name in PACKET_TYPES}

    levels_per_type = {
        "perc": none_levels(),
        "abs": none_levels(),
    }

    # Second iteration: seperate by perc and abs for easier further processing
    for name in PACKET_TYPES:
        for direction in DIRECTIONS:
            levels = params.get(name, {})
            level = levels.get(direction) or levels.get("both")
            if level is not None:
                levels_per_type[level[0]][name][direction] = level[1]

    return levels_per_type["abs"], levels_per_type["perc"]


SpecificTrafficLevels = Dict[Union[Tuple[str, str], Tuple[str, str, str]], Any]


def get_specific_traffic_levels(
    general_traffic_levels: GeneralTrafficLevels,
    unit: str,
    speed_in: Optional[float],
    speed_out: Optional[float],
    speed_total: Optional[float],
) -> SpecificTrafficLevels:
    traffic_levels: SpecificTrafficLevels = {}
    for (traffic_dir, up_or_low), (level_type, levels) in general_traffic_levels.items():
        if not isinstance(levels, tuple):
            traffic_levels[(traffic_dir, "predictive")] = levels
            traffic_levels[(traffic_dir, up_or_low, "warn")] = None
            traffic_levels[(traffic_dir, up_or_low, "crit")] = None
            continue  # don't convert predictive levels config
        warn, crit = levels

        for what, level_value in [("warn", warn), ("crit", crit)]:
            # If the measurement unit is set to bit and the bw levels
            # are of type absolute, convert these 'bit' entries to byte
            # still reported as bytes to stay compatible with older rrd data
            if unit == "Bit" and level_type == "abs":
                assert isinstance(level_value, int)
                level_value = level_value // 8
            elif level_type == "perc":
                assert isinstance(level_value, float)
                level_value = _get_scaled_traffic_level(
                    traffic_dir, level_value, speed_in, speed_out, speed_total
                )

            traffic_levels[(traffic_dir, up_or_low, what)] = level_value  # bytes
    return traffic_levels


def _get_scaled_traffic_level(
    direction: str,
    level_value: float,
    speed_in: Optional[float],
    speed_out: Optional[float],
    speed_total: Optional[float],
) -> Optional[float]:
    """convert percentages to absolute values."""

    def _scale(speed: float) -> float:
        return level_value / 100.0 * speed

    for direction_id, speed in zip(("in", "out", "total"), (speed_in, speed_out, speed_total)):
        if direction == direction_id:
            if speed is None:
                return None
            return _scale(speed)

    return None


def _uses_description_and_alias(item_appearance: str) -> Tuple[bool, bool]:
    if item_appearance == "descr":
        return True, False
    if item_appearance == "alias":
        return False, True
    return False, False


def _compute_item(
    item_appearance: str,
    attributes: Attributes,
    section: Section,
    pad_portnumbers: bool,
) -> str:
    uses_description, uses_alias = _uses_description_and_alias(item_appearance)
    if uses_description and attributes.descr:
        item = attributes.descr
    elif uses_alias and attributes.alias:
        item = attributes.alias
    else:
        item = _pad_with_zeroes(section, attributes.index, pad_portnumbers)
    return item


def check_regex_match_conditions(
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
    attributes: Attributes,
    matching_conditions: MatchingConditions,
) -> bool:

    match_index = matching_conditions.get("match_index")
    match_alias = matching_conditions.get("match_alias")
    match_desc = matching_conditions.get("match_desc")
    porttypes = matching_conditions.get("porttypes")
    if porttypes is not None:
        porttypes = porttypes[:]
        porttypes.append("")  # Allow main check to set no port type (e.g. hitachi_hnas_fc_if)
    portstates = matching_conditions.get("portstates")
    admin_states = matching_conditions.get("admin_states")

    return (
        check_regex_match_conditions(attributes.index, match_index)
        and check_regex_match_conditions(attributes.alias, match_alias)
        and check_regex_match_conditions(attributes.descr, match_desc)
        and (porttypes is None or attributes.type in porttypes)
        and (portstates is None or attributes.oper_status in portstates)
        and (
            admin_states is None
            or attributes.admin_status is None
            or attributes.admin_status in admin_states
        )
    )


class GroupConfiguration(TypedDict, total=False):
    member_appearance: str
    inclusion_condition: MatchingConditions
    exclusion_conditions: Iterable[MatchingConditions]
    labels: ServiceLabels


def _check_group_matching_conditions(
    attributes: Attributes,
    group_name: str,
    group_configuration: GroupConfiguration,
) -> bool:

    # group defined in agent output
    if "inclusion_condition" not in group_configuration:
        return group_name == attributes.group

    # group defined in rules
    return _check_single_matching_conditions(
        attributes,
        group_configuration["inclusion_condition"],
    ) and not any(
        _check_single_matching_conditions(
            attributes,
            exclusion_condition,
        )
        for exclusion_condition in group_configuration["exclusion_conditions"]
    )


def _groups_from_params(
    discovery_params: Sequence[Mapping[str, Any]],
) -> Dict[str, GroupConfiguration]:
    groups: Dict[str, GroupConfiguration] = {}
    inclusion_importances = {}
    exclusion_conditions = []

    # First, we find all defined groups. If multiple groups with the same name are defined, the one
    # from the most specific rule wins (the one highest up in the hierarchy). We also gather all
    # exclusion conditions (setting 'Do not group interfaces').
    for rule_importance, rule in enumerate(discovery_params[::-1]):
        create_groups, group_config = rule.get("grouping", (True, {"group_items": []}))
        if create_groups:
            for group_item in group_config["group_items"]:
                groups[group_item["group_name"]] = {
                    "member_appearance": group_item["member_appearance"],
                    "inclusion_condition": rule["matching_conditions"][1],
                }
                if "labels" in group_config:
                    groups[group_item["group_name"]]["labels"] = group_config["labels"]

                inclusion_importances[group_item["group_name"]] = rule_importance
        else:
            exclusion_conditions.append((rule["matching_conditions"][1], rule_importance))

    # Second, we add the exclusion conditions to the found groups. For each group, we only store
    # those exclusion conditions which are higher up in the hierarchy than the inclusion condition.
    for group_name, group_configuration in groups.items():
        group_configuration["exclusion_conditions"] = [
            exclusion_condition
            for exclusion_condition, exclusion_importance in exclusion_conditions
            if exclusion_importance > inclusion_importances[group_name]
        ]

    return groups


def discover_interfaces(  # pylint: disable=too-many-branches
    params: Sequence[Mapping[str, Any]],
    section: Section,
) -> type_defs.DiscoveryResult:
    if len(section) == 0:
        return

    pre_inventory = []
    seen_indices: Set[str] = set()
    n_times_item_seen: Dict[str, int] = defaultdict(int)
    interface_groups: Dict[str, GroupConfiguration] = {}

    # ==============================================================================================
    # SINGLE-INTERFACE DISCOVERY
    # ==============================================================================================
    for interface in section:
        discover_single_interface = False
        single_interface_settings = DISCOVERY_DEFAULT_PARAMETERS["discovery_single"][1]
        # find the most specific rule which applies to this interface and which has single-interface
        # discovery settings
        for rule in params:
            if "discovery_single" in rule and _check_single_matching_conditions(
                interface.attributes,
                rule["matching_conditions"][1],
            ):
                discover_single_interface, single_interface_settings = rule["discovery_single"]
                break

        # add all ways of describing this interface to the seen items (even for unmonitored ports)
        # to ensure meaningful descriptions
        pad_portnumbers = single_interface_settings.get(
            "pad_portnumbers",
            DISCOVERY_DEFAULT_PARAMETERS["discovery_single"][1]["pad_portnumbers"],
        )

        for item_appearance in (
            ["index", "descr", "alias"]
            if interface.attributes.descr != interface.attributes.alias
            else ["index", "descr"]
        ):
            n_times_item_seen[
                _compute_item(
                    item_appearance,
                    interface.attributes,
                    section,
                    pad_portnumbers,
                )
            ] += 1

        # compute actual item name
        item = _compute_item(
            single_interface_settings.get(
                "item_appearance",
                DISCOVERY_DEFAULT_PARAMETERS["discovery_single"][1]["item_appearance"],
            ),
            interface.attributes,
            section,
            pad_portnumbers,
        )

        # discover single interface
        if discover_single_interface and interface.attributes.index not in seen_indices:
            discovered_params_single = {
                "discovered_oper_status": [interface.attributes.oper_status],
                "discovered_speed": interface.attributes.speed,
            }
            if interface.attributes.admin_status is not None:
                discovered_params_single["discovered_admin_status"] = [
                    interface.attributes.admin_status
                ]

            try:
                index_as_item = int(item) == int(interface.attributes.index)
            except (TypeError, ValueError):
                index_as_item = False

            pre_inventory.append(
                (
                    item,
                    discovered_params_single,
                    int(interface.attributes.index),
                    index_as_item,
                    single_interface_settings.get("labels"),
                )
            )
            seen_indices.add(interface.attributes.index)

        # special case: the agent output already set this interface to grouped, in this case, we do
        # not use any matching conditions but instead check if interface.group == group_name, see
        # below
        if interface.attributes.group:
            interface_groups.setdefault(
                interface.attributes.group,
                {
                    "member_appearance": single_interface_settings.get(
                        "item_appearance",
                        "index",
                    ),
                },
            )

    # ==============================================================================================
    # GROUPING
    # ==============================================================================================
    interface_groups.update(_groups_from_params(params))
    for group_name, group_configuration in interface_groups.items():
        groups_has_members = False
        group_oper_status = "2"  # operation status, default is down (2)
        group_speed = 0.0  # total maximum speed of all interfaces in this group

        # Extract labels, they will be handled seperately.
        group_labels = group_configuration.pop("labels", None)

        # find all interfaces matching the group to compute state and speed
        for interface in section:
            if _check_group_matching_conditions(
                interface.attributes,
                group_name,
                group_configuration,
            ):
                groups_has_members = True
                # if at least one is up (1) then up is considered as valid
                group_oper_status = (
                    interface.attributes.oper_status_up
                    if interface.attributes.is_up
                    else group_oper_status
                )
                group_speed += interface.attributes.speed

        # only discover non-empty groups
        if groups_has_members:
            discovered_params_group = {
                "aggregate": group_configuration,
                "discovered_oper_status": [group_oper_status],
                "discovered_speed": group_speed,
            }

            # Note: the group interface index is always set to 1
            pre_inventory.append((group_name, discovered_params_group, 1, False, group_labels))

    # Check for duplicate items (e.g. when using Alias as item and the alias is not unique)
    for item, discovered_params, index, index_as_item, labels in pre_inventory:
        if not index_as_item and n_times_item_seen[item] > 1:
            new_item = "%s %d" % (item, index)
        else:
            new_item = item
        yield Service(
            item=new_item,
            parameters=dict(discovered_params),
            labels=[ServiceLabel(key, value) for key, value in labels.items()] if labels else None,
        )


def _get_value_store_key(
    name: str,
    *add_to_key: str,
) -> str:
    key = name
    for to_add in add_to_key:
        key += ".%s" % to_add
    return key


GroupMembers = Dict[Optional[str], List[Dict[str, str]]]


def _check_ungrouped_ifs(
    item: str,
    params: Mapping[str, Any],
    section: Section,
    timestamp: float,
    input_is_rate: bool,
    value_store: Optional[MutableMapping[str, Any]] = None,
) -> type_defs.CheckResult:
    """
    Check one or more ungrouped interfaces. In a non-cluster setup, only one interface will match
    the item and the results will simply be the output of check_single_interface. On a cluster,
    multiple interfaces can match. In this case, only the results from the interface with the
    highest outgoing traffic will be reported (since the corresponding node is likely the master).
    """
    last_results = None
    results_from_fastest_interface = None
    max_out_traffic = -1.0

    for interface in section:
        if item_matches(
            item, interface.attributes.index, interface.attributes.alias, interface.attributes.descr
        ):
            last_results = list(
                check_single_interface(
                    item,
                    params,
                    interface,
                    timestamp=timestamp,
                    input_is_rate=input_is_rate,
                    use_discovered_state_and_speed=interface.attributes.node is None,
                    value_store=value_store,
                )
            )
            for result in last_results:
                if (
                    isinstance(
                        result,
                        Metric,
                    )
                    and result.name == "out"
                    and result.value > max_out_traffic
                ):
                    max_out_traffic = result.value
                    results_from_fastest_interface = last_results

    if results_from_fastest_interface:
        yield from results_from_fastest_interface
        return
    # in case there were results, but they did not contain the metric for outgoing traffic, we
    # simply report the last result
    if last_results:
        yield from last_results
        return


def _filter_matching_interfaces(
    *,
    item: str,
    group_config: GroupConfiguration,
    section: Section,
) -> Collection[InterfaceWithCounters]:
    return [
        interface
        for interface in section
        if _check_group_matching_conditions(
            interface.attributes,
            item,
            group_config,
        )
    ]


def _accumulate_attributes(
    *,
    cumulated_attributes: Attributes,
    matching_attributes: Collection[Attributes],
    group_config: GroupConfiguration,
) -> None:
    num_up = 0
    nodes = set()

    for attributes in matching_attributes:
        nodes.add(str(attributes.node))
        if attributes.is_up:
            num_up += 1

        # Add interface info to group info
        if attributes.is_up:
            cumulated_attributes.speed += attributes.speed
        cumulated_attributes.out_qlen += attributes.out_qlen

        # This is the fallback ifType if None is set in the parameters
        cumulated_attributes.type = attributes.type

    if num_up == len(matching_attributes):
        cumulated_attributes.oper_status = cumulated_attributes.oper_status_up  # up
    elif num_up > 0:
        cumulated_attributes.oper_status = "8"  # degraded
    else:
        cumulated_attributes.oper_status = "2"  # down
    cumulated_attributes.oper_status_name = statename(cumulated_attributes.oper_status)

    alias_info = []
    if len(nodes) > 1:
        alias_info.append("nodes: %s" % ", ".join(nodes))

    # From pre-2.0
    if (iftype := group_config.get("iftype")) is not None:
        alias_info.append("type: %s" % iftype)
    if group_config.get("items"):
        alias_info.append("%d grouped interfaces" % len(matching_attributes))

    cumulated_attributes.alias = ", ".join(alias_info)


def _accumulate_counters(
    *,
    cumulated_interface: InterfaceWithCounters,
    matching_interfaces: Iterable[InterfaceWithCounters],
    input_is_rate: bool,
    timestamp: float,
    value_store: MutableMapping[str, Any],
) -> type_defs.CheckResult:
    for idx, interface in enumerate(matching_interfaces):
        if not input_is_rate:
            # Only these values are packed into counters
            # We might need to enlarge this table
            # However, more values leads to more MKCounterWrapped...
            rate_counter = [
                ("in", interface.counters.in_octets),
                ("inucast", interface.counters.in_ucast),
                ("inmcast", interface.counters.in_mcast),
                ("inbcast", interface.counters.in_bcast),
                ("indisc", interface.counters.in_disc),
                ("inerr", interface.counters.in_err),
                ("out", interface.counters.out_octets),
                ("outucast", interface.counters.out_ucast),
                ("outmcast", interface.counters.out_mcast),
                ("outbcast", interface.counters.out_bcast),
                ("outdisc", interface.counters.out_disc),
                ("outerr", interface.counters.out_err),
            ]
            for name, counter in rate_counter:
                try:
                    # We make sure that every group member has valid rates before adding up the
                    # counters
                    get_rate(
                        value_store,
                        _get_value_store_key(name, str(interface.attributes.node), str(idx)),
                        timestamp,
                        saveint(counter),
                        raise_overflow=True,
                    )
                except GetRateError:
                    yield IgnoreResults(value="Initializing counters")
                    # continue, other counters might wrap as well

        cumulated_interface.counters.in_octets += interface.counters.in_octets
        cumulated_interface.counters.in_ucast += interface.counters.in_ucast
        cumulated_interface.counters.in_mcast += interface.counters.in_mcast
        cumulated_interface.counters.in_bcast += interface.counters.in_bcast
        cumulated_interface.counters.in_disc += interface.counters.in_disc
        cumulated_interface.counters.in_err += interface.counters.in_err
        cumulated_interface.counters.out_octets += interface.counters.out_octets
        cumulated_interface.counters.out_ucast += interface.counters.out_ucast
        cumulated_interface.counters.out_mcast += interface.counters.out_mcast
        cumulated_interface.counters.out_bcast += interface.counters.out_bcast
        cumulated_interface.counters.out_disc += interface.counters.out_disc
        cumulated_interface.counters.out_err += interface.counters.out_err


def _group_members(
    *,
    matching_attributes: Iterable[Attributes],
    item: str,
    group_config: GroupConfiguration,
    section: Section,
) -> GroupMembers:
    group_members: GroupMembers = {}
    for attributes in matching_attributes:
        groups_node = group_members.setdefault(attributes.node, [])
        member_info = {
            "name": _compute_item(
                group_config.get(
                    "member_appearance",
                    # This happens when someones upgrades from v1.6 to v2,0, where the structure of the
                    # discovered parameters changed. Interface groups defined by the user will stop
                    # working, users have to do a re-discovery in that case, as we wrote in werk #11361.
                    # However, we can still support groups defined already in the agent output, since
                    # these work purley by the group name.
                    str(
                        group_config.get(
                            "item_type",
                            DISCOVERY_DEFAULT_PARAMETERS["discovery_single"][1]["item_appearance"],
                        )
                    ),
                ),
                attributes,
                section,
                item[0] == "0",
            ),
            "oper_status_name": attributes.oper_status_name,
        }
        if attributes.admin_status is not None:
            member_info["admin_status_name"] = statename(attributes.admin_status)
        groups_node.append(member_info)
    return group_members


def _check_grouped_ifs(  # pylint: disable=too-many-branches
    item: str,
    params: Mapping[str, Any],
    section: Section,
    group_name: str,
    timestamp: float,
    input_is_rate: bool,
    value_store: Optional[MutableMapping[str, Any]] = None,
) -> type_defs.CheckResult:
    """
    Grouped interfaces are combined into a single interface, which is then passed to
    check_single_interface.
    """
    matching_interfaces = _filter_matching_interfaces(
        item=item,
        group_config=params["aggregate"],
        section=section,
    )

    used_value_store = value_store if value_store is not None else get_value_store()

    cumulated_interface = InterfaceWithCounters(
        attributes=Attributes(
            index=item,
            descr=item,
            alias="",
            type="",
        ),
        counters=Counters(),
    )

    _accumulate_attributes(
        cumulated_attributes=cumulated_interface.attributes,
        matching_attributes=[iface.attributes for iface in matching_interfaces],
        group_config=params["aggregate"],
    )

    yield from _accumulate_counters(
        cumulated_interface=cumulated_interface,
        matching_interfaces=matching_interfaces,
        input_is_rate=input_is_rate,
        timestamp=timestamp,
        value_store=used_value_store,
    )

    yield from check_single_interface(
        item,
        params,
        cumulated_interface,
        group_members=_group_members(
            matching_attributes=[iface.attributes for iface in matching_interfaces],
            item=item,
            group_config=params["aggregate"],
            section=section,
        ),
        group_name=group_name,
        timestamp=timestamp,
        input_is_rate=input_is_rate,
        # the discovered speed corresponds to only one of the nodes, so it cannot be used for
        # interface groups on clusters; same for state
        use_discovered_state_and_speed=section[0].attributes.node is None,
        value_store=used_value_store,
    )


def check_multiple_interfaces(
    item: str,
    params: Mapping[str, Any],
    section: Section,
    *,
    group_name: str = "Interface group",
    timestamp: Optional[float] = None,
    input_is_rate: bool = False,
    value_store: Optional[MutableMapping[str, Any]] = None,
) -> type_defs.CheckResult:

    if timestamp is None:
        timestamp = time.time()

    if "aggregate" in params:
        yield from _check_grouped_ifs(
            item,
            params,
            section,
            group_name,
            timestamp,
            input_is_rate,
            value_store,
        )
    else:
        yield from _check_ungrouped_ifs(
            item,
            params,
            section,
            timestamp,
            input_is_rate,
            value_store,
        )


def _get_rate(
    value_store: MutableMapping[str, Any],
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


def _get_map_states(defined_mapping: Iterable[Tuple[Iterable[str], int]]) -> Mapping[str, State]:
    map_states = {}
    for states, mon_state in defined_mapping:
        for st in states:
            map_states[st] = State(mon_state)
    return map_states


def _render_status_info_group_members(
    oper_status_name: str,
    admin_status_name: Optional[str],
) -> str:
    if admin_status_name is None:
        return "(%s)" % oper_status_name
    return "(op. state: %s, admin state: %s)" % (oper_status_name, admin_status_name)


def _check_status(
    interface_status: str,
    target_states: Optional[Container[str]],
    states_map: Mapping[str, State],
) -> State:
    mon_state = State.OK
    if target_states is not None and interface_status not in target_states:
        mon_state = State.CRIT
    mon_state = states_map.get(interface_status, mon_state)
    return mon_state


def _check_speed(attributes: Attributes, targetspeed: Optional[int]) -> Result:
    """Check speed settings of interface

    Only if speed information is available. This is not always the case.
    """
    if attributes.speed:
        speed_actual = render.nicspeed(attributes.speed / 8)
        speed_expected = (
            ""
            if (targetspeed is None or int(attributes.speed) == targetspeed)
            else " (expected: %s)" % render.nicspeed(targetspeed / 8)
        )
        return Result(
            state=State.WARN if speed_expected else State.OK,
            summary=f"Speed: {speed_actual}{speed_expected}",
        )

    if targetspeed:
        return Result(
            state=State.OK,
            summary="Speed: %s (assumed)" % render.nicspeed(targetspeed / 8),
        )

    return Result(state=State.OK, summary="Speed: %s" % (attributes.speed_as_text or "unknown"))


# TODO: Check what the relationship between Errors, Discards, and ucast/mcast actually is.
# One case of winperf_if appeared to indicate that in that case Errors = Discards.
def check_single_interface(
    item: str,
    params: Mapping[str, Any],
    interface: InterfaceWithCounters,
    group_members: Optional[GroupMembers] = None,
    *,
    group_name: str = "Interface group",
    timestamp: Optional[float] = None,
    input_is_rate: bool = False,
    use_discovered_state_and_speed: bool = True,
    value_store: Optional[MutableMapping[str, Any]] = None,
) -> type_defs.CheckResult:

    if timestamp is None:
        timestamp = time.time()
    used_value_store = value_store if value_store is not None else get_value_store()

    # Params now must be a dict. Some keys might
    # be set to None
    if use_discovered_state_and_speed:
        targetspeed = params.get("speed", params.get("discovered_speed"))
    else:
        targetspeed = params.get("speed")
    assumed_speed_in = params.get("assumed_speed_in")
    assumed_speed_out = params.get("assumed_speed_out")
    average = params.get("average")
    unit = "Bit" if params.get("unit") in ["Bit", "bit"] else "B"
    average_bmcast = params.get("average_bm")

    # broadcast storm detection is turned off by default
    nucast_levels = params.get("nucasts")
    disc_levels = params.get("discards")

    # Convert the traffic related levels to a common format
    general_traffic_levels = get_traffic_levels(params)
    abs_packet_levels, perc_packet_levels = _get_packet_levels(params)

    yield from _interface_name(
        group_name=group_name if group_members else None,
        item=item,
        params=params,
        attributes=interface.attributes,
    )

    yield from _interface_status(
        params=params,
        attributes=interface.attributes,
        use_discovered_states=use_discovered_state_and_speed,
    )

    if interface.attributes.extra_info:
        yield Result(state=State.OK, summary=interface.attributes.extra_info)

    yield from _interface_mac(interface.attributes)

    yield from _output_group_members(group_members=group_members)

    yield _check_speed(interface.attributes, targetspeed)

    # prepare reference speed for computing relative bandwidth usage
    ref_speed = None
    if interface.attributes.speed:
        ref_speed = interface.attributes.speed / 8.0
    elif targetspeed:
        ref_speed = targetspeed / 8.0

    # Speed in bytes
    speed_b_in = (assumed_speed_in // 8) if assumed_speed_in else ref_speed
    speed_b_out = (assumed_speed_out // 8) if assumed_speed_out else ref_speed
    speed_b_total = speed_b_in + speed_b_out if speed_b_in and speed_b_out else None

    # Convert the traffic levels to interface specific levels, for example where the percentage
    # levels are converted to absolute levels or assumed speeds of an interface are treated correctly
    traffic_levels = get_specific_traffic_levels(
        general_traffic_levels, unit, speed_b_in, speed_b_out, speed_b_total
    )

    #
    # All internal values within this check after this point are bytes, not bits!
    #

    # When the interface is reported as down, there is no need to try to handle,
    # the performance counters. Most devices do reset the counter values to zero,
    # but we spotted devices, which do report error packes even for down interfaces.
    # To deal with it, we simply skip over all performance counter checks for down
    # interfaces.
    if str(interface.attributes.oper_status) == "2":
        return

    rates_dict: dict[str, float | None] = {}
    overflow_dict: dict[str, GetRateError] = {}
    rate_content = [
        ("intraffic", interface.counters.in_octets),
        ("inmcast", interface.counters.in_mcast),
        ("inbcast", interface.counters.in_bcast),
        ("inucast", interface.counters.in_ucast),
        ("indisc", interface.counters.in_disc),
        ("inerr", interface.counters.in_err),
        ("outtraffic", interface.counters.out_octets),
        ("outmcast", interface.counters.out_mcast),
        ("outbcast", interface.counters.out_bcast),
        ("outucast", interface.counters.out_ucast),
        ("outdisc", interface.counters.out_disc),
        ("outerr", interface.counters.out_err),
    ]
    for name, counter in rate_content:
        try:
            rates_dict[name] = _get_rate(
                used_value_store,
                _get_value_store_key(name, str(interface.attributes.node)),
                timestamp,
                counter,
                input_is_rate,
            )
        except GetRateError as get_rate_excpt:
            rates_dict[name] = None
            overflow_dict[name] = get_rate_excpt

    rates = _Rates(**rates_dict)

    yield Metric(
        "outqlen",
        interface.attributes.out_qlen,
    )

    yield from _output_bandwidth_rates(
        rates,
        speed_b_in,
        speed_b_out,
        speed_b_total,
        average,
        unit,
        traffic_levels,
        used_value_store,
        timestamp,
        item,
        assumed_speed_in,
        assumed_speed_out,
        monitor_total="total_traffic" in params,
    )

    yield from _output_packet_rates(
        # This is only temporary and will be handled with CMK-6472
        abs_packet_levels,
        perc_packet_levels,
        nucast_levels,
        disc_levels,
        average_bmcast,
        item=item,
        rates=rates,
        value_store=used_value_store,
        timestamp=timestamp,
    )

    if overflow_dict:
        overflows_human_readable = (
            f"{counter}: {get_rate_excpt}" for counter, get_rate_excpt in overflow_dict.items()
        )
        yield Result(
            state=State.OK,
            notice=f"Could not compute rates for the following counter(s): {', '.join(overflows_human_readable)}",
        )


def _interface_name(  # pylint: disable=too-many-branches
    *,
    group_name: Optional[str],
    item: str,
    params: Mapping[str, Any],
    attributes: Attributes,
) -> Iterable[Result]:
    if group_name:
        # The detailed group info is added later on
        yield Result(state=State.OK, summary=group_name)
        return

    if "infotext_format" in params:
        bracket_info = ""
        if params["infotext_format"] == "alias":
            bracket_info = attributes.alias
        elif params["infotext_format"] == "description":
            bracket_info = attributes.descr
        elif params["infotext_format"] == "alias_and_description":
            bracket_info = ", ".join([i for i in [attributes.alias, attributes.descr] if i])
        elif params["infotext_format"] == "alias_or_description":
            bracket_info = attributes.alias if attributes.alias else attributes.descr
        elif params["infotext_format"] == "desription_or_alias":
            bracket_info = attributes.descr if attributes.descr else attributes.alias

        if bracket_info:
            info_interface = "[%s]" % bracket_info
        else:
            info_interface = ""
    else:
        # Display port number or alias in summary_interface if that is not part
        # of the service description anyway
        if (
            (item == attributes.index or item.lstrip("0") == attributes.index)
            and attributes.alias in (item, "")
            and attributes.descr in (item, "")
        ):  # description trivial
            info_interface = ""
        elif (
            item == "%s %s" % (attributes.alias, attributes.index) and attributes.descr != ""
        ):  # non-unique Alias
            info_interface = "[%s/%s]" % (attributes.alias, attributes.descr)
        elif attributes.alias not in (item, ""):  # alias useful
            info_interface = "[%s]" % attributes.alias
        elif attributes.descr not in (item, ""):  # description useful
            info_interface = "[%s]" % attributes.descr
        else:
            info_interface = "[%s]" % attributes.index

    if attributes.node is not None:
        if info_interface:
            info_interface = "%s on %s" % (
                info_interface,
                attributes.node,
            )
        else:
            info_interface = "On %s" % attributes.node

    if info_interface:
        yield Result(
            state=State.OK,
            summary=info_interface,
        )


def _interface_mac(attributes: Attributes) -> Iterable[Result]:
    if attributes.phys_address:
        yield Result(
            state=State.OK,
            summary="MAC: %s" % render_mac_address(attributes.phys_address),
        )


def _interface_status(
    *,
    params: Mapping[str, Any],
    attributes: Attributes,
    use_discovered_states: bool,
) -> Iterable[Result]:

    if use_discovered_states:
        target_oper_states = params.get("state", params.get("discovered_oper_status"))
        target_admin_states = params.get("admin_state", params.get("discovered_admin_status"))
    else:
        target_oper_states = params.get("state")
        target_admin_states = params.get("admin_state")

    state_mapping_type, state_mappings = params.get(
        "state_mappings",
        (
            "independent_mappings",
            {},
        ),
    )
    yield from _check_oper_and_admin_state(
        attributes,
        state_mapping_type=state_mapping_type,
        state_mappings=state_mappings,
        target_oper_states=target_oper_states,
        target_admin_states=target_admin_states,
    )


def _check_oper_and_admin_state(
    attributes: Attributes,
    state_mapping_type: Literal["independent_mappings", "combined_mappings"],
    state_mappings: Union[
        Iterable[Tuple[str, str, int]], Mapping[str, Iterable[Tuple[Iterable[str], int]]]  #
    ],
    target_oper_states: Optional[Container[str]],
    target_admin_states: Optional[Container[str]],
) -> Iterable[Result]:
    if combined_mon_state := _check_oper_and_admin_state_combined(
        attributes,
        state_mapping_type,
        state_mappings,
    ):
        yield combined_mon_state
        return

    map_oper_states, map_admin_states = _get_oper_and_admin_states_maps_independent(
        state_mapping_type,
        state_mappings,
    )

    yield from _check_oper_and_admin_state_independent(
        attributes,
        target_oper_states=target_oper_states,
        target_admin_states=target_admin_states,
        map_oper_states=map_oper_states,
        map_admin_states=map_admin_states,
    )


def _get_oper_and_admin_states_maps_independent(
    state_mapping_type: Literal["combined_mappings", "independent_mappings"],
    state_mappings: Union[
        Iterable[Tuple[str, str, int]], Mapping[str, Iterable[Tuple[Iterable[str], int]]]  #
    ],
) -> Tuple[Iterable[Tuple[Iterable[str], int]], Iterable[Tuple[Iterable[str], int]]]:
    if state_mapping_type == "independent_mappings":
        assert isinstance(state_mappings, Mapping)
        return state_mappings.get("map_operstates", []), state_mappings.get("map_admin_states", [])
    return [], []


def _check_oper_and_admin_state_independent(
    attributes: Attributes,
    target_oper_states: Optional[Container[str]],
    target_admin_states: Optional[Container[str]],
    map_oper_states: Iterable[Tuple[Iterable[str], int]],
    map_admin_states: Iterable[Tuple[Iterable[str], int]],
) -> Iterable[Result]:
    yield Result(
        state=_check_status(
            attributes.oper_status,
            target_oper_states,
            _get_map_states(map_oper_states),
        ),
        summary=f"({attributes.oper_status_name})",
        details=f"Operational state: {attributes.oper_status_name}",
    )

    if not attributes.admin_status:
        return

    yield Result(
        state=_check_status(
            str(attributes.admin_status),
            target_admin_states,
            _get_map_states(map_admin_states),
        ),
        summary=f"Admin state: {statename(attributes.admin_status)}",
    )


def _check_oper_and_admin_state_combined(
    attributes: Attributes,
    state_mapping_type: Literal["combined_mappings", "independent_mappings"],
    state_mappings: Union[
        Iterable[Tuple[str, str, int]], Mapping[str, Iterable[Tuple[Iterable[str], int]]]  #
    ],
) -> Optional[Result]:
    if attributes.admin_status is None:
        return None
    if state_mapping_type == "independent_mappings":
        return None
    assert not isinstance(state_mappings, Mapping)
    if (
        combined_mon_state := {
            (oper_state, admin_state,): State(
                mon_state
            )  #
            for oper_state, admin_state, mon_state in state_mappings
        }.get(
            (
                attributes.oper_status,
                attributes.admin_status,
            )
        )
    ) is None:
        return None
    return Result(
        state=combined_mon_state,
        summary=f"(op. state: {attributes.oper_status_name}, admin state: {statename(attributes.admin_status)})",
        details=f"Operational state: {attributes.oper_status_name}, Admin state: {statename(attributes.admin_status)}",
    )


def _output_group_members(
    *,
    group_members: Optional[GroupMembers],
) -> Iterable[Result]:
    if not group_members:
        return

    infos_group = []
    for group_node, members in group_members.items():
        member_info = []
        for member in members:
            member_info.append(
                "%s %s"
                % (
                    member["name"],
                    _render_status_info_group_members(
                        member["oper_status_name"],
                        member.get("admin_status_name"),
                    ),
                )
            )

        nodeinfo = ""
        if group_node is not None and len(group_members) > 1:
            nodeinfo = " on node %s" % group_node
        infos_group.append("[%s%s]" % (", ".join(member_info), nodeinfo))

    yield Result(
        state=State.OK,
        summary="Members: %s" % " ".join(infos_group),
    )


def _output_bandwidth_rates(  # pylint: disable=too-many-branches
    rates: _Rates,
    speed_b_in: float,
    speed_b_out: float,
    speed_b_total: float,
    average: Optional[int],
    unit: str,
    traffic_levels: SpecificTrafficLevels,
    value_store: MutableMapping[str, Any],
    timestamp: float,
    item: str,
    assumed_speed_in: Optional[int],
    assumed_speed_out: Optional[int],
    *,
    monitor_total: bool,
) -> type_defs.CheckResult:
    if unit == "Bit":
        bandwidth_renderer: Callable[[float], str] = render.nicspeed
    else:
        bandwidth_renderer = render.iobandwidth

    for direction, traffic, speed in [
        ("in", rates.intraffic, speed_b_in),
        ("out", rates.outtraffic, speed_b_out),
        *(
            [
                (
                    "total",
                    _sum_optional_floats(rates.intraffic, rates.outtraffic),
                    speed_b_total,
                )
            ]
            if monitor_total
            else []
        ),
    ]:
        if traffic is None:
            continue
        yield from _check_single_bandwidth(
            direction=direction,
            traffic=traffic,
            speed=speed,
            renderer=bandwidth_renderer,
            average=average,
            traffic_levels=traffic_levels,
            value_store=value_store,
            timestamp=timestamp,
            item=item,
            assumed_speed_in=assumed_speed_in,
            assumed_speed_out=assumed_speed_out,
        )


def _check_single_bandwidth(  # pylint: disable=too-many-branches
    *,
    direction: str,
    traffic: float,
    speed: float,
    renderer: Callable[[float], str],
    average: Optional[int],
    traffic_levels: SpecificTrafficLevels,
    value_store: MutableMapping[str, Any],
    timestamp: float,
    item: str,
    assumed_speed_in: Optional[int],
    assumed_speed_out: Optional[int],
) -> type_defs.CheckResult:
    use_predictive_levels = (direction, "predictive") in traffic_levels

    # The "normal" upper/lower levels can be valid for the raw value or the average value.
    # We display them in the raw signal's graph for both cases.
    # However, predictive levels are different in it's nature and will be handled seperately
    if use_predictive_levels:
        levels_upper = None
        levels_lower = None
    else:
        levels_upper = (
            traffic_levels[(direction, "upper", "warn")],
            traffic_levels[(direction, "upper", "crit")],
        )
        levels_lower = (
            traffic_levels[(direction, "lower", "warn")],
            traffic_levels[(direction, "lower", "crit")],
        )

    if average:
        filtered_traffic = get_average(
            value_store,
            "%s.%s.avg" % (direction, item),
            timestamp,
            traffic,
            average,
        )  # apply levels to average traffic
        title = "%s average %dmin" % (direction.title(), average)
    else:
        filtered_traffic = traffic
        title = direction.title()

    if use_predictive_levels:
        if average:
            dsname = "%s_avg_%d" % (direction, average)
        else:
            dsname = direction

        levels_predictive = traffic_levels[(direction, "predictive")]
        result, metric_from_pred_check, *ref_curve = check_levels_predictive(
            filtered_traffic,
            levels=levels_predictive,
            metric_name=dsname,
            render_func=renderer,
            label=title,
        )
        assert isinstance(result, Result)

        if average:
            # The avg is not needed for displaying a graph, but it's historic
            # value will be needed for the future calculation of the ref_curve,
            # so we can't dump it.
            yield metric_from_pred_check

        yield from ref_curve  # reference curve for predictive levels
    else:
        # The metric already got yielded, so it's only the result that is
        # needed here.
        (result,) = check_levels(
            filtered_traffic,
            levels_upper=levels_upper,
            levels_lower=levels_lower,
            render_func=renderer,
            label=title,
        )

    # We have a valid result now. Just enhance it by the percentage info,
    # if available
    if speed:
        perc_info = render.percent(100.0 * filtered_traffic / speed)
        if assumed_speed_in or assumed_speed_out:
            perc_info += "/" + renderer(speed)

        yield Result(
            state=result.state,
            summary="%s (%s)" % (result.summary, perc_info),
        )
    else:
        yield result

    # output metric after result. this makes it easier to analyze the check output,
    # as this is the "normal" order when yielding from check_levels.
    # Note: we always yield the unaveraged values here, since this is what we want to display in
    # our graphs
    yield Metric(
        direction,
        traffic,
        levels=levels_upper,
        boundaries=(0, speed),
    )


def _render_floating_point(value: float, precision: int, unit: str) -> str:
    """Render a floating point value to the given precision,
    removing trailing zeros and a trailing decimal point,
    appending the given unit.

    Examples:
    >>> _render_floating_point(3.141593, 3, " rad")
    '3.142 rad'
    >>> _render_floating_point(-0.0001, 3, "%")
    '>-0.001%'
    >>> _render_floating_point(100.0, 3, "%")
    '100%'
    """
    value = float(value)  # be nice

    if round(value) == value:
        return f"{value:.0f}{unit}"

    if abs(value) < float(tol := f"0.{'0'*(precision-1)}1"):
        return f"{'<' if value > 0 else '>-'}{tol}{unit}"

    return f"{value:.{precision}f}".rstrip("0.") + unit


def _sum_optional_floats(*vs: float | None) -> float | None:
    """
    >>> _sum_optional_floats(1.1, 2, 0)
    3.1
    >>> _sum_optional_floats(123.12312, None, 0) is None
    True
    """
    s = 0.0
    for v in vs:
        if v is None:
            return None
        s += v
    return s


def _output_packet_rates(
    abs_packet_levels: GeneralPacketLevels,
    perc_packet_levels: GeneralPacketLevels,
    nucast_levels: Optional[Tuple[float, float]],
    disc_levels: Optional[Tuple[float, float]],
    average_bmcast: Optional[int],
    *,
    item: str,
    rates: _Rates,
    value_store: MutableMapping[str, Any],
    timestamp: float,
) -> type_defs.CheckResult:
    for direction, mrate, brate, urate, nurate, discrate, errorrate in [
        (
            "in",
            rates.inmcast,
            rates.inbcast,
            rates.inucast,
            _sum_optional_floats(rates.inmcast, rates.inbcast),
            rates.indisc,
            rates.inerr,
        ),
        (
            "out",
            rates.outmcast,
            rates.outbcast,
            rates.outucast,
            _sum_optional_floats(rates.outmcast, rates.outbcast),
            rates.outdisc,
            rates.outerr,
        ),
    ]:
        all_pacrate = _sum_optional_floats(urate, nurate, errorrate)
        success_pacrate = _sum_optional_floats(urate, nurate)
        for rate, abs_levels, perc_levels, display_name, metric_name, reference_rate in [
            (
                errorrate,
                abs_packet_levels["errors"][direction],
                perc_packet_levels["errors"][direction],
                "errors",
                "err",
                all_pacrate,
            ),
            (
                mrate,
                abs_packet_levels["multicast"][direction],
                perc_packet_levels["multicast"][direction],
                "multicast",
                "mcast",
                success_pacrate,
            ),
            (
                brate,
                abs_packet_levels["broadcast"][direction],
                perc_packet_levels["broadcast"][direction],
                "broadcast",
                "bcast",
                success_pacrate,
            ),
            (
                urate,
                abs_packet_levels["unicast"][direction],
                perc_packet_levels["unicast"][direction],
                "unicast",
                "ucast",
                success_pacrate,
            ),
        ]:
            if rate is None:
                continue

            yield from _check_single_packet_rate(
                rate=rate,
                direction=direction,
                abs_levels=abs_levels,
                perc_levels=perc_levels,
                display_name=display_name,
                metric_name=metric_name,
                reference_rate=reference_rate,
                average_bmcast=average_bmcast,
                item=item,
                value_store=value_store,
                timestamp=timestamp,
            )

        for display_name, metric_name, rate, levels in [
            ("Non-unicast", "nucast", nurate, nucast_levels),
            ("Discards", "disc", discrate, disc_levels),
        ]:
            if rate is None:
                continue
            yield from check_levels(
                rate,
                levels_upper=levels,
                metric_name=f"{direction}{metric_name}",
                render_func=partial(_render_floating_point, precision=2, unit=" packets/s"),
                label=f"{display_name} {direction}",
                notice_only=True,
            )


def _check_single_packet_rate(
    *,
    rate: float,
    direction: str,
    abs_levels: Any,
    perc_levels: Any,
    display_name: str,
    metric_name: str,
    reference_rate: float | None,
    average_bmcast: Optional[int],
    item: str,
    value_store: MutableMapping[str, Any],
    timestamp: float,
) -> type_defs.CheckResult:
    # Calculate the metric with actual levels, no matter if they
    # come from perc_- or abs_levels
    if perc_levels is not None:
        if reference_rate is None:
            return
        if reference_rate > 0:
            merged_levels: Optional[Tuple[float, float]] = (
                perc_levels[0] / 100.0 * reference_rate,
                perc_levels[1] / 100.0 * reference_rate,
            )
        else:
            merged_levels = None
    else:
        merged_levels = abs_levels

    metric = Metric(
        f"{direction}{metric_name}",
        rate,
        levels=merged_levels,
    )

    # Further calculation now precedes with average value,
    # if requested.
    infotxt = f"{display_name.title()} {direction}"
    if average_bmcast is not None and display_name not in ("errors", "unicast"):
        rate = get_average(
            value_store,
            "%s.%s.%s.avg" % (direction, display_name, item),
            timestamp,
            rate,
            average_bmcast,
        )
        infotxt += f" average {average_bmcast}min"

    if perc_levels is not None:
        if reference_rate is None:
            return
        # Note: A rate of 0% for a pacrate of 0 is mathematically incorrect,
        # but it yields the best information for the "no packets" case in the check output.
        perc_value = 0 if reference_rate == 0 else rate * 100 / reference_rate
        (result,) = check_levels(
            perc_value,
            levels_upper=perc_levels,
            render_func=partial(_render_floating_point, precision=3, unit="%"),
            label=infotxt,
            notice_only=True,
        )
        yield result
    else:
        (result,) = check_levels(
            rate,
            levels_upper=abs_levels,
            render_func=partial(_render_floating_point, precision=2, unit=" packets/s"),
            label=infotxt,
            notice_only=True,
        )
        yield result

    # output metric after result. this makes it easier to analyze the check output,
    # as this is the "normal" order when yielding from check_levels.
    # Note: we always yield the unaveraged values here, since this is what we want to display in
    # our graphs
    yield metric


def cluster_check(
    item: str,
    params: Mapping[str, Any],
    section: Mapping[str, Optional[Section]],
) -> type_defs.CheckResult:

    ifaces = [
        InterfaceWithCounters(
            attributes=Attributes(
                **{  # type: ignore[arg-type]
                    **asdict(iface.attributes),
                    "node": node,
                }
            ),
            counters=iface.counters,
        )
        for node, node_ifaces in section.items()
        for iface in node_ifaces or ()
    ]

    yield from check_multiple_interfaces(
        item,
        params,
        ifaces,
    )
