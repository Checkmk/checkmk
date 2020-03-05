#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Types and classes used by the API for agent_based plugins
"""
from typing import Any, Callable, Generator, List, NamedTuple, Optional, Tuple, Union
import collections

from cmk.base.api import PluginName
from cmk.base.check_utils import AgentSectionContent
from cmk.base.snmp_utils import SNMPTable, OIDSpec
from cmk.base.discovered_labels import HostLabel

AgentParseFunction = Callable[[AgentSectionContent], Any]

# we do *not* use SNMPSectionContent here, because List[SNMPTable]
# is more specific.
SNMPParseFunction = Callable[[List[SNMPTable]], Any]

SNMPDetectAtom = Tuple[str, str, bool]  # (oid, regex_pattern, expected_match)
SNMPDetectSpec = List[List[SNMPDetectAtom]]


class OIDEnd(int):
    """OID specification to get the end of the OID string

    When specifying an OID in an SNMPTree object, the parse function
    will be handed the corresponding value of that OID. If you use OIDEnd()
    instead, the parse function will be given the tailing portion of the
    OID (the part that you not already know).
    """
    def __new__(cls):
        return super(OIDEnd, cls).__new__(cls, 0)

    def __repr__(self):
        return "OIDEnd()"


# We inherit from int in the above, because we must be compatible
# to the old APIs OID_END, OID_STRING and so on (in particular OID_END = 0).
# Once we can drop those, we can make this a simple object,
# and adjust the type hints in SNMPTree. We use a type alias for
# the time beeing, in order to make it easier to find all occurrances.
# Once it's not needed anymore, replace all ocurrances by OIDEnd:
CompatibleOIDEnd = int


class SNMPTree:
    """Specify an OID table to fetch

    For every SNMPTree that is specified, the parse function will
    be handed a list of lists with the values of the corresponding
    OIDs.
    """
    def __init__(self, *, base, oids):
        # type: (str, List[Union[str, OIDSpec, CompatibleOIDEnd]]) -> None
        # replace int by OIDEnd once ready
        self._base = self._sanitize_base(base)
        self._oids = self._sanitize_oids(oids)

    @staticmethod
    def _sanitize_base(base):
        # type: (str) -> OIDSpec
        oid_base = OIDSpec(base)
        if not str(oid_base).startswith('.'):
            raise ValueError("%r must start with '.'" % (oid_base,))
        return oid_base

    @staticmethod
    def _sanitize_oids(oids):
        # type: (List[Union[str, OIDSpec, CompatibleOIDEnd]]) -> List[Union[OIDSpec, CompatibleOIDEnd]]
        if not isinstance(oids, list):
            raise TypeError("oids must be a list")

        # remove the "int" once CompatibleOIDEnd is not needed anymore
        typed_oids = [
            oid if isinstance(oid, (OIDSpec, OIDEnd, int)) else OIDSpec(oid) for oid in oids
        ]

        # remaining validations only regard true OIDSpec objects
        oid_specs = [o for o in typed_oids if isinstance(o, OIDSpec)]
        if len(oid_specs) < 2:
            return typed_oids

        for oid in oid_specs:
            if str(oid).startswith('.'):
                raise ValueError("column %r must not start with '.'" % (oid,))

        # make sure the base is as long as possible
        heads_counter = collections.Counter(str(oid).split('.', 1)[0] for oid in oid_specs)
        head, count = max(heads_counter.items(), key=lambda x: x[1])
        if count == len(oid_specs) and all(str(o) != head for o in oid_specs):
            raise ValueError("base can be extended by '.%s'" % head)

        return typed_oids

    @property
    def base(self):
        # type: () -> OIDSpec
        return self._base

    @property
    def oids(self):
        # type: () -> List[Union[OIDSpec, CompatibleOIDEnd]]
        return self._oids

    def __eq__(self, other):
        # type: (Any) -> bool
        if not isinstance(other, self.__class__):
            return False
        return self.__dict__ == other.__dict__

    def __repr__(self):
        # type: () -> str
        return "%s(base=%r, oids=%r)" % (self.__class__.__name__, self.base, self.oids)


HostLabelFunction = Callable[[Any], Generator[HostLabel, None, None]]

AgentSectionPlugin = NamedTuple("AgentSectionPlugin", [
    ("name", PluginName),
    ("parsed_section_name", PluginName),
    ("parse_function", AgentParseFunction),
    ("host_label_function", HostLabelFunction),
    ("supercedes", List[PluginName]),
])

SNMPSectionPlugin = NamedTuple("SNMPSectionPlugin", [
    ("name", PluginName),
    ("parsed_section_name", PluginName),
    ("parse_function", SNMPParseFunction),
    ("host_label_function", HostLabelFunction),
    ("supercedes", List[PluginName]),
    ("detect_spec", SNMPDetectSpec),
    ("trees", List[SNMPTree]),
])
