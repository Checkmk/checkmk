#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import enum
import itertools
import re
import time
from collections import defaultdict
from collections.abc import (
    Callable,
    Collection,
    Container,
    Iterable,
    Iterator,
    Mapping,
    MutableMapping,
    Sequence,
)
from dataclasses import dataclass, fields, replace
from functools import partial
from typing import Any, assert_never, Final, Literal, ParamSpec, TypedDict, TypeVar

import pydantic

from cmk.agent_based.v1 import check_levels as check_levels_v1
from cmk.agent_based.v1 import check_levels_predictive
from cmk.agent_based.v2 import (
    CheckResult,
    DiscoveryResult,
    get_average,
    get_rate,
    get_value_store,
    GetRateError,
    Metric,
    render,
    Result,
    Service,
    ServiceLabel,
    State,
)

ServiceLabels = dict[str, str]

_ItemAppearance = Literal["index", "descr", "alias"]


class SingleInterfaceDiscoveryParams(TypedDict, total=False):
    item_appearance: _ItemAppearance
    pad_portnumbers: bool
    labels: ServiceLabels


MatchingConditions = Mapping[str, list[str]]


class DiscoveryDefaultParams(TypedDict, total=False):
    discovery_single: tuple[bool, SingleInterfaceDiscoveryParams]
    matching_conditions: tuple[bool, MatchingConditions]


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


def _to_item_appearance(value: str) -> _ItemAppearance:
    match value:
        case "index" | "descr" | "alias":
            return value
    raise ValueError(f"Invalid item appearance: {value}")


class IndependentMapping(pydantic.BaseModel, frozen=True):
    map_operstates: Sequence[tuple[Sequence[str], Literal[0, 1, 2, 3]]] = []
    map_admin_states: Sequence[tuple[Sequence[str], Literal[0, 1, 2, 3]]] = []


class CombinedMapping(list[tuple[str, str, Literal[0, 1, 2, 3]]]):
    pass


StateMappings = IndependentMapping | CombinedMapping


class _MissingOperStatus:
    def __str__(self) -> str:
        return "Not available"


@dataclass(frozen=True)
class MemberInfo:
    name: str
    oper_status_name: str | _MissingOperStatus
    admin_status_name: str | None = None

    def __str__(self) -> str:
        status_info = (
            f"({self.oper_status_name})"
            if self.admin_status_name is None
            else f"(op. state: {self.oper_status_name}, admin state: {self.admin_status_name})"
        )
        return f"{self.name} {status_info}"


@dataclass
class Attributes:
    index: str
    descr: str
    alias: str
    type: str
    speed: float = 0
    oper_status: str = ""
    out_qlen: float | None = None
    phys_address: Iterable[int] | str = ""
    oper_status_name: str | _MissingOperStatus = ""
    speed_as_text: str = ""
    group: str | None = None
    node: str | None = None
    admin_status: str | None = None
    extra_info: str | None = None

    def __post_init__(self) -> None:
        self.finalize()

    def finalize(self) -> None:
        if not self.oper_status_name:
            self.oper_status_name = get_if_state_name(self.oper_status)

        # Fix bug in TP Link switches
        if self.speed > 9 * 1000 * 1000 * 1000 * 1000:
            self.speed /= 10000

        self.descr = _cleanup_if_strings(self.descr)
        self.alias = _cleanup_if_strings(self.alias)

    @property
    def oper_status_up(self) -> str:
        return "1"

    @property
    def is_up(self) -> bool:
        return self.oper_status == self.oper_status_up

    @property
    def id_for_value_store(self) -> str:
        return f"{self.index}.{self.descr}.{self.alias}.{self.node}"


Interface = Attributes  # CMK-12228


@dataclass
class Counters:
    in_octets: float | None = None
    in_mcast: float | None = None
    in_bcast: float | None = None
    in_nucast: float | None = None
    in_ucast: float | None = None
    in_disc: float | None = None
    in_err: float | None = None
    out_octets: float | None = None
    out_mcast: float | None = None
    out_bcast: float | None = None
    out_nucast: float | None = None
    out_ucast: float | None = None
    out_disc: float | None = None
    out_err: float | None = None


@dataclass
class InterfaceWithCounters:
    attributes: Attributes
    counters: Counters


@dataclass(frozen=True, kw_only=True)
class Rates:
    in_octets: float | None = None
    in_mcast: float | None = None
    in_bcast: float | None = None
    in_ucast: float | None = None
    in_nucast: float | None = None
    in_disc: float | None = None
    in_err: float | None = None
    out_octets: float | None = None
    out_mcast: float | None = None
    out_bcast: float | None = None
    out_ucast: float | None = None
    out_nucast: float | None = None
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
        value_store: MutableMapping[str, object],
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
        value_store: MutableMapping[str, object],
    ) -> tuple[Rates, Sequence[tuple[str, GetRateError]]]:
        rate_errors = {}
        in_octets, rate_errors["in_octets"] = cls._compute_rate(
            counter=iface_counters.counters.in_octets,
            timestamp=timestamp,
            value_store=value_store,
            value_store_key=f"in_octets.{iface_counters.attributes.id_for_value_store}",
        )
        in_ucast, rate_errors["in_ucast"] = cls._compute_rate(
            counter=iface_counters.counters.in_ucast,
            timestamp=timestamp,
            value_store=value_store,
            value_store_key=f"in_ucast.{iface_counters.attributes.id_for_value_store}",
        )
        in_mcast, rate_errors["in_mcast"] = cls._compute_rate(
            counter=iface_counters.counters.in_mcast,
            timestamp=timestamp,
            value_store=value_store,
            value_store_key=f"in_mcast.{iface_counters.attributes.id_for_value_store}",
        )
        in_bcast, rate_errors["in_bcast"] = cls._compute_rate(
            counter=iface_counters.counters.in_bcast,
            timestamp=timestamp,
            value_store=value_store,
            value_store_key=f"in_bcast.{iface_counters.attributes.id_for_value_store}",
        )
        in_nucast, rate_errors["in_nucast"] = cls._compute_rate(
            counter=iface_counters.counters.in_nucast,
            timestamp=timestamp,
            value_store=value_store,
            value_store_key=f"in_nucast.{iface_counters.attributes.id_for_value_store}",
        )
        in_disc, rate_errors["in_disc"] = cls._compute_rate(
            counter=iface_counters.counters.in_disc,
            timestamp=timestamp,
            value_store=value_store,
            value_store_key=f"in_disc.{iface_counters.attributes.id_for_value_store}",
        )
        in_err, rate_errors["in_err"] = cls._compute_rate(
            counter=iface_counters.counters.in_err,
            timestamp=timestamp,
            value_store=value_store,
            value_store_key=f"in_err.{iface_counters.attributes.id_for_value_store}",
        )
        out_octets, rate_errors["out_octets"] = cls._compute_rate(
            counter=iface_counters.counters.out_octets,
            timestamp=timestamp,
            value_store=value_store,
            value_store_key=f"out_octets.{iface_counters.attributes.id_for_value_store}",
        )
        out_ucast, rate_errors["out_ucast"] = cls._compute_rate(
            counter=iface_counters.counters.out_ucast,
            timestamp=timestamp,
            value_store=value_store,
            value_store_key=f"out_ucast.{iface_counters.attributes.id_for_value_store}",
        )
        out_mcast, rate_errors["out_mcast"] = cls._compute_rate(
            counter=iface_counters.counters.out_mcast,
            timestamp=timestamp,
            value_store=value_store,
            value_store_key=f"out_mcast.{iface_counters.attributes.id_for_value_store}",
        )
        out_bcast, rate_errors["out_bcast"] = cls._compute_rate(
            counter=iface_counters.counters.out_bcast,
            timestamp=timestamp,
            value_store=value_store,
            value_store_key=f"out_bcast.{iface_counters.attributes.id_for_value_store}",
        )
        out_nucast, rate_errors["out_nucast"] = cls._compute_rate(
            counter=iface_counters.counters.out_nucast,
            timestamp=timestamp,
            value_store=value_store,
            value_store_key=f"out_nucast.{iface_counters.attributes.id_for_value_store}",
        )
        out_disc, rate_errors["out_disc"] = cls._compute_rate(
            counter=iface_counters.counters.out_disc,
            timestamp=timestamp,
            value_store=value_store,
            value_store_key=f"out_disc.{iface_counters.attributes.id_for_value_store}",
        )
        out_err, rate_errors["out_err"] = cls._compute_rate(
            counter=iface_counters.counters.out_err,
            timestamp=timestamp,
            value_store=value_store,
            value_store_key=f"out_err.{iface_counters.attributes.id_for_value_store}",
        )
        return Rates(
            in_octets=in_octets,
            in_mcast=in_mcast,
            in_bcast=in_bcast,
            in_nucast=in_nucast,
            in_ucast=in_ucast,
            in_disc=in_disc,
            in_err=in_err,
            out_octets=out_octets,
            out_mcast=out_mcast,
            out_bcast=out_bcast,
            out_nucast=out_nucast,
            out_ucast=out_ucast,
            out_disc=out_disc,
            out_err=out_err,
        ), [
            (rate_name, get_rate_error)
            for rate_name, get_rate_error in rate_errors.items()
            if get_rate_error
        ]

    @staticmethod
    def _compute_rate(
        *,
        counter: float | None,
        timestamp: float,
        value_store: MutableMapping[str, object],
        value_store_key: str,
    ) -> tuple[float | None, GetRateError | None]:
        if counter is None:
            return None, None
        try:
            return (
                get_rate(
                    value_store=value_store,
                    key=value_store_key,
                    time=timestamp,
                    value=counter,
                    raise_overflow=True,
                ),
                None,
            )
        except GetRateError as get_rate_error:
            return None, get_rate_error


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
            average=(
                self.average + other.average
                if (self.average is not None and other.average is not None)
                else None
            ),
        )


@dataclass(frozen=True, kw_only=True)
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

    def __add__(self, other: "RatesWithAverages") -> "RatesWithAverages":
        return RatesWithAverages(
            **{
                field.name: (
                    value + other_value
                    if (value := getattr(self, field.name)) is not None
                    and (other_value := getattr(other, field.name)) is not None
                    else None
                )
                for field in fields(self)
            }
        )


@dataclass(frozen=True, kw_only=True)
class _AveragingParams:
    value_store: MutableMapping[str, object]
    value_store_key: str
    timestamp: float
    backlog_minutes: int


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
        value_store: MutableMapping[str, object],
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
        in_octets = cls._rate_with_average(
            rate=iface_rates.rates.in_octets,
            averaging_params=(
                _AveragingParams(
                    value_store=value_store,
                    value_store_key=f"in_octets.{iface_rates.attributes.id_for_value_store}.average",
                    timestamp=timestamp,
                    backlog_minutes=backlog_minutes_in_octets,
                )
                if (backlog_minutes_in_octets := params.get("average")) is not None
                else None
            ),
        )
        out_octets = cls._rate_with_average(
            rate=iface_rates.rates.out_octets,
            averaging_params=(
                _AveragingParams(
                    value_store=value_store,
                    value_store_key=f"out_octets.{iface_rates.attributes.id_for_value_store}.average",
                    timestamp=timestamp,
                    backlog_minutes=backlog_minutes_out_octets,
                )
                if (backlog_minutes_out_octets := params.get("average")) is not None
                else None
            ),
        )
        in_ucast = cls._rate_with_average(
            rate=iface_rates.rates.in_ucast,
            averaging_params=None,
        )
        out_ucast = cls._rate_with_average(
            rate=iface_rates.rates.out_ucast,
            averaging_params=None,
        )
        in_mcast = cls._rate_with_average(
            rate=iface_rates.rates.in_mcast,
            averaging_params=(
                _AveragingParams(
                    value_store=value_store,
                    value_store_key=f"in_mcast.{iface_rates.attributes.id_for_value_store}.average",
                    timestamp=timestamp,
                    backlog_minutes=average_backlog_in_mcast,
                )
                if (average_backlog_in_mcast := params.get("average_bm")) is not None
                else None
            ),
        )
        out_mcast = cls._rate_with_average(
            rate=iface_rates.rates.out_mcast,
            averaging_params=(
                _AveragingParams(
                    value_store=value_store,
                    value_store_key=f"out_mcast.{iface_rates.attributes.id_for_value_store}.average",
                    timestamp=timestamp,
                    backlog_minutes=average_backlog_out_mcast,
                )
                if (average_backlog_out_mcast := params.get("average_bm")) is not None
                else None
            ),
        )
        in_bcast = cls._rate_with_average(
            rate=iface_rates.rates.in_bcast,
            averaging_params=(
                _AveragingParams(
                    value_store=value_store,
                    value_store_key=f"in_bcast.{iface_rates.attributes.id_for_value_store}.average",
                    timestamp=timestamp,
                    backlog_minutes=average_backlog_in_bcast,
                )
                if (average_backlog_in_bcast := params.get("average_bm")) is not None
                else None
            ),
        )
        out_bcast = cls._rate_with_average(
            rate=iface_rates.rates.out_bcast,
            averaging_params=(
                _AveragingParams(
                    value_store=value_store,
                    value_store_key=f"out_bcast.{iface_rates.attributes.id_for_value_store}.average",
                    timestamp=timestamp,
                    backlog_minutes=average_backlog_out_bcast,
                )
                if (average_backlog_out_bcast := params.get("average_bm")) is not None
                else None
            ),
        )
        in_nucast = cls._rate_with_average(
            rate=iface_rates.rates.in_nucast,
            averaging_params=None,
        ) or cls._add_rates_and_averages(
            in_mcast,
            in_bcast,
        )
        out_nucast = cls._rate_with_average(
            rate=iface_rates.rates.out_nucast,
            averaging_params=None,
        ) or cls._add_rates_and_averages(
            out_mcast,
            out_bcast,
        )
        in_disc = cls._rate_with_average(
            rate=iface_rates.rates.in_disc,
            averaging_params=None,
        )
        out_disc = cls._rate_with_average(
            rate=iface_rates.rates.out_disc,
            averaging_params=None,
        )
        in_err = cls._rate_with_average(
            rate=iface_rates.rates.in_err,
            averaging_params=None,
        )
        out_err = cls._rate_with_average(
            rate=iface_rates.rates.out_err,
            averaging_params=None,
        )
        total_octets = cls._add_rates_and_averages(
            in_octets,
            out_octets,
        )
        return cls(
            attributes=iface.attributes,
            rates_with_averages=RatesWithAverages(
                in_octets=in_octets,
                in_mcast=in_mcast,
                in_bcast=in_bcast,
                in_nucast=in_nucast,
                in_ucast=in_ucast,
                in_disc=in_disc,
                in_err=in_err,
                out_octets=out_octets,
                out_mcast=out_mcast,
                out_bcast=out_bcast,
                out_nucast=out_nucast,
                out_ucast=out_ucast,
                out_disc=out_disc,
                out_err=out_err,
                total_octets=total_octets,
            ),
            get_rate_errors=iface_rates.get_rate_errors,
        )

    @staticmethod
    def _rate_with_average(
        *,
        rate: float | None,
        averaging_params: _AveragingParams | None,
    ) -> RateWithAverage | None:
        if rate is None:
            return None
        if averaging_params is None:
            return RateWithAverage(
                rate=rate,
                average=None,
            )
        return RateWithAverage(
            rate=rate,
            average=(
                Average(
                    value=average,
                    backlog=averaging_params.backlog_minutes,
                )
                if (
                    average := get_average(
                        value_store=averaging_params.value_store,
                        key=averaging_params.value_store_key,
                        time=averaging_params.timestamp,
                        value=rate,
                        backlog_minutes=averaging_params.backlog_minutes,
                    )
                )
                is not None
                else None
            ),
        )

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


TInterfaceType = TypeVar("TInterfaceType", InterfaceWithCounters, InterfaceWithRates)


Section = Sequence[TInterfaceType]


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
def _cleanup_if_strings(s: str) -> str:
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


def get_if_state_name(state: str) -> str:
    """return name of the network interface card state.
    on lookup failure returns state.
    Reference: windows SDK ifdef.h, for example"""
    state_to_name: Final[dict[str, str]] = {
        "1": "up",
        "2": "down",
        "3": "testing",
        "4": "unknown",
        "5": "dormant",
        "6": "not present",
        "7": "lower layer down",
        "8": "degraded",
    }
    return state_to_name.get(state, state)


def render_mac_address(phys_address: Iterable[int] | str) -> str:
    if isinstance(phys_address, str):
        mac_bytes = (ord(x) for x in phys_address)
    else:
        mac_bytes = (x for x in phys_address)
    return (":".join(["%02s" % hex(m)[2:] for m in mac_bytes]).replace(" ", "0")).upper()


def matching_interfaces_for_item(
    item: str,
    section: Section[TInterfaceType],
    appearance: _ItemAppearance | None = None,
) -> Iterator[TInterfaceType]:
    if not section:
        return

    if section[0].attributes.node:
        yield from _matching_clustered_interfaces_for_item(item, section, appearance)
        return

    if match := _matching_unclustered_interface_for_item(item, section, appearance):
        yield match


def _matching_clustered_interfaces_for_item(
    item: str,
    section: Section[TInterfaceType],
    appearance: _ItemAppearance | None,
) -> Iterator[TInterfaceType]:
    for _node, node_interfaces in itertools.groupby(
        # itertools.groupby needs the input to be sorted accordingly. This is most likely already
        # the case, at least if we reach this point via cluster_check, but I don't want to rely on
        # it.
        sorted(
            section,
            key=lambda iface: str(iface.attributes.node),
        ),
        key=lambda iface: iface.attributes.node,
    ):
        if match := _matching_unclustered_interface_for_item(
            item, list(node_interfaces), appearance
        ):
            yield match


def _matching_unclustered_interface_for_item(
    item: str,
    section: Section[TInterfaceType],
    appearance: _ItemAppearance | None,
) -> TInterfaceType | None:
    return (
        simple_match
        if (simple_match := _matching_interface_for_simple_item(item, section, appearance))
        else _matching_interface_for_compound_item(item, section, appearance)
    )


def _matching_interface_for_simple_item(
    item: str,
    ifaces: Iterable[TInterfaceType],
    appearance: _ItemAppearance | None,
) -> TInterfaceType | None:
    # Use old matching logic if service has not been rediscovered
    # and appearance is missing from discovered params
    use_old_matching = appearance is None
    return next(
        (
            interface
            for interface in ifaces
            if (
                (appearance == "index" or use_old_matching)
                and (
                    (item.lstrip("0") == interface.attributes.index)
                    or (item == "0" * len(item) and saveint(interface.attributes.index) == 0)
                )
            )
            or ((appearance == "alias" or use_old_matching) and item == interface.attributes.alias)
            or ((appearance == "descr" or use_old_matching) and item == interface.attributes.descr)
        ),
        None,
    )


def _matching_interface_for_compound_item(
    item: str,
    ifaces: Iterable[TInterfaceType],
    appearance: _ItemAppearance | None,
) -> TInterfaceType | None:
    # Use old matching logic if service has not been rediscovered
    # and appearance is missing from discovered params
    use_old_matching = appearance is None
    return next(
        (
            interface
            for interface in ifaces
            if (
                (appearance == "alias" or use_old_matching)
                and item == f"{interface.attributes.alias} {interface.attributes.index}"
            )
            or (
                (appearance == "descr" or use_old_matching)
                and item == f"{interface.attributes.descr} {interface.attributes.index}"
            )
        ),
        None,
    )


# Pads port numbers with zeroes, so that items
# nicely sort alphabetically
def _pad_with_zeroes(
    section: Section[TInterfaceType],
    ifIndex: str,
    pad_portnumbers: bool,
) -> str:
    if pad_portnumbers:
        max_index = max(int(interface.attributes.index) for interface in section)
        digits = len(str(max_index))
        return ("%0" + str(digits) + "d") % int(ifIndex)
    return ifIndex


class BandwidthUnit(enum.IntEnum):
    BYTE = 1
    BIT = 8


@dataclass(frozen=True)
class FixedLevels:
    upper: tuple[float, float] | None
    lower: tuple[float, float] | None


@dataclass(frozen=True)
class PredictiveLevels:
    config: dict[str, Any]


@dataclass(frozen=True)
class BandwidthLevels:
    input: FixedLevels | PredictiveLevels
    output: FixedLevels | PredictiveLevels
    total: FixedLevels | PredictiveLevels


def bandwidth_levels(
    *,
    params: Mapping[str, Any],
    speed_in: float | None,
    speed_out: float | None,
    speed_total: float | None,
    unit: BandwidthUnit,
) -> BandwidthLevels:
    speeds = {
        "in": speed_in,
        "out": speed_out,
        "total": speed_total,
    }
    raw_levels = [
        *params.get("traffic", []),
        *[("total", vs) for vs in params.get("total_traffic", {}).get("levels", [])],
    ]

    merged_levels: dict[
        str,
        PredictiveLevels | dict[str, tuple[float, float] | None],
    ] = {}

    for direction_spec, (levels_type, levels_spec) in raw_levels:
        for direction in ["in", "out"] if direction_spec == "both" else [direction_spec]:
            if levels_type == "predictive":
                merged_levels[direction] = PredictiveLevels(levels_spec)

            else:
                upper_or_lower, thresholds = levels_spec

                if isinstance(
                    levels_direction := merged_levels.get(direction, {}), PredictiveLevels
                ):
                    levels_direction = {}

                levels_direction |= {
                    upper_or_lower: _scaled_bandwidth_thresholds(
                        thresholds_type=levels_type,
                        thresholds=thresholds,
                        speed=speeds[direction],
                        unit=unit,
                    )
                }

                merged_levels[direction] = levels_direction

    return BandwidthLevels(
        input=_finalize_bandwidth_levels(merged_levels.get("in", {})),
        output=_finalize_bandwidth_levels(merged_levels.get("out", {})),
        total=_finalize_bandwidth_levels(merged_levels.get("total", {})),
    )


def _scaled_bandwidth_thresholds(
    *,
    thresholds_type: Literal["abs", "perc"],
    thresholds: tuple[float, float],
    speed: float | None,
    unit: BandwidthUnit,
) -> tuple[float, float] | None:
    """convert percentages to absolute values."""

    def scale(thresholds: tuple[float, float], scale: float) -> tuple[float, float]:
        return thresholds[0] * scale, thresholds[1] * scale

    match thresholds_type:
        case "abs":
            return scale(thresholds, 1 / unit)
        case "perc":
            return scale(thresholds, speed / 100) if speed else None
    assert_never(thresholds_type)


def _finalize_bandwidth_levels(
    merged_direction_levels: PredictiveLevels | Mapping[str, tuple[float, float] | None],
) -> FixedLevels | PredictiveLevels:
    return (
        merged_direction_levels
        if isinstance(merged_direction_levels, PredictiveLevels)
        else FixedLevels(
            upper=merged_direction_levels.get("upper"),
            lower=merged_direction_levels.get("lower"),
        )
    )


GeneralPacketLevels = dict[str, dict[str, tuple[float, float] | None]]


def _get_packet_levels(
    params: Mapping[str, Any],
) -> tuple[GeneralPacketLevels, GeneralPacketLevels]:
    DIRECTIONS = ("in", "out")
    PACKET_TYPES = ("errors", "multicast", "broadcast", "unicast", "discards")

    def none_levels() -> dict[str, dict[str, Any | None]]:
        return {name: {direction: None for direction in DIRECTIONS} for name in PACKET_TYPES}

    levels_per_type = {
        "perc": none_levels(),
        "abs": none_levels(),
    }

    # Second iteration: separate by perc and abs for easier further processing
    for name in PACKET_TYPES:
        for direction in DIRECTIONS:
            levels = params.get(name, {})
            level = levels.get(direction) or levels.get("both")
            if level is not None:
                levels_per_type[level[0]][name][direction] = level[1]

    return levels_per_type["abs"], levels_per_type["perc"]


@dataclass(frozen=True)
class ItemInfo:
    used_appearance: _ItemAppearance
    item: str


def _compute_item(
    configured_item_appearance: _ItemAppearance,
    attributes: Attributes,
    section: Section[TInterfaceType],
    pad_portnumbers: bool,
) -> ItemInfo:
    match configured_item_appearance:
        case "descr":
            if attributes.descr:
                return ItemInfo(
                    used_appearance="descr",
                    item=attributes.descr,
                )
        case "alias":
            if attributes.alias:
                return ItemInfo(
                    used_appearance="alias",
                    item=attributes.alias,
                )

    return ItemInfo(
        used_appearance="index",
        item=_pad_with_zeroes(section, attributes.index, pad_portnumbers),
    )


def check_regex_match_conditions(
    name: str,
    what: Iterable[str] | None,
) -> bool:
    if what is None:
        return True
    for r in what:
        if re.match(r, name):
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
    member_appearance: _ItemAppearance
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
) -> dict[str, GroupConfiguration]:
    groups: dict[str, GroupConfiguration] = {}
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


def discover_interfaces(
    params: Sequence[Mapping[str, Any]],
    section: Section[TInterfaceType],
) -> DiscoveryResult:
    if len(section) == 0:
        return

    pre_inventory = []
    seen_indices: set[str] = set()
    n_times_item_seen: dict[str, int] = defaultdict(int)
    interface_groups: dict[str, GroupConfiguration] = {}

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

        for appearance in (
            ["index", "descr", "alias"]
            if interface.attributes.descr != interface.attributes.alias
            else ["index", "descr"]
        ):
            n_times_item_seen[
                _compute_item(
                    _to_item_appearance(appearance),
                    interface.attributes,
                    section,
                    pad_portnumbers,
                ).item
            ] += 1

        # compute actual item name
        item_info = _compute_item(
            _to_item_appearance(single_interface_settings["item_appearance"])
            if "item_appearance" in single_interface_settings
            else (DISCOVERY_DEFAULT_PARAMETERS["discovery_single"][1]["item_appearance"]),
            interface.attributes,
            section,
            pad_portnumbers,
        )
        item = item_info.item

        # discover single interface
        if discover_single_interface and interface.attributes.index not in seen_indices:
            discovered_params_single: dict[str, object] = {
                "item_appearance": item_info.used_appearance,
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
                    "member_appearance": (
                        _to_item_appearance(single_interface_settings["item_appearance"])
                        if "item_appearance" in single_interface_settings
                        else "index"
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

        # Extract labels, they will be handled separately.
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


GroupMembers = dict[str | None, list[MemberInfo]]


def _check_ungrouped_ifs(
    item: str,
    params: Mapping[str, Any],
    section: Section[TInterfaceType],
    timestamps: Sequence[float],
    value_store: MutableMapping[str, Any],
) -> CheckResult:
    """
    Check one or more ungrouped interfaces. In a non-cluster setup, only one interface will match
    the item and the results will simply be the output of check_single_interface. On a cluster,
    multiple interfaces can match. In this case, only the results from the interface with the
    highest outgoing traffic will be reported (since the corresponding node is likely the master).
    """
    last_results = None
    results_from_fastest_interface = None
    max_out_traffic = -1.0
    item_appearance = (
        _to_item_appearance(params["item_appearance"]) if "item_appearance" in params else None
    )
    for timestamp, interface in zip(
        timestamps, matching_interfaces_for_item(item, section, item_appearance)
    ):
        last_results = list(
            check_single_interface(
                item,
                params,
                InterfaceWithRatesAndAverages.from_interface_with_counters_or_rates(
                    interface,
                    timestamp=timestamp,
                    value_store=value_store,
                    params=params,
                ),
                use_discovered_state_and_speed=interface.attributes.node is None,
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


def _accumulate_attributes(
    *,
    matching_attributes: Collection[Attributes],
    item: str,
    group_config: GroupConfiguration,
) -> Attributes:
    cumulated_attributes = Attributes(
        index=item,
        descr=item,
        alias="",
        type="",
        out_qlen=0,
    )
    num_up = 0
    nodes = set()

    for attributes in matching_attributes:
        nodes.add(str(attributes.node))
        if attributes.is_up:
            num_up += 1

        # Add interface info to group info
        if attributes.is_up:
            cumulated_attributes.speed += attributes.speed
            cumulated_attributes.out_qlen = _sum_optional_floats(
                cumulated_attributes.out_qlen,
                attributes.out_qlen,
            )

        # This is the fallback ifType if None is set in the parameters
        cumulated_attributes.type = attributes.type

    if num_up == len(matching_attributes):
        cumulated_attributes.oper_status = cumulated_attributes.oper_status_up  # up
    elif num_up > 0:
        cumulated_attributes.oper_status = "8"  # degraded
    else:
        cumulated_attributes.oper_status = "2"  # down
        cumulated_attributes.out_qlen = None
    cumulated_attributes.oper_status_name = get_if_state_name(cumulated_attributes.oper_status)

    alias_info = []
    if len(nodes) > 1:
        alias_info.append("nodes: %s" % ", ".join(nodes))

    # From pre-2.0
    if (iftype := group_config.get("iftype")) is not None:
        alias_info.append("type: %s" % iftype)
    if group_config.get("items"):
        alias_info.append("%d grouped interfaces" % len(matching_attributes))

    cumulated_attributes.alias = ", ".join(alias_info)

    return cumulated_attributes


def _accumulate_rates_with_averages(
    matching_interfaces: Iterable[InterfaceWithRatesAndAverages],
) -> RatesWithAverages:
    return (
        sum(
            data_of_up_interfaces[1:],
            start=data_of_up_interfaces[0],
        )
        if (
            data_of_up_interfaces := [
                iface.rates_with_averages for iface in matching_interfaces if iface.attributes.is_up
            ]
        )
        else RatesWithAverages()
    )


def _accumulate_get_rate_errors(
    matching_interfaces: Iterable[InterfaceWithRatesAndAverages],
) -> Sequence[tuple[str, GetRateError]]:
    return list(
        itertools.chain.from_iterable(
            iface.get_rate_errors for iface in matching_interfaces if iface.attributes.is_up
        )
    )


def _group_members(
    *,
    matching_attributes: Iterable[Attributes],
    item: str,
    group_config: GroupConfiguration,
    section: Section[TInterfaceType],
) -> GroupMembers:
    group_members: GroupMembers = {}
    for attributes in matching_attributes:
        groups_node = group_members.setdefault(attributes.node, [])
        member_info = MemberInfo(
            name=_compute_item(
                # This happens when someones upgrades from v1.6 to v2,0, where the structure of the
                # discovered parameters changed. Interface groups defined by the user will stop
                # working, users have to do a re-discovery in that case, as we wrote in werk #11361.
                # However, we can still support groups defined already in the agent output, since
                # these work purley by the group name.
                group_config["member_appearance"]
                if "member_appearance" in group_config
                else _to_item_appearance(
                    str(
                        group_config.get(
                            "item_type",
                            DISCOVERY_DEFAULT_PARAMETERS["discovery_single"][1]["item_appearance"],
                        )
                    )
                ),
                attributes,
                section,
                item[0] == "0",
            ).item,
            oper_status_name=attributes.oper_status_name,
            admin_status_name=(
                None
                if attributes.admin_status is None
                else get_if_state_name(attributes.admin_status)
            ),
        )
        groups_node.append(member_info)
    return group_members


def _check_grouped_ifs(
    item: str,
    params: Mapping[str, Any],
    section: Section[TInterfaceType],
    group_name: str,
    timestamps: Sequence[float],
    value_store: MutableMapping[str, Any],
) -> CheckResult:
    """
    Grouped interfaces are combined into a single interface, which is then passed to
    check_single_interface.
    """
    matching_interfaces = [
        InterfaceWithRatesAndAverages.from_interface_with_counters_or_rates(
            iface,
            timestamp=timestamp,
            value_store=value_store,
            params=params,
        )
        for timestamp, iface in zip(timestamps, section)
        if _check_group_matching_conditions(
            iface.attributes,
            item,
            params["aggregate"],
        )
    ]
    yield from check_single_interface(
        item,
        params,
        InterfaceWithRatesAndAverages(
            attributes=_accumulate_attributes(
                matching_attributes=[iface.attributes for iface in matching_interfaces],
                item=item,
                group_config=params["aggregate"],
            ),
            rates_with_averages=_accumulate_rates_with_averages(matching_interfaces),
            get_rate_errors=_accumulate_get_rate_errors(matching_interfaces),
        ),
        group_members=_group_members(
            matching_attributes=(iface.attributes for iface in matching_interfaces),
            item=item,
            group_config=params["aggregate"],
            section=section,
        ),
        group_name=group_name,
        # the discovered speed corresponds to only one of the nodes, so it cannot be used for
        # interface groups on clusters; same for state
        use_discovered_state_and_speed=section[0].attributes.node is None,
    )


def check_multiple_interfaces(
    item: str,
    params: Mapping[str, Any],
    section: Section[TInterfaceType],
    *,
    group_name: str = "Interface group",
    timestamps: Sequence[float] | None = None,
    value_store: MutableMapping[str, Any] | None = None,
) -> CheckResult:
    if timestamps is not None:
        timestamps_f = timestamps
    else:
        now = time.time()
        timestamps_f = [now] * len(section)
    if value_store is None:
        value_store = get_value_store()

    if "aggregate" in params:
        yield from _check_grouped_ifs(
            item,
            params,
            section,
            group_name,
            timestamps_f,
            value_store,
        )
    else:
        yield from _check_ungrouped_ifs(
            item,
            params,
            section,
            timestamps_f,
            value_store,
        )


def _get_map_states(defined_mapping: Iterable[tuple[Iterable[str], int]]) -> Mapping[str, State]:
    map_states = {}
    for states, mon_state in defined_mapping:
        for st in states:
            map_states[st] = State(mon_state)
    return map_states


def _check_status(
    interface_status: str,
    target_states: Container[str] | None,
    states_map: Mapping[str, State],
) -> State:
    mon_state = State.OK
    if target_states is not None and interface_status not in target_states:
        mon_state = State.CRIT
    mon_state = states_map.get(interface_status, mon_state)
    return mon_state


def _check_speed(attributes: Attributes, targetspeed: int | None) -> Result:
    """Check speed settings of interface

    Only if speed information is available. This is not always the case.
    """
    if attributes.speed:
        speed_actual = render.nicspeed(attributes.speed / BandwidthUnit.BIT)
        speed_expected = (
            ""
            if (targetspeed is None or int(attributes.speed) == targetspeed)
            else " (expected: %s)" % render.nicspeed(targetspeed / BandwidthUnit.BIT)
        )
        return Result(
            state=State.WARN if speed_expected else State.OK,
            summary=f"Speed: {speed_actual}{speed_expected}",
        )

    if targetspeed:
        return Result(
            state=State.OK,
            summary="Speed: %s (assumed)" % render.nicspeed(targetspeed / BandwidthUnit.BIT),
        )

    return Result(state=State.OK, summary="Speed: %s" % (attributes.speed_as_text or "unknown"))


_TCheckInterfaceParams = ParamSpec("_TCheckInterfaceParams")


_METRICS_TO_LEGACY_MAP = {
    "if_in_discards": "indisc",
    "if_in_errors": "inerr",
    "if_out_discards": "outdisc",
    "if_out_errors": "outerr",
    "if_in_mcast": "inmcast",
    "if_in_bcast": "inbcast",
    "if_out_mcast": "outmcast",
    "if_out_bcast": "outbcast",
    "if_in_unicast": "inucast",
    "if_in_non_unicast": "innucast",
    "if_out_unicast": "outucast",
    "if_out_non_unicast": "outnucast",
}


# This is a workaround for the following problem: livestatus in combination with the Nagios core
# only reports those metrics which are currently still updated. Metrics which were once produced but
# are not updated anylonger are currently not reported in the livestatus metrics column. Hence,
# renaming metrics currently leads to a loss of historic data in the CRE, even if there is a
# corresponding translation. This issue will hopefully be eliminated in the 2.3. Once this is the
# case, we can remove _rename_metrics_to_legacy.
def _rename_metrics_to_legacy(
    check_interfaces: Callable[_TCheckInterfaceParams, CheckResult],
) -> Callable[_TCheckInterfaceParams, CheckResult]:
    def rename_metrics_to_legacy(
        *args: _TCheckInterfaceParams.args,
        **kwargs: _TCheckInterfaceParams.kwargs,
    ) -> CheckResult:
        yield from (
            (
                Metric(
                    name=_METRICS_TO_LEGACY_MAP.get(
                        output.name,
                        output.name,
                    ),
                    value=output.value,
                    levels=output.levels,
                    boundaries=output.boundaries,
                )
                if isinstance(output, Metric)
                else output
            )
            for output in check_interfaces(*args, **kwargs)
        )

    return rename_metrics_to_legacy


@_rename_metrics_to_legacy
def check_single_interface(
    item: str,
    params: Mapping[str, Any],
    interface: InterfaceWithRatesAndAverages,
    group_members: GroupMembers | None = None,
    *,
    group_name: str = "Interface group",
    use_discovered_state_and_speed: bool = True,
) -> CheckResult:
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

    if use_discovered_state_and_speed:
        targetspeed: int | None = params.get("speed", params.get("discovered_speed"))
    else:
        targetspeed = params.get("speed")

    yield _check_speed(interface.attributes, targetspeed)

    assumed_speed_in: int | None = params.get("assumed_speed_in")
    assumed_speed_out: int | None = params.get("assumed_speed_out")
    bandwidth_unit = (
        BandwidthUnit.BIT if params.get("unit") in ["Bit", "bit"] else BandwidthUnit.BYTE
    )

    # prepare reference speed for computing relative bandwidth usage
    ref_speed = None
    if interface.attributes.speed:
        ref_speed = interface.attributes.speed / BandwidthUnit.BIT
    elif targetspeed:
        ref_speed = targetspeed / BandwidthUnit.BIT

    # Speed in bytes
    speed_b_in = (assumed_speed_in // BandwidthUnit.BIT) if assumed_speed_in else ref_speed
    speed_b_out = (assumed_speed_out // BandwidthUnit.BIT) if assumed_speed_out else ref_speed
    speed_b_total = speed_b_in + speed_b_out if speed_b_in and speed_b_out else None

    # Compute levels
    bw_levels = bandwidth_levels(
        params=params,
        speed_in=speed_b_in,
        speed_out=speed_b_out,
        speed_total=speed_b_total,
        unit=bandwidth_unit,
    )
    abs_packet_levels, perc_packet_levels = _get_packet_levels(params)

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

    if interface.attributes.out_qlen is not None:
        yield Metric(
            "outqlen",
            interface.attributes.out_qlen,
        )

    yield from _output_bandwidth_rates(
        rates=interface.rates_with_averages,
        speed_b_in=speed_b_in,
        speed_b_out=speed_b_out,
        speed_b_total=speed_b_total,
        unit=bandwidth_unit,
        levels=bw_levels,
        assumed_speed_in=assumed_speed_in,
        assumed_speed_out=assumed_speed_out,
        monitor_total="total_traffic" in params,
    )

    yield from _output_packet_rates(
        abs_packet_levels=abs_packet_levels,
        perc_packet_levels=perc_packet_levels,
        nucast_levels=params.get("nucasts"),
        rates=interface.rates_with_averages,
    )

    if interface.get_rate_errors:
        overflows_human_readable = "\n".join(
            f"{counter}: {get_rate_excpt}" for counter, get_rate_excpt in interface.get_rate_errors
        )
        yield Result(
            state=State.OK,
            notice=f"Could not compute rates for the following counter(s):\n{overflows_human_readable}",
        )


def _interface_name(
    *,
    group_name: str | None,
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
    # Display port number or alias in summary_interface if that is not part of the service
    # description anyway
    elif (
        (item == attributes.index or item.lstrip("0") == attributes.index)
        and attributes.alias in (item, "")
        and attributes.descr in (item, "")
    ):  # description trivial
        info_interface = ""
    elif (
        item == f"{attributes.alias} {attributes.index}" and attributes.descr != ""
    ):  # non-unique Alias
        info_interface = f"[{attributes.alias}/{attributes.descr}]"
    elif attributes.alias not in (item, ""):  # alias useful
        info_interface = "[%s]" % attributes.alias
    elif attributes.descr not in (item, ""):  # description useful
        info_interface = "[%s]" % attributes.descr
    else:
        info_interface = "[%s]" % attributes.index

    if attributes.node is not None:
        if info_interface:
            info_interface = f"{info_interface} on {attributes.node}"
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


def _parse_params(
    state_mappings: tuple[Literal["independent_mappings", "combined_mappings"], Any],
) -> StateMappings:
    match state_mappings:
        case "independent_mappings", mapping:
            return IndependentMapping.model_validate(mapping)
        case "combined_mappings", mapping:
            return CombinedMapping(mapping)
    raise ValueError(f"Unknown state_mappings: {state_mappings}")


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

    state_mappings = (
        _parse_params(params["state_mappings"])
        if "state_mappings" in params
        else IndependentMapping()
    )
    yield from _check_oper_and_admin_state(
        attributes,
        state_mappings=state_mappings,
        target_oper_states=target_oper_states,
        target_admin_states=target_admin_states,
    )


def _check_oper_and_admin_state(
    attributes: Attributes,
    state_mappings: StateMappings,
    target_oper_states: Container[str] | None,
    target_admin_states: Container[str] | None,
) -> Iterable[Result]:
    if isinstance(state_mappings, CombinedMapping):
        combined_mon_state = __oper_and_admin_state_combined(attributes, state_mappings)
        if combined_mon_state is not None and attributes.admin_status is not None:
            yield Result(
                state=combined_mon_state,
                summary=f"(op. state: {attributes.oper_status_name}, admin state: {get_if_state_name(attributes.admin_status)})",
                details=f"Operational state: {attributes.oper_status_name}, Admin state: {get_if_state_name(attributes.admin_status)}",
            )
            return
    yield from _check_oper_and_admin_state_independent(
        attributes,
        target_oper_states=target_oper_states,
        target_admin_states=target_admin_states,
        mapping=_get_oper_and_admin_states_maps_independent(state_mappings),
    )


def _get_oper_and_admin_states_maps_independent(
    state_mappings: StateMappings,
) -> IndependentMapping:
    if isinstance(state_mappings, IndependentMapping):
        return state_mappings
    return IndependentMapping()


def _check_oper_and_admin_state_independent(
    attributes: Attributes,
    target_oper_states: Container[str] | None,
    target_admin_states: Container[str] | None,
    mapping: IndependentMapping,
) -> Iterable[Result]:
    yield Result(
        state=_check_status(
            attributes.oper_status,
            target_oper_states,
            _get_map_states(mapping.map_operstates),
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
            _get_map_states(mapping.map_admin_states),
        ),
        summary=f"Admin state: {get_if_state_name(attributes.admin_status)}",
    )


def __oper_and_admin_state_combined(
    attributes: Attributes, state_mappings: CombinedMapping
) -> State | None:
    for oper_state, admin_state, mon_state in state_mappings:
        if attributes.oper_status == oper_state and attributes.admin_status == admin_state:
            return State(mon_state)
    return None


def _output_group_members(
    *,
    group_members: GroupMembers | None,
) -> Iterable[Result]:
    if not group_members:
        return

    infos_group = []
    for group_node, members in group_members.items():
        member_info = []
        for member in members:
            member_info.append(str(member))

        nodeinfo = ""
        if group_node is not None and len(group_members) > 1:
            nodeinfo = " on node %s" % group_node
        infos_group.append("[{}{}]".format(", ".join(member_info), nodeinfo))

    yield Result(
        state=State.OK,
        summary="Members: %s" % " ".join(infos_group),
    )


def _output_bandwidth_rates(
    *,
    rates: RatesWithAverages,
    speed_b_in: float | None,
    speed_b_out: float | None,
    speed_b_total: float | None,
    unit: BandwidthUnit,
    levels: BandwidthLevels,
    assumed_speed_in: int | None,
    assumed_speed_out: int | None,
    monitor_total: bool,
) -> CheckResult:
    if unit is BandwidthUnit.BIT:
        bandwidth_renderer: Callable[[float], str] = render.nicspeed
    else:
        bandwidth_renderer = render.iobandwidth

    for direction, traffic, speed, direction_levels in [
        ("in", rates.in_octets, speed_b_in, levels.input),
        ("out", rates.out_octets, speed_b_out, levels.output),
        *(
            [
                (
                    "total",
                    rates.total_octets,
                    speed_b_total,
                    levels.total,
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
            levels=direction_levels,
            assumed_speed_in=assumed_speed_in,
            assumed_speed_out=assumed_speed_out,
        )


def _check_single_bandwidth(
    *,
    direction: str,
    traffic: RateWithAverage,
    speed: float | None,
    renderer: Callable[[float], str],
    levels: FixedLevels | PredictiveLevels,
    assumed_speed_in: int | None,
    assumed_speed_out: int | None,
) -> CheckResult:
    if traffic.average:
        filtered_traffic = traffic.average.value
        title = "%s average %dmin" % (direction.title(), traffic.average.backlog)
    else:
        filtered_traffic = traffic.rate
        title = direction.title()

    if isinstance(levels, PredictiveLevels):
        if traffic.average:
            dsname = "%s_avg_%d" % (direction, traffic.average.backlog)
        else:
            dsname = direction

        result, metric_from_pred_check, *ref_curve = check_levels_predictive(
            filtered_traffic,
            levels=levels.config,
            metric_name=dsname,
            render_func=renderer,
            label=title,
        )
        assert isinstance(result, Result)

        if traffic.average:
            # The avg is not needed for displaying a graph, but it's historic
            # value will be needed for the future calculation of the ref_curve,
            # so we can't dump it.
            yield metric_from_pred_check

        yield from ref_curve  # reference curve for predictive levels
    else:
        # The metric already got yielded, so it's only the result that is
        # needed here.
        (result,) = check_levels_v1(
            filtered_traffic,
            levels_upper=levels.upper,
            levels_lower=levels.lower,
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
            summary=f"{result.summary} ({perc_info})",
        )
    else:
        yield result

    # output metric after result. this makes it easier to analyze the check output,
    # as this is the "normal" order when yielding from check_levels_fixed.
    # Note: we always yield the unaveraged values here, since this is what we want to display in
    # our graphs
    yield Metric(
        direction,
        traffic.rate,
        levels=levels.upper if isinstance(levels, FixedLevels) else None,
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

    if abs(value) < float(tol := f"0.{'0' * (precision - 1)}1"):
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
    *,
    abs_packet_levels: GeneralPacketLevels,
    perc_packet_levels: GeneralPacketLevels,
    nucast_levels: tuple[float, float] | None,
    rates: RatesWithAverages,
) -> CheckResult:
    for direction, mrate, brate, urate, nurate, discrate, errorrate in [
        (
            "in",
            rates.in_mcast,
            rates.in_bcast,
            rates.in_ucast,
            rates.in_nucast,
            rates.in_disc,
            rates.in_err,
        ),
        (
            "out",
            rates.out_mcast,
            rates.out_bcast,
            rates.out_ucast,
            rates.out_nucast,
            rates.out_disc,
            rates.out_err,
        ),
    ]:
        all_pacrate = _sum_optional_floats(
            urate.rate if urate else None,
            nurate.rate if nurate else None,
            errorrate.rate if errorrate else None,
        )
        success_pacrate = _sum_optional_floats(
            urate.rate if urate else None,
            nurate.rate if nurate else None,
        )
        for rate, abs_levels, perc_levels, display_name, metric_name, reference_rate in [
            (
                errorrate,
                abs_packet_levels["errors"][direction],
                perc_packet_levels["errors"][direction],
                "errors",
                "errors",
                all_pacrate,
            ),
            (
                discrate,
                abs_packet_levels["discards"][direction],
                perc_packet_levels["discards"][direction],
                "discards",
                "discards",
                _sum_optional_floats(
                    urate.rate if urate else None,
                    nurate.rate if nurate else None,
                    discrate.rate if discrate else None,
                ),
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
                "unicast",
                success_pacrate,
            ),
        ]:
            if rate is None:
                continue

            yield from _check_single_packet_rate(
                packets=rate,
                direction=direction,
                abs_levels=abs_levels,
                perc_levels=perc_levels,
                display_name=display_name,
                metric_name=metric_name,
                reference_rate=reference_rate,
            )

        for display_name, metric_name, packets, levels in [
            ("Non-unicast", "non_unicast", nurate, nucast_levels),
        ]:
            if packets is None:
                continue
            yield from check_levels_v1(
                packets.rate,
                levels_upper=levels,
                metric_name=f"if_{direction}_{metric_name}",
                render_func=partial(_render_floating_point, precision=2, unit=" packets/s"),
                label=f"{display_name} {direction}",
                notice_only=True,
            )


def _check_single_packet_rate(
    *,
    packets: RateWithAverage,
    direction: str,
    abs_levels: Any,
    perc_levels: Any,
    display_name: str,
    metric_name: str,
    reference_rate: float | None,
) -> CheckResult:
    # Calculate the metric with actual levels, no matter if they
    # come from perc_- or abs_levels
    if perc_levels is not None:
        if reference_rate is None:
            return
        if reference_rate > 0:
            merged_levels: tuple[float, float] | None = (
                perc_levels[0] / 100.0 * reference_rate,
                perc_levels[1] / 100.0 * reference_rate,
            )
        else:
            merged_levels = None
    else:
        merged_levels = abs_levels

    # Further calculation now precedes with average value,
    # if requested.
    infotxt = f"{display_name.title()} {direction}"
    if packets.average:
        infotxt += f" average {packets.average.backlog}min"
        rate_check = packets.average.value
    else:
        rate_check = packets.rate

    if perc_levels is not None:
        if reference_rate is None:
            return
        # Note: A rate of 0% for a pacrate of 0 is mathematically incorrect,
        # but it yields the best information for the "no packets" case in the check output.
        perc_value = 0 if reference_rate == 0 else rate_check * 100 / reference_rate
        (result,) = check_levels_v1(
            perc_value,
            levels_upper=perc_levels,
            render_func=partial(_render_floating_point, precision=3, unit="%"),
            label=infotxt,
            notice_only=True,
        )
        yield result
    else:
        (result,) = check_levels_v1(
            rate_check,
            levels_upper=abs_levels,
            render_func=partial(_render_floating_point, precision=2, unit=" packets/s"),
            label=infotxt,
            notice_only=True,
        )
        yield result

    # output metric after result. this makes it easier to analyze the check output,
    # as this is the "normal" order when yielding from check_levels_fixed.
    # Note: we always yield the unaveraged values here, since this is what we want to display in
    # our graphs
    yield Metric(
        f"if_{direction}_{metric_name}",
        packets.rate,
        levels=merged_levels,
    )


def cluster_check(
    item: str,
    params: Mapping[str, Any],
    section: Mapping[str, Section[TInterfaceType] | None],
) -> CheckResult:
    yield from check_multiple_interfaces(
        item,
        params,
        [
            replace(
                iface,
                attributes=replace(
                    iface.attributes,
                    node=node,
                ),
            )
            for node, node_ifaces in section.items()
            for iface in node_ifaces or ()
        ],
    )
