#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Classes used by the API for section plugins
"""
from cmk.utils.type_defs import SNMPDetectBaseType
from cmk.base.api.agent_based.type_defs import OIDSpecTuple


class SNMPDetectSpecification(SNMPDetectBaseType):
    """A specification for SNMP device detection

    Note that the structure of this object is not part of the API,
    and may change at any time.
    """
    # This class is only part of the check *API*, in the sense that it hides
    # the SNMPDetectBaseType from the user (and from the auto generated doc!).
    # Use it for type annotations API frontend objects


class OIDBytes(OIDSpecTuple):
    """Class to indicate that the OIDs value should be provided as list of integers

    Args:
        oid: The OID to fetch

    Example:

        >>> _ = OIDBytes("2.1")

    """
    def __new__(cls, value: str) -> 'OIDBytes':
        return super().__new__(cls, value, "binary", False)

    def __repr__(self) -> str:
        return f"OIDBytes({self.column!r})"


class OIDCached(OIDSpecTuple):
    """Class to indicate that the OIDs value should be cached

    Args:
        oid: The OID to fetch

    Example:

        >>> _ = OIDCached("2.1")

    """
    def __new__(cls, value: str) -> 'OIDCached':
        return super().__new__(cls, value, "string", True)

    def __repr__(self) -> str:
        return f"OIDCached({self.column!r})"


class OIDEnd(OIDSpecTuple):
    """Class to indicate the end of the OID string should be provided

    When specifying an OID in an SNMPTree object, the parse function
    will be handed the corresponding value of that OID. If you use OIDEnd()
    instead, the parse function will be given the tailing portion of the
    OID (the part that you not already know).
    """
    def __new__(cls) -> 'OIDEnd':
        return super().__new__(cls, 0, "string", False)

    def __repr__(self) -> str:
        return "OIDEnd()"
