#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from abc import ABC, abstractmethod
from collections.abc import Mapping
from enum import Enum
from functools import cache
from typing import Any, Literal, NotRequired, override, TypedDict, TypeVar

import pyparsing as pp

from cmk.fields import String

_T = TypeVar("_T", int, float, bool, str, dict[str, Any], list, tuple, None)


class FieldsFilter(ABC):
    def __contains__(self, field_path: str) -> bool:
        return self.is_included(field_path)

    @abstractmethod
    def is_included(self, field_path: str | None = None) -> bool: ...

    @abstractmethod
    def get_nested_fields(self, field_path: str) -> "FieldsFilter": ...

    @abstractmethod
    def apply(self, data: _T) -> _T: ...


class _Included(FieldsFilter):
    @override
    def is_included(self, field_path: str | None = None) -> bool:
        return True

    @override
    def get_nested_fields(self, field_path: str) -> "FieldsFilter":
        return self

    @override
    def apply(self, data: _T) -> _T:
        return data

    @override
    def __repr__(self) -> str:
        return "Included"

    @override
    def __eq__(self, other: object) -> bool:
        return isinstance(other, _Included)


class _Excluded(FieldsFilter):
    @override
    def is_included(self, field_path: str | None = None) -> bool:
        return False

    @override
    def get_nested_fields(self, field_path: str) -> "FieldsFilter":
        return self

    @override
    def apply(self, data: _T) -> _T:
        # NOTE: It's unlikely that this will be called.
        # 1. _Excluded shouldn't exist at the root level. (or at least it wouldn't make sense)
        # 2. _ExcludeFields doesn't call apply for _Excluded instances.
        if isinstance(data, list):
            return [self.apply(item) for item in data]
        if isinstance(data, tuple):
            return tuple(self.apply(item) for item in data)
        if isinstance(data, dict):
            return {}
        return data

    @override
    def __repr__(self) -> str:
        return "Excluded"

    @override
    def __eq__(self, other: object) -> bool:
        return isinstance(other, _Excluded)


class _SpecificFieldsFilter(FieldsFilter, ABC):
    @override
    def __init__(self, fields: dict[str, FieldsFilter]) -> None:
        self.fields = fields

    @override
    def __eq__(self, other: object) -> bool:
        return isinstance(other, self.__class__) and self.fields == other.fields

    @override
    def is_included(self, field_path: str | None = None) -> bool:
        if field_path is None:
            # this is either _IncludeFields or _ExcludeFields which are both partially included
            return True
        nested = self.get_nested_fields(field_path)
        # _Included and _IncludeFields are obviously included, _ExcludeFields is partially included
        return not isinstance(nested, _Excluded)

    @override
    def apply(self, data: _T) -> _T:
        if isinstance(data, list):
            return [self.apply(item) for item in data]
        if isinstance(data, tuple):
            return tuple(self.apply(item) for item in data)
        if isinstance(data, dict):
            return {
                key: nested.apply(value)
                for key, value in data.items()
                if (nested := self.get_nested_fields(key)).is_included()
            }
        return data


class _IncludeFields(_SpecificFieldsFilter):
    def __init__(self, fields: dict[str, FieldsFilter]) -> None:
        if len(fields) == 0:
            raise ValueError("Must specify at least one field to include.")
        if any(isinstance(value, _Excluded | _ExcludeFields) for value in fields.values()):
            raise ValueError("Cannot mix include and exclude filters.")

        super().__init__(fields)

    @override
    def get_nested_fields(self, field_path: str) -> "FieldsFilter":
        key, _, remainder = field_path.partition(".")
        if key not in self.fields:
            return _Excluded()

        nested = self.fields[key]
        return nested.get_nested_fields(remainder) if remainder else nested

    @override
    def __repr__(self) -> str:
        fields = ", ".join(f"{key}={self.fields[key]!r}" for key in sorted(self.fields.keys()))
        return f"Include[{fields}]"


class _ExcludeFields(_SpecificFieldsFilter):
    def __init__(self, fields: dict[str, FieldsFilter]) -> None:
        if len(fields) == 0:
            raise ValueError("Must specify at least one field to exclude.")
        if any(isinstance(value, _Included | _IncludeFields) for value in fields.values()):
            raise ValueError("Cannot mix include and exclude filters.")

        super().__init__(fields)

    @override
    def get_nested_fields(self, field_path: str) -> "FieldsFilter":
        key, _, remainder = field_path.partition(".")
        if key not in self.fields:
            return _Included()

        nested = self.fields[key]
        return nested.get_nested_fields(remainder) if remainder else nested

    @override
    def __repr__(self) -> str:
        fields = ", ".join(f"{key}={self.fields[key]!r}" for key in sorted(self.fields.keys()))
        return f"Exclude[{fields}]"


class _Mode(Enum):
    INCLUDE = "INCLUDE"
    EXCLUDE = "EXCLUDE"


class _Field(TypedDict):
    path: list[str]
    fields: NotRequired["_Fields"]


type _Fields = list[_Field]


class _ParseResult(TypedDict):
    mode: _Mode
    fields: _Fields


@cache
def _grammar() -> pp.ParserElement:
    # Parse fields with the following grammar:
    # <fields> ::= [ "!" ] <fields_struct>
    # <fields_struct> ::= "(" <field_items> ")"
    # <field_items> ::= <field> [ "," <field_items> ]
    # <field> ::= <field_path> | <fields_substruct>
    # <field_substruct> ::= <field_path> <field_struct>
    # <field_path> ::= <field_name> [ "~" <field_path> ]
    # <field_name> ::= <valid_name_char> [ <field_name> ]
    # <valid_name_char> ::= "-" | "_" | "A" | ... | "Z" | "a" | ... | "z" | "0" | ... | "9"
    field = pp.Forward()
    field_items = pp.Group(pp.DelimitedList(pp.Group(field))).set_results_name("fields")
    field_struct = pp.Suppress("(") + field_items + pp.Suppress(")")

    field_name = pp.Word(pp.alphanums + "-_")
    field_path = pp.Group(pp.DelimitedList(field_name, delim="~")).set_results_name("path")

    field_substruct = field_path + field_struct

    field <<= field_substruct | field_path
    mode = (
        pp.Optional(pp.Literal("!"))
        .setParseAction(lambda tokens: _Mode.EXCLUDE if tokens else _Mode.INCLUDE)
        .set_results_name("mode")
    )
    fields = mode + field_struct
    return fields


def _merge_fields(a: FieldsFilter, b: FieldsFilter) -> FieldsFilter:
    """Combine a and b into a single filter."""
    # NOTE: this function generally only deals with either ALL include or ALL exclude instances
    #       and is not designed to handle mixed cases

    # check if a or b in/exclude completely
    if not isinstance(a, _SpecificFieldsFilter):
        return b  # nothing to do, `b` will be the same or more specific
    if not isinstance(b, _SpecificFieldsFilter):
        return a  # nothing to do, `a` will be the same or more specific

    # both are specific fields filters, merge fields
    fields = a.fields.copy()
    for key, value in b.fields.items():
        if key in fields:
            fields[key] = _merge_fields(fields[key], value)
        else:
            fields[key] = value

    return a.__class__(fields)


def _build_field_filter(
    remaining_path: list[str],
    fields: _Fields | None,
    specific_fields_class: type[_SpecificFieldsFilter],
    complete_filter_class: type[_Included | _Excluded],
) -> FieldsFilter:
    if remaining_path:
        return specific_fields_class(
            {
                remaining_path[0]: _build_field_filter(
                    remaining_path[1:],
                    fields,
                    specific_fields_class,
                    complete_filter_class,
                )
            }
        )

    if fields:
        return specific_fields_class(
            _build_fields(fields, specific_fields_class, complete_filter_class)
        )

    return complete_filter_class()


def _build_fields(
    fields: _Fields,
    specific_fields_class: type[_SpecificFieldsFilter],
    complete_filter_class: type[_Included | _Excluded],
) -> dict[str, FieldsFilter]:
    result: dict[str, FieldsFilter] = {}
    for field in fields:
        key = field["path"][0]
        field_filter = _build_field_filter(
            remaining_path=field["path"][1:],
            fields=field.get("fields"),
            specific_fields_class=specific_fields_class,
            complete_filter_class=complete_filter_class,
        )
        if key in result:
            result[key] = _merge_fields(result[key], field_filter)
        else:
            result[key] = field_filter

    return result


def parse_fields_filter(fields_filter: str) -> FieldsFilter:
    """Parse a filter string into a FieldsFilter instance."""
    if not fields_filter:
        return make_filter(this_is="included")

    try:
        parsed_raw = _grammar().parse_string(fields_filter, parse_all=True).as_dict()
    except pp.ParseException as e:
        raise ValueError(f"Invalid format: {e}") from e

    parsed: _ParseResult = {
        "mode": parsed_raw["mode"],
        "fields": parsed_raw["fields"],
    }

    if parsed["mode"] == _Mode.EXCLUDE:
        specific_fields_class: type[_SpecificFieldsFilter] = _ExcludeFields
        all_fields_class: type[_Included | _Excluded] = _Excluded
    else:
        specific_fields_class = _IncludeFields
        all_fields_class = _Included

    return specific_fields_class(
        _build_fields(parsed["fields"], specific_fields_class, all_fields_class)
    )


def make_filter(
    *,
    include: dict[str, FieldsFilter] | None = None,
    exclude: dict[str, FieldsFilter] | None = None,
    this_is: Literal["excluded", "included"] | None = None,
) -> FieldsFilter:
    """Create filters programmatically. Only one of the arguments can be set.
    Include and exclude filters cannot be mixed.

    Examples:
        >>> # Include all fields
        >>> make_filter(this_is="included")
        Included
        >>> # Include only "field", all other keys are excluded
        >>> make_filter(include={"field": make_filter(this_is="included")})
        Include[field=Included]
        >>> # Exclude only "field", all other keys are included
        >>> make_filter(exclude={"field": make_filter(this_is="excluded")})
        Exclude[field=Excluded]
        >>> # Include "subfield" within "field", all other keys (on both levels) are excluded
        >>> make_filter(include={"field": make_filter(include={"subfield": make_filter(this_is="included")})})
        Include[field=Include[subfield=Included]]
        >>> # Exclude "subfield" within "field", all other keys (on both levels) are included
        >>> make_filter(exclude={"field": make_filter(exclude={"subfield": make_filter(this_is="excluded")})})
        Exclude[field=Exclude[subfield=Excluded]]
    """
    if include is None and exclude is None and this_is is None:
        raise ValueError("At least one of include, exclude or this_is must be set.")
    if include is not None and exclude is not None:
        raise ValueError("Cannot combine include and exclude filters.")
    if this_is and (include is not None or exclude is not None):
        raise ValueError("Cannot combine this_is with include or exclude filters.")

    if include is not None:
        return _IncludeFields(include)

    if exclude is not None:
        return _ExcludeFields(exclude)

    return _Excluded() if this_is == "excluded" else _Included()


class FieldsFilterField(String):
    default_error_messages = {
        "invalid_format": "The fields format is invalid.",
    }

    def __init__(
        self,
        *,
        description: str = """The fields to include/exclude.

The syntax is a comma-separated list of field paths.
Each field path is a sequence of field names separated by a tilde (`~`).
Field names may contain alphanumeric characters, dashes (`-`) and underscores (`_`).
The field path may be followed by a list of subfields enclosed in parentheses (`(` and `)`).

The outermost fields must be enclosed in parentheses and may be prefixed with an exclamation mark (`!`) to negate the selection.

Examples:
- `(ipaddress)` selects the field `ipaddress`, all other fields will be omitted.
- `!(ipaddress)` excludes the field `ipaddress`, all other fields will be included.
- `(ipaddress,ipv6address)` selects only the fields `ipaddress` and `ipv6address`.
- `(attributes~ipaddress)` selects the field `ipaddress` within `attributes`, all other fields (not just within attributes) will be omitted.
- `(attributes(ipaddress,ipv6address))` selects the fields `ipaddress` and `ipv6address` within `attributes`, again all other fields will be omitted.
- `!(extensions~attributes(ipaddress,ipv6address))` excludes the fields `ipaddress` and `ipv6address` within `attributes` under `extensions`, all other fields will be included.
""",
        example: str = "!(links)",
        **kwargs: Any,
    ) -> None:
        super().__init__(description=description, example=example, **kwargs)

    @override
    def _deserialize(
        self, value: Any, attr: str | None, data: Mapping[str, Any] | None, **kwargs: Any
    ) -> FieldsFilter:
        value = super()._deserialize(value, attr, data)
        try:
            return parse_fields_filter(value)
        except ValueError:
            raise self.make_error("invalid_format")

    @override
    def _serialize(
        self, value: Any, attr: str | None, obj: dict[str, Any] | None, **kwargs: Any
    ) -> str:
        raise NotImplementedError("This field is not meant to be serialized.")
