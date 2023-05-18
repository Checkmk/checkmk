#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


# mypy: disable-error-code="var-annotated"

from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.config import check_info

_CHECKED_COUNTERS = [  # counter, setting, name, perfvar
    (
        "i/o database reads (attached) average latency",
        "read_attached_latency",
        "db read (attached) latency",
        "db_read_latency",
    ),
    (
        "i/o database reads (recovery) average latency",
        "read_recovery_latency",
        "db read (recovery) latency",
        "db_read_recovery_latency",
    ),
    (
        "i/o database writes (attached) average latency",
        "write_latency",
        "db write (attached) latency",
        "db_write_latency",
    ),
    ("i/o log writes average latency", "log_latency", "Log latency", "db_log_latency"),
]

_de_DE = {
    "e/a: durchschnittliche wartezeit f\x81r datenbankleseoperationen (angef\x81gt)": "i/o database reads (attached) average latency",
    "e/a: durchschnittliche wartezeit f\x81r datenbankleseoperationen (wiederherstellung)": "i/o database reads (recovery) average latency",
    "e/a: durchschnittliche wartezeit f\x81r datenbankschreiboperationen (angef\x81gt)": "i/o database writes (attached) average latency",
    "e/a: durchschnittliche wartezeit f\x81r protokollschreiboperationen": "i/o log writes average latency",
}


def _delocalize_de_DE(instance, counter, value):
    # replace localized thousands-/ decimal-separators
    value = value.replace(".", "").replace(",", ".")
    counter = _de_DE.get(counter, counter)
    return instance, counter, value


def parse_msexch_database(info):
    if not (info and info[0]):
        return {}

    delocalize_func = None
    offset = 0
    if len(info[0]) > 1 and info[0][0] == "locale":
        locale = info[0][1].strip()
        offset = 1
        delocalize_func = {
            "de-DE": _delocalize_de_DE,
        }.get(locale)

    parsed = {}
    for row in info[offset:]:
        row = [r.strip('"') for r in row]
        if len(row) != 2 or not row[0].startswith("\\\\"):
            continue

        __, obj, counter = row[0].rsplit("\\", 2)
        instance = obj.split("(", 1)[-1].split(")", 1)[0]
        value = row[1]

        if delocalize_func is not None:
            instance, counter, value = delocalize_func(instance, counter, value)

        # The entries for log verifier contain an ID as the last part
        # which changes upon reboot of the exchange server. Therefore,
        # we just remove them here as a workaround.
        if "/log verifier" in instance:
            instance = instance.rsplit(" ", 1)[0]

        try:
            parsed.setdefault(instance, {})[counter] = float(value)
        except ValueError:
            continue
    return parsed


def inventory_msexch_database(parsed):
    for instance, data in parsed.items():
        if any(entry[0] in data for entry in _CHECKED_COUNTERS):
            yield instance, None


def check_msexch_database(item, params, parsed):
    data = parsed.get(item)
    if data is None:
        return

    for counter, setting, name, perfvar in _CHECKED_COUNTERS:
        value = data.get(counter)
        if value is None:
            continue
        status = 0
        warn, crit = params.get(setting, (None, None))
        if crit is not None and value >= crit:
            status = 2
        elif warn is not None and value >= warn:
            status = 1
        yield status, "%.1fms %s" % (value, name), [(perfvar, value, warn, crit, None, None)]


check_info["msexch_database"] = LegacyCheckDefinition(
    discovery_function=inventory_msexch_database,
    check_function=check_msexch_database,
    parse_function=parse_msexch_database,
    service_name="Exchange Database %s",
    check_ruleset_name="msx_database",
    check_default_parameters={
        "read_attached_latency": (200.0, 250.0),
        "read_recovery_latency": (150.0, 200.0),
        "write_latency": (40.0, 50.0),
        "log_latency": (5.0, 10.0),
    },
)
