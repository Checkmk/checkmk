# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
"""Inventory-only SNMP types and capability names shared by hardware tables."""

from collections.abc import Sequence
from typing import Annotated, Protocol

from pydantic import BeforeValidator

# Missing optional columns on older firmware are unknown, never fabricated zero/False.
type InventoryInteger = Annotated[int | None, BeforeValidator(lambda value: None if value == "" else value)]
type InventoryTruthValue = Annotated[
    bool | None,
    BeforeValidator(lambda value: {"1": True, "2": False, "": None}.get(value, value)),
]

# PDU2-MIB enumerations; unknown future codes remain visible in the UI.
SENSOR_TYPES = {
    1: "rmsCurrent",
    2: "peakCurrent",
    3: "unbalancedCurrent",
    4: "rmsVoltage",
    5: "activePower",
    6: "apparentPower",
    7: "powerFactor",
    8: "activeEnergy",
    9: "apparentEnergy",
    10: "temperature",
    11: "humidity",
    12: "airFlow",
    13: "airPressure",
    14: "onOff",
    15: "trip",
    16: "vibration",
    17: "waterDetection",
    18: "smokeDetection",
    19: "binary",
    20: "contact",
    21: "fanSpeed",
    22: "surgeProtectorStatus",
    23: "frequency",
    24: "phaseAngle",
    25: "rmsVoltageLN",
    26: "residualCurrent",
    27: "rcmState",
    28: "absoluteHumidity",
    29: "reactivePower",
    30: "other",
    31: "none",
    32: "powerQuality",
    33: "overloadStatus",
    34: "overheatStatus",
    35: "displacementPowerFactor",
    36: "residualDcCurrent",
    37: "fanStatus",
    38: "inletPhaseSyncAngle",
    39: "inletPhaseSync",
    40: "operatingState",
    41: "activeInlet",
    42: "illuminance",
    43: "doorContact",
    44: "tamperDetection",
    45: "motionDetection",
    46: "i1smpsStatus",
    47: "i2smpsStatus",
    48: "switchStatus",
    49: "doorLockState",
    50: "doorHandleLock",
    51: "crestFactor",
    52: "length",
    53: "distance",
    54: "activePowerDemand",
    55: "residualAcCurrent",
    56: "particleDensity",
    57: "voltageThd",
    58: "currentThd",
    59: "inrushCurrent",
    60: "unbalancedVoltage",
    61: "unbalancedLineLineCurrent",
    62: "unbalancedLineLineVoltage",
    63: "dewPoint",
    64: "mass",
    65: "flux",
    66: "luminousIntensity",
    67: "luminousEnergy",
    68: "luminousFlux",
    69: "luminousEmittance",
    70: "electricalResistance",
    71: "electricalImpedance",
    72: "totalHarmonicDistortion",
    73: "magneticFieldStrength",
    74: "magneticFluxDensity",
    75: "electricFieldStrength",
    76: "selection",
    77: "rotationalSpeed",
    78: "transferSwitchBypassState",
    79: "batteryLevel",
    80: "installFaultStatus",
    81: "transferSwitchOutputStatus",
}

SENSOR_UNITS = {
    -1: "none",
    0: "other",
    1: "volt",
    2: "amp",
    3: "watt",
    4: "voltamp",
    5: "wattHour",
    6: "voltampHour",
    7: "degreeC",
    8: "hertz",
    9: "percent",
    10: "meterpersec",
    11: "pascal",
    12: "psi",
    13: "g",
    14: "degreeF",
    15: "feet",
    16: "inches",
    17: "cm",
    18: "meters",
    19: "rpm",
    20: "degrees",
    21: "lux",
    22: "grampercubicmeter",
    23: "var",
    24: "feetpersec",
    25: "lbspercubicfoot",
    26: "microgrampercubicmeter",
    27: "hour",
    28: "minute",
    29: "second",
    30: "coulomb",
    31: "kelvin",
    32: "voltAmpReactiveHour",
    33: "voltPerAmpere",
    34: "voltPerMeter",
    35: "gram",
    36: "meterPerSquareSec",
    37: "litersPerHour",
    38: "nit",
    39: "candela",
    40: "lumen",
    41: "lumenSecond",
    42: "cubicMeter",
    43: "radiant",
    44: "steradiant",
    45: "newton",
    46: "joule",
    47: "ohm",
    48: "tesla",
    49: "henry",
    50: "farad",
    51: "mol",
    52: "becquerel",
    53: "gray",
    54: "sievert",
}


def sensor_capabilities(value: str | Sequence[int]) -> str:
    """Connector capability bit n corresponds to SensorTypeEnumeration n+1.

    Checkmk OIDBytes supplies octets. SNMP BITS are most-significant-bit first;
    retain unknown future bits rather than silently dropping hardware features.
    """
    octets = value.encode("latin-1") if isinstance(value, str) else value
    return ", ".join(
        SENSOR_TYPES.get(byte_index * 8 + bit + 1, f"bit {byte_index * 8 + bit}")
        for byte_index, octet in enumerate(octets)
        for bit in range(8)
        if octet & (0x80 >> bit)
    )


type InventoryCapabilities = Annotated[str, BeforeValidator(sensor_capabilities)]


class PowerSourceConfiguration(Protocol):
    """Identity and display fields shared by inlet, protector and switch rows."""

    @property
    def index(self) -> str: ...

    @property
    def label(self) -> str: ...

    @property
    def name(self) -> str: ...


def power_source_names(
    inlets: Sequence[PowerSourceConfiguration] | None,
    protectors: Sequence[PowerSourceConfiguration] | None,
    transfer_switches: Sequence[PowerSourceConfiguration] | None,
) -> dict[str, tuple[int, str]]:
    """Map complete PDU2-MIB label OIDs to immediate hardware sources.

    outletPowerSource and overCurrentProtectorPowerSource document references
    to inletLabel, overCurrentProtectorLabel or transferSwitchLabel.
    transferSwitchPowerSource1/2 normally reference overCurrentProtectorLabel.
    Include the table, label column and full PDU/component index; equal numeric
    suffixes in other tables must never resolve to the wrong component.
    """
    names = {}
    for prefix, kind, rows in (
        ("1.3.6.1.4.1.13742.6.3.3.3.1.2", "Inlet", inlets),
        ("1.3.6.1.4.1.13742.6.3.4.3.1.2", "Overcurrent Protector", protectors),
        ("1.3.6.1.4.1.13742.6.3.9.3.1.2", "Transfer Switch", transfer_switches),
    ):
        for row in rows or ():
            pdu, component = row.index.split(".")
            label = row.label or row.name or component
            names[f"{prefix}.{row.index}"] = (int(pdu), f"{kind}: {label}")
    return names


def resolve_power_source(oid: str, names: dict[str, tuple[int, str]], pdu_id: int) -> str:
    """Keep unresolved OIDs and distinguish references to another linked PDU.

    Resolve only the immediate source, so loops in device wiring references
    cannot cause recursion. Both leading-dot and plain numeric OIDs work.
    """
    if (source := names.get(oid.strip().lstrip("."))) is None:
        return oid
    source_pdu, label = source
    return label if source_pdu == pdu_id else f"{label} (PDU {source_pdu})"
