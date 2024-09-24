#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Detection specifications"""

import itertools
import re

_SNMPDetectBaseType = list[list[tuple[str, str, bool]]]


class SNMPDetectSpecification(_SNMPDetectBaseType):
    """A specification for SNMP device detection

    Note that the structure of this object is not part of the API,
    and may change at any time.
    """

    # This class is only part of the check *API*, in the sense that it hides
    # the SNMPDetectBaseType from the user (and from the auto generated doc!).
    # Use it for type annotations API frontend objects


def all_of(
    spec_0: SNMPDetectSpecification,
    spec_1: SNMPDetectSpecification,
    *specs: SNMPDetectSpecification,
) -> SNMPDetectSpecification:
    """Detect the device if all passed specifications are met

    Args:
        spec_0: A valid specification for SNMP device detection
        spec_1: A valid specification for SNMP device detection

    Returns:
        A valid specification for SNMP device detection

    Example:

        >>> DETECT = all_of(exists("1.2.3.4"), contains("1.2.3.5", "foo"))

    """
    reduced = SNMPDetectSpecification(l0 + l1 for l0, l1 in itertools.product(spec_0, spec_1))
    if not specs:
        return reduced
    return all_of(reduced, *specs)


def any_of(*specs: SNMPDetectSpecification) -> SNMPDetectSpecification:
    """Detect the device if any of the passed specifications are met

    Args:
        spec: A valid specification for SNMP device detection

    Returns:
        A valid specification for SNMP device detection

    Example:

        >>> DETECT = any_of(exists("1.2.3.4"), exists("1.2.3.5"))

    """
    return SNMPDetectSpecification(sum(specs, []))


def _negate(spec: SNMPDetectSpecification) -> SNMPDetectSpecification:
    assert len(spec) == 1
    assert len(spec[0]) == 1
    return SNMPDetectSpecification([[(spec[0][0][0], spec[0][0][1], not spec[0][0][2])]])


def matches(oidstr: str, value: str) -> SNMPDetectSpecification:
    """Detect the device if the value of the OID matches the expression

    Args:
        oidstr: The OID to match the value against
        value: The regular expression that the value of the OID should match

    Returns:
        A valid specification for SNMP device detection

    Example:

        >>> DETECT = matches("1.2.3.4", ".* Server")

    """
    return SNMPDetectSpecification([[(oidstr, value, True)]])


def contains(oidstr: str, value: str) -> SNMPDetectSpecification:
    """Detect the device if the value of the OID contains the given string

    Args:
        oidstr: The OID to match the value against
        value: The substring expected to be in the OIDs value

    Returns:
        A valid specification for SNMP device detection

    Example:

        >>> DETECT = contains("1.2.3", "isco")

    """
    return SNMPDetectSpecification([[(oidstr, f".*{re.escape(value)}.*", True)]])


def startswith(oidstr: str, value: str) -> SNMPDetectSpecification:
    """Detect the device if the value of the OID starts with the given string

    Args:
        oidstr: The OID to match the value against
        value: The expected start of the OIDs value

    Returns:
        A valid specification for SNMP device detection

    Example:

        >>> DETECT = startswith("1.2.3", "Sol")

    """
    return SNMPDetectSpecification([[(oidstr, f"{re.escape(value)}.*", True)]])


def endswith(oidstr: str, value: str) -> SNMPDetectSpecification:
    """Detect the device if the value of the OID ends with the given string

    Args:
        oidstr: The OID to match the value against
        value: The expected end of the OIDs value

    Returns:
        A valid specification for SNMP device detection

    Example:

        >>> DETECT = endswith("1.2.3", "nix")

    """
    return SNMPDetectSpecification([[(oidstr, f".*{re.escape(value)}", True)]])


def equals(oidstr: str, value: str) -> SNMPDetectSpecification:
    """Detect the device if the value of the OID equals the given string

    Args:
        oidstr: The OID to match the value against
        value: The expected value of the OID

    Returns:
        A valid specification for SNMP device detection

    Example:

        >>> DETECT = equals("1.2.3", "MySwitch")

    """
    return SNMPDetectSpecification([[(oidstr, f"{re.escape(value)}", True)]])


def exists(oidstr: str) -> SNMPDetectSpecification:
    """Detect the device if the OID exists at all

    Args:
        oidstr: The OID that is required to exist

    Returns:
        A valid specification for SNMP device detection

    Example:

        >>> DETECT = exists("1.2.3")

    """
    return SNMPDetectSpecification([[(oidstr, ".*", True)]])


def not_matches(oidstr: str, value: str) -> SNMPDetectSpecification:
    """The negation of :func:`matches`"""
    return _negate(matches(oidstr, value))


def not_contains(oidstr: str, value: str) -> SNMPDetectSpecification:
    """The negation of :func:`contains`"""
    return _negate(contains(oidstr, value))


def not_startswith(oidstr: str, value: str) -> SNMPDetectSpecification:
    """The negation of :func:`startswith`"""
    return _negate(startswith(oidstr, value))


def not_endswith(oidstr: str, value: str) -> SNMPDetectSpecification:
    """The negation of :func:`endswith`"""
    return _negate(endswith(oidstr, value))


def not_equals(oidstr: str, value: str) -> SNMPDetectSpecification:
    """The negation of :func:`equals`"""
    return _negate(equals(oidstr, value))


def not_exists(oidstr: str) -> SNMPDetectSpecification:
    """The negation of :func:`exists`"""
    return _negate(exists(oidstr))
