#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from typing import Final, NamedTuple, TypeVar

from cmk.agent_based.v2 import Result, State

type RawState = str
type StateLabel = str

_ABBREVIATIONS: Final[dict[RawState, StateLabel]] = {
    "awb": "Always WriteBack",
    "b": "Blocked",
    "cac": "CacheCade",
    "cbshld": "Copyback Shielded",
    "c": "Cached IO",
    "cfshld": "Configured shielded",
    "consist": "Consistent",
    "cpybck": "CopyBack",
    "dg": "Drive Group",
    "dgrd": "Degraded",
    "dhs": "Dedicated Hot Spare",
    "did": "Device ID",
    "eid": "Enclosure Device ID",
    "f": "Foreign",
    "ghs": "Global Hot Spare",
    "hd": "Hidden",
    "hspshld": "Hot Spare shielded",
    "intf": "Interface",
    "med": "Media Type",
    "nr": "No Read Ahead",
    "offln": "Offline",
    "ofln": "OffLine",
    "onln": "Online",
    "optl": "Optimal",
    "pdgd": "Partially Degraded",
    "pi": "Protection Info",
    "rec": "Recovery",
    "ro": "Read Only",
    "r": "Read Ahead Always",
    "rw": "Read Write",
    "scc": "Scheduled Check Consistency",
    "sed": "Self Encryptive Drive",
    "sesz": "Sector Size",
    "slt": "Slot No.",
    "sp": "Spun",
    "trans": "TransportReady",
    "t": "Transition",
    "ubad": "Unconfigured Bad",
    "ubunsp": "Unconfigured Bad Unsupported",
    "ugood": "Unconfigured Good",
    "ugshld": "Unconfigured shielded",
    "ugunsp": "Unsupported",
    "u": "Up",
    "vd": "Virtual Drive",
    "wb": "WriteBack",
    "wt": "WriteThrough",
}


class LDisk(NamedTuple):
    state: str
    default_cache: str | None = None
    current_cache: str | None = None
    default_write: str | None = None
    current_write: str | None = None


SectionLDisks = Mapping[str, LDisk]


class PDisk(NamedTuple):
    name: str
    state: str
    failures: int | None


SectionPDisks = Mapping[str, PDisk]


_T = TypeVar("_T")


def check_state(mismatch_state: State, label: str, actual: _T, expected: _T) -> Result:
    """
    >>> check_state(State.WARN, "socks", "white", "black")
    Result(state=<State.WARN: 1>, summary='Socks: white (expected: black)')
    """
    short = f"{label.capitalize()}: {actual}"
    if actual == expected:
        return Result(state=State.OK, summary=short)
    return Result(state=mismatch_state, summary=f"{short} (expected: {expected})")


PDISKS_DEFAULTS: Final[dict[RawState, int]] = {
    "dhs": State.OK.value,
    "ghs": State.OK.value,
    "ugood": State.OK.value,
    "ubad": State.WARN.value,
    "onln": State.OK.value,
    "ofln": State.WARN.value,
    "jbod": State.OK.value,
}


LDISKS_DEFAULTS: Final = {
    "Optimal": 0,
    "Partially Degraded": 1,
    "Degraded": 2,
    "Offline": 1,
    "Recovery": 1,
}


def expand_abbreviation(short: RawState) -> StateLabel:
    """
    >>> expand_abbreviation('Optl')
    'Optimal'
    >>> expand_abbreviation('Whatever')
    'Whatever'
    """
    return _ABBREVIATIONS.get(short.lower(), short)
