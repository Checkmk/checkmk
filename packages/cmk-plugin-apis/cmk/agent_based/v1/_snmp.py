#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Classes used by the API for section plug-ins"""

import string
from collections.abc import Sequence
from typing import Literal, NamedTuple, override, Self


class _OIDSpecTuple(NamedTuple):
    column: int | str
    encoding: Literal["string", "binary"]
    save_to_cache: bool

    # we create a deepcopy in our unit tests, so support it.
    def __deepcopy__(self, _memo: object) -> Self:
        return self


class OIDBytes(_OIDSpecTuple):
    """Class to indicate that the OIDs value should be provided as list of integers

    Args:
        oid: The OID to fetch

    Example:

        >>> _ = OIDBytes("2.1")

    """

    def __new__(cls, value: str) -> "OIDBytes":
        return super().__new__(cls, value, "binary", False)

    @override
    def __repr__(self) -> str:
        return f"OIDBytes({self.column!r})"


class OIDCached(_OIDSpecTuple):
    """Class to indicate that the OIDs value should be cached

    Args:
        oid: The OID to fetch

    Example:

        >>> _ = OIDCached("2.1")

    """

    def __new__(cls, value: str) -> "OIDCached":
        return super().__new__(cls, value, "string", True)

    @override
    def __repr__(self) -> str:
        return f"OIDCached({self.column!r})"


class OIDEnd(_OIDSpecTuple):
    """Class to indicate the end of the OID string should be provided

    When specifying an OID in an SNMPTree object, the parse function
    will be handed the corresponding value of that OID. If you use OIDEnd()
    instead, the parse function will be given the tailing portion of the
    OID (the part that you not already know).
    """

    def __new__(cls) -> "OIDEnd":
        return super().__new__(cls, 0, "string", False)

    @override
    def __repr__(self) -> str:
        return "OIDEnd()"


class _SNMPTreeTuple(NamedTuple):
    base: str
    oids: Sequence[_OIDSpecTuple]


class SNMPTree(_SNMPTreeTuple):
    # This extends the basic tuple type by
    # * validation
    # * a more user friendly way of creation
    # * doc
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
        ...         OIDEnd(),  # I want the end oids of every entry
        ...         "7.8",  # just a regular entry
        ...         OIDCached("123"),  # this is HUGE, please cache it
        ...         OIDBytes("42"),  # I expect bytes, give me a list of integers
        ...     ],
        ... )
    """

    VALID_CHARACTERS: set[str] = {".", *string.digits}

    def __new__(cls, base: str, oids: Sequence[str | _OIDSpecTuple]) -> Self:
        if not isinstance(oids, list):
            raise TypeError(f"'oids' argument to SNMPTree must be a list, got {type(oids)}")

        return super().__new__(
            cls,
            base=base,
            oids=[
                o if isinstance(o, _OIDSpecTuple) else _OIDSpecTuple(o, "string", False)
                for o in oids
            ],
        )

    def validate(self) -> None:
        self._validate_base(self.base)
        self._validate_oids(self.oids)

    @classmethod
    def validate_oid_string(cls, value: str) -> None:
        if not isinstance(value, str):
            raise TypeError(f"expected a non-empty string: {value!r}")
        if not value:
            raise ValueError(f"expected a non-empty string: {value!r}")
        if not cls.VALID_CHARACTERS.issuperset(value):
            invalid_chars = "".join(sorted(set(value).difference(cls.VALID_CHARACTERS)))
            raise ValueError(f"invalid characters in OID descriptor: {invalid_chars!r}")
        if value.endswith("."):
            raise ValueError(f"{value} should not end with '.'")

    def _validate_base(self, base: str) -> None:
        self.validate_oid_string(base)
        if not base.startswith("."):
            raise ValueError(f"{base!r} must start with '.'")

    def _validate_oids(self, oid_list: Sequence[_OIDSpecTuple]) -> None:
        """Validate OIDs

        Note that in fact, this function can deal with, and may return integers.
        The old check_api not only allowed zero to be passed (which currently is the
        same as OIDEnd()), but also three more special values, represented by the integers
        -1 to -4. For the time being, we allow those.

        However, we deliberately do not allow them in the type annotations.
        """

        # collect beginnings of OIDs to ensure base is as long as possible:
        heads: list[str] = []

        for column, _encoding, _save_to_cache in oid_list:
            if column in (0, -1, -2, -3, -4):  # alowed for legacy checks. Remove some day (tm).
                continue
            if not isinstance(column, str):
                raise ValueError(f"invalid OID column {column!r}")

            self.validate_oid_string(column)

            if column.startswith("."):
                raise ValueError(f"{column!r} must not start with '.'")

            heads.append(column.split(".", 1)[0])

        # make sure the base is as long as possible
        if len(heads) > 1 and len(set(heads)) == 1:
            raise ValueError(f"base can be extended by '.{heads[0]}'")
