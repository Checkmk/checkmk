#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Type definitions

Some of these are exposed in the API, some are not.
"""
from collections.abc import Mapping
from typing import (
    Any,
    Callable,
    Generator,
    List,
    MutableMapping,
    NamedTuple,
    Optional,
    Sequence,
    Set,
    Union,
)
import pprint

from cmk.utils.type_defs import (
    ParsedSectionName,
    SectionName,
    SNMPDetectBaseType,
)
from cmk.snmplib.type_defs import OIDSpec  # pylint: disable=cmk-module-layer-violation


class PluginSuppliedLabel(NamedTuple("_LabelTuple", [("name", str), ("value", str)])):
    """A user friendly variant of our internally used labels

    This is a tiny bit redundant, but it helps decoupling API
    code from internal representations.
    """
    def __init__(self, name, value):
        super().__init__()
        if not isinstance(name, str):
            raise TypeError(f"Invalid label name given: Expected string (got {name!r})")
        if not isinstance(value, str):
            raise TypeError(f"Invalid label value given: Expected string (got {value!r})")

    def __repr__(self):
        return "%s(%r, %r)" % (self.__class__.__name__, self.name, self.value)


class HostLabel(PluginSuppliedLabel):
    """Representing a host label in Checkmk

    This class creates a host label that can be yielded by a host_label_function as regisitered
    with the section.

        >>> my_label = HostLabel("my_key", "my_value")

    """


# We must make sure that `SpecialColumn(OIDEnd()) == SpecialColumn.END`
class OIDEnd(int):
    """OID specification to get the end of the OID string

    When specifying an OID in an SNMPTree object, the parse function
    will be handed the corresponding value of that OID. If you use OIDEnd()
    instead, the parse function will be given the tailing portion of the
    OID (the part that you not already know).
    """

    # NOTE: The default constructor already does the right thing for our "glorified 0".
    def __repr__(self):
        return "OIDEnd()"


class Parameters(Mapping):
    """Parameter objects are used to pass parameters to plugin functions"""
    def __init__(self, data):
        if not isinstance(data, dict):
            self._data = data  # error handling will try to repr(self).
            raise TypeError("Parameters expected dict, got %r" % (data,))
        self._data = dict(data)

    def __getitem__(self, key):
        return self._data[key]

    def __len__(self):
        return len(self._data)

    def __iter__(self):
        return iter(self._data)

    def __repr__(self):
        # use pformat to be testable.
        return "%s(%s)" % (self.__class__.__name__, pprint.pformat(self._data))


class SNMPTree(NamedTuple):
    """Specify an OID table to fetch

    For every SNMPTree that is specified, the parse function will
    be handed a list of lists with the values of the corresponding
    OIDs.

    Args:
        base: The OID base string, starting with a dot.
        oids: A list of OID specifications.

    Example:

        >>> _ = SNMPTree(
        ...     base=".1.2.3.4.5.6",
        ...     oids=[
        ...         OIDEnd(),  # get the end oids of every entry
        ...         "7.8",  # just a regular entry
        ...     ],
        ... )
    """
    base: str
    oids: Sequence[Union[str, OIDSpec, OIDEnd]]

    def validate(self) -> None:
        self._validate_base(self.base)
        self._validate_oids(self.oids)

    @staticmethod
    def _validate_common_oid_properties(raw: str) -> None:
        _ = OIDSpec(raw)  # TODO: move validation here

    def _validate_base(self, base: str) -> None:
        self._validate_common_oid_properties(base)
        if not base.startswith('.'):
            raise ValueError(f"{base!r} must start with '.'")

    def _validate_oids(self, oid_list: Sequence[Union[str, OIDSpec, OIDEnd]]) -> None:
        """Validate OIDs

        Note that in fact, this function can deal with, and may return integers.
        The old check_api not only allowed zero to be passed (which currently is the
        same as OIDEnd()), but also three more special values, represented by the integers
        -1 to -4. For the time being, we allow those.

        However, we deliberately do not allow them in the type annotations.
        """

        if not isinstance(oid_list, list):
            raise TypeError(f"'oids' argument to SNMPTree must be a list, got {type(oid_list)}")

        # collect beginnings of OIDs to ensure base is as long as possible:
        heads: List[str] = []

        for oid in oid_list:
            if isinstance(oid, OIDEnd):
                continue
            if oid in (0, -1, -2, -3, -4):  # alowed for legacy checks. Remove some day (tm).
                continue

            # creating the object currently does most of the validation
            if not isinstance(oid, OIDSpec):
                self._validate_common_oid_properties(oid)

            raw_oid = str(oid)
            if raw_oid.startswith('.'):
                raise ValueError(f"column {oid!r} must not start with '.'")

            heads.append(raw_oid.split('.', 1)[0])

        # make sure the base is as long as possible
        if len(heads) > 1 and len(set(heads)) == 1:
            raise ValueError("base can be extended by '.%s'" % heads[0])


StringTable = List[List[str]]
StringByteTable = List[List[Union[str, List[int]]]]

AgentParseFunction = Callable[[StringTable], Any]

HostLabelGenerator = Generator[HostLabel, None, None]
HostLabelFunction = Callable[..., HostLabelGenerator]

SNMPParseFunction = Union[  #
    Callable[[List[StringTable]], Any],  #
    Callable[[List[StringByteTable]], Any],  #
]

SimpleSNMPParseFunction = Union[  #
    Callable[[StringTable], Any],  #
    Callable[[StringByteTable], Any],  #
]

AgentSectionPlugin = NamedTuple(
    "AgentSectionPlugin",
    [
        ("name", SectionName),
        ("parsed_section_name", ParsedSectionName),
        ("parse_function", AgentParseFunction),
        ("host_label_function", HostLabelFunction),
        ("supersedes", Set[SectionName]),
        ("module", Optional[str]),  # not available for auto migrated plugins.
    ],
)

SNMPSectionPlugin = NamedTuple(
    "SNMPSectionPlugin",
    [
        ("name", SectionName),
        ("parsed_section_name", ParsedSectionName),
        ("parse_function", SNMPParseFunction),
        ("host_label_function", HostLabelFunction),
        ("supersedes", Set[SectionName]),
        ("detect_spec", SNMPDetectBaseType),
        ("trees", List[SNMPTree]),
        ("module", Optional[str]),  # not available for auto migrated plugins.
    ],
)

SectionPlugin = Union[AgentSectionPlugin, SNMPSectionPlugin]

ValueStore = MutableMapping[str, Any]
