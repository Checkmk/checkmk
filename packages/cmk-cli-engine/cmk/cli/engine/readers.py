#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
from collections import Counter
from collections.abc import Mapping, Sequence

from .options import GetoptOptions, Option, OptionName


def parse_sub_options(
    sub_options: Sequence[Option], all_opts: GetoptOptions, logger: logging.Logger
) -> Mapping[OptionName, object]:
    options: dict[OptionName, object] = {}
    counts: Counter[OptionName] = Counter()
    collected: dict[OptionName, list[str]] = {}

    for o, a in all_opts:
        for option in sub_options:
            if o not in option.options():
                continue

            if option.is_deprecated_option(o):
                logger.warning(
                    "%(deprecated)r is deprecated in favour of option %(name)r",
                    {"deprecated": o, "name": option.name},
                )

            if a and not option.argument:
                raise ValueError("No argument to %s expected." % o)

            if option.repeat:
                if option.argument:
                    collected.setdefault(option.name, []).append(a)
                else:
                    counts[option.name] += 1
                continue

            val: object = a
            if not option.argument:
                val = True
            elif option.argument_conv:
                try:
                    val = option.argument_conv(a)
                except ValueError:
                    raise ValueError("%s: Invalid argument" % o)

            options[option.name] = val

    return {
        **options,
        **counts,
        **{name: tuple(values) for name, values in collected.items()},
    }


def option_string(parsed: Mapping[OptionName, object], name: OptionName) -> str | None:
    match parsed.get(name):
        case None:
            return None
        case str() as value:
            return value
        case value:
            raise TypeError(f"--{name}: invalid argument {value!r}")


def option_strings(parsed: Mapping[OptionName, object], name: OptionName) -> Sequence[str]:
    match parsed.get(name):
        case None:
            return ()
        case tuple() as value:
            strings = tuple(element for element in value if isinstance(element, str))
            if len(strings) == len(value):
                return strings
            raise TypeError(f"--{name}: invalid argument {value!r}")
        case value:
            raise TypeError(f"--{name}: invalid argument {value!r}")


def option_count(parsed: Mapping[OptionName, object], name: OptionName) -> int:
    match parsed.get(name):
        case int() as value:
            return value
        case value:
            raise TypeError(f"--{name}: invalid argument {value!r}")


def option_names[NameT](
    parsed: Mapping[OptionName, object], name: OptionName, type_: type[NameT]
) -> frozenset[NameT]:
    match parsed.get(name):
        case set() | frozenset() as value:
            names = frozenset(element for element in value if isinstance(element, type_))
            if len(names) == len(value):
                return names
            raise TypeError(f"--{name}: invalid argument {value!r}")
        case value:
            raise TypeError(f"--{name}: invalid argument {value!r}")
