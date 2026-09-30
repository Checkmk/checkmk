#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable
from dataclasses import dataclass
from typing import override

__all__ = [
    "ParseFailure",
    "parse_as",
]


@dataclass(frozen=True)
class ParseFailure:
    """A placeholder for a value that the parse function could not parse

    Sometimes a device sends data that a plug-in does not expect, for example a
    state that a newer firmware has introduced. Rather than failing for the whole
    section, the parse function can put a ``ParseFailure`` into the parsed section
    instead of that value. Create it with :func:`parse_as`, or from an exception
    you caught, so that the crash report contains the error's traceback.

    Use it only for data the plug-in should be able to parse, so that the crash
    report helps to fix the plug-in. Data that a device leaves out or marks as
    unavailable on purpose is not a parse failure: handle it in the check function.

    What your plug-in has to do:

    * Keep the item, and everything else discovery needs, outside the failure.
      Discovery, host label and inventory functions get the failure like any other
      value of the section, and they cannot report it.
    * Yield the failure from every check function that uses the value. A failure
      that no check function yields is not reported at all, and the type checker
      does not make sure that it is yielded.
    * Go on yielding the results that do not depend on the value, if there are any.
    * A cluster check function of your own gets the failures of all nodes and has
      to yield them itself. ``clusterize.make_node_notice_results`` drops the
      results of a node whose check function yielded a failure.

    What Checkmk does with a failure that a check function yields:

    * The service shows the UNKNOWN result
      ``Could not parse '<field>': <error message>`` next to the other results.
    * Checkmk creates a crash report on every check, and the service details show
      its ID.
    * The other services of the section are not affected.
    * In a cluster, the failure counts as an UNKNOWN result of the node that sent
      the data, and the cluster mode weighs it like any other result of that node.
      The crash report is created in any case.

    Args:
        field: What could not be parsed, as the user should see it, for example the
            name of the SNMP column. Choose a name that tells it apart from the
            other values of the section.
        exception: The exception that parsing raised.

    Example::

        def parse_fans(string_table: StringTable) -> Mapping[str, FanState | ParseFailure]:
            return {
                fan_id: parse_as(FanState, state, field="fan state")
                for fan_id, state in string_table
            }


        def discover_fans(section: Mapping[str, FanState | ParseFailure]) -> DiscoveryResult:
            for fan_id in section:
                yield Service(item=fan_id)


        def check_fan(item: str, section: Mapping[str, FanState | ParseFailure]) -> CheckResult:
            if (state := section.get(item)) is None:
                return
            if isinstance(state, ParseFailure):
                yield state
                return
            yield Result(state=State.OK, summary=f"Fan state: {state.name}")

    If a fan reports the unknown state ``"9"``, its service shows the UNKNOWN result
    ``Could not parse 'fan state': '9' is not a valid FanState``.
    """

    field: str
    exception: Exception

    @override
    def __str__(self) -> str:
        return f"Could not parse {self.field!r}: {self.exception}"


def parse_as[V, T](target: Callable[[V], T], value: V, *, field: str) -> T | ParseFailure:
    """Parse ``value`` with ``target``, or return a :class:`ParseFailure` if that fails

    ``target`` is anything that parses the value, for example ``int``, an enum, or a
    function that parses a whole line of the string table. It fails by raising a
    ``ValueError``, a ``TypeError`` or a ``LookupError`` (like ``KeyError`` and
    ``IndexError``). Any other error is not caught: the parse function then fails
    as it would without ``parse_as``.

    Example:

        >>> parse_as(int, "42", field="fan speed")
        42
        >>> print(parse_as(int, "n/a", field="fan speed"))
        Could not parse 'fan speed': invalid literal for int() with base 10: 'n/a'
    """
    try:
        return target(value)
    except (TypeError, ValueError, LookupError) as exc:
        return ParseFailure(field, exc)
