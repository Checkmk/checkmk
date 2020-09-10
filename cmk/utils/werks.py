#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Code for processing Checkmk werks. This is needed by several components,
so it's best place is in the central library."""

import itertools
import json
from pathlib import Path
import re
from typing import Any, Dict

from six import ensure_str

import cmk.utils.paths

from cmk.utils.exceptions import MKGeneralException
from cmk.utils.i18n import _


# This class is used to avoid repeated construction of dictionaries, including
# *all* translation values.
class WerkTranslator:
    def __init__(self):
        super(WerkTranslator, self).__init__()
        self._classes = {
            "feature": _("New feature"),
            "fix": _("Bug fix"),
            "security": _("Security fix"),
        }
        self._components = {
            # CRE
            "core": _("Core & setup"),
            "checks": _("Checks & agents"),
            "multisite": _("User interface"),
            "wato": _("WATO"),
            "notifications": _("Notifications"),
            "bi": _("BI"),
            "reporting": _("Reporting & availability"),
            "ec": _("Event console"),
            "livestatus": _("Livestatus"),
            "liveproxy": _("Livestatus proxy"),
            "inv": _("HW/SW inventory"),

            # CEE
            "cmc": _("The Checkmk Micro Core"),
            "setup": _("Setup, site management"),
            "config": _("Configuration generation"),
            "inline-snmp": _("Inline SNMP"),
            "agents": _("Agent bakery"),
            "metrics": _("Metrics system"),
            "alerts": _("Alert handlers"),

            # CMK-OMD
            "omd": _("Site management"),
            "rpm": _("RPM packaging"),
            "deb": _("DEB packaging"),
            "nagvis": _("NagVis"),
            "packages": _("Other components"),
            "distros": _("Linux distributions"),
        }
        self._levels = {
            1: _("Trivial change"),
            2: _("Prominent change"),
            3: _("Major change"),
        }
        self._compatibilities = {
            "compat": _("Compatible"),
            "incomp_ack": _("Incompatible"),
            "incomp_unack": _("Incompatible - TODO"),
        }

    def classes(self):
        return list(self._classes.items())

    def class_of(self, werk):
        return self._classes[werk["class"]]

    def components(self):
        return list(self._components.items())

    def component_of(self, werk):
        c = werk["component"]
        return self._components.get(c, c)

    def levels(self):
        return list(self._levels.items())

    def level_of(self, werk):
        return self._levels[werk["level"]]

    def compatibilities(self):
        return list(self._compatibilities.items())

    def compatibility_of(self, werk):
        return self._compatibilities[werk["compatible"]]


def _compiled_werks_dir():
    return Path(cmk.utils.paths.share_dir, "werks")


def load():
    werks: Dict[int, Dict[str, Any]] = {}
    # The suppressions are needed because of https://github.com/PyCQA/pylint/issues/1660
    for file_name in itertools.chain(_compiled_werks_dir().glob("werks"),
                                     _compiled_werks_dir().glob("werks-*")):
        werks.update(load_precompiled_werks_file(file_name))
    return werks


def load_precompiled_werks_file(path):
    with path.open() as fp:
        return {int(werk_id): werk for werk_id, werk in json.load(fp).items()}


def load_raw_files(werks_dir):
    if werks_dir is None:
        werks_dir = _compiled_werks_dir()
    werks = {}
    for file_name in werks_dir.glob("[0-9]*"):
        werk_id = int(file_name.name)
        try:
            werk = _load_werk(file_name)
            werk["id"] = werk_id
            werks[werk_id] = werk
        except Exception as e:
            raise MKGeneralException(_("Failed to load werk \"%s\": %s") % (werk_id, e))
    return werks


_REQUIRED_WERK_FIELDS = {
    "class",
    "component",
    "date",
    "level",
    "title",
    "version",
}

_OPTIONAL_WERK_FIELDS = {
    "compatible",
    "edition",
    "knowledge",
    # TODO: What's this? Can we simply nuke the fields below from all werks?
    "state",
    "targetversion",
}

_ALLOWED_WERK_FIELDS = _REQUIRED_WERK_FIELDS | _OPTIONAL_WERK_FIELDS


def _load_werk(path):
    werk: Dict[str, Any] = {
        "body": [],
        "compatible": "compat",
        "edition": "cre",
    }
    in_header = True
    with path.open(encoding="utf-8") as fp:
        for line in fp:
            line = line.strip()
            if in_header and not line:
                in_header = False
            elif in_header:
                key, text = line.split(":", 1)
                try:
                    value = int(text.strip())
                except ValueError:
                    value = text.strip()
                field = key.lower()
                if field not in _ALLOWED_WERK_FIELDS:
                    raise MKGeneralException("unknown werk field %s" % key)
                werk[field] = value
            else:
                werk["body"].append(line)

    missing_fields = _REQUIRED_WERK_FIELDS - set(werk.keys())
    if missing_fields:
        raise MKGeneralException("missing fields: %s" % ",".join(missing_fields))
    # TODO: Check if all fields have an allowed value, see .werks/config.
    return werk


def write_precompiled_werks(path, werks):
    with path.open("w", encoding="utf-8") as fp:
        fp.write(ensure_str(json.dumps(werks, check_circular=False)))


def write_as_text(werks, f, write_version=True):
    """Write the given werks to a file object

    This is used for creating a textual hange log for the released versions and the announcement mails.
    """
    translator = WerkTranslator()
    werklist = sort_by_version_and_component(werks.values())
    for version, version_group in itertools.groupby(werklist, key=lambda w: w["version"]):
        # write_version=False is used by the announcement mails
        if write_version:
            f.write("%s:\n" % ensure_str(version))
        for component, component_group in itertools.groupby(version_group,
                                                            key=translator.component_of):
            f.write("    %s:\n" % ensure_str(component))
            for werk in component_group:
                write_werk_as_text(f, werk)
            f.write("\n")
        f.write("\n")


def write_werk_as_text(f, werk):
    prefix = ""
    if werk["class"] == "fix":
        prefix = " FIX:"
    elif werk["class"] == "security":
        prefix = " SEC:"

    if werk.get("description") and len(werk["description"]) > 3:
        omit = "..."
    else:
        omit = ""

    f.write("    * %04d%s %s%s\n" % (werk["id"], prefix, ensure_str(werk["title"]), omit))

    if werk["compatible"] == "incomp":
        f.write("            NOTE: Please refer to the migration notes!\n")


_CLASS_SORTING_VALUE = {
    "feature": 1,
    "security": 2,
    "fix": 3,
}

_COMPATIBLE_SORTING_VALUE = {
    "incomp_unack": 1,
    "incomp_ack": 2,
    "compat": 3,
}


# sort by version and within one version by component
def sort_by_version_and_component(werks):
    translator = WerkTranslator()
    return sorted(werks,
                  key=lambda w: (-parse_check_mk_version(w["version"]), translator.component_of(w),
                                 _CLASS_SORTING_VALUE.get(w["class"], 99), -w["level"],
                                 _COMPATIBLE_SORTING_VALUE.get(w["compatible"], 99), w["title"]))


def sort_by_date(werks):
    return sorted(werks, key=lambda w: w["date"], reverse=True)


VERSION_PATTERN = re.compile(r'^([.\-a-z]+)?(\d+)')


# Parses versions of Checkmk and converts them into comparable integers.
def parse_check_mk_version(v: str) -> int:
    """Figure out how to compare versions semantically.

    Parses versions of Checkmk and converts them into comparable integers.

    >>> p = parse_check_mk_version

    All dailies are built equal.

    >>> p("1.5.0-2019.10.10")
    1050090000

    >>> p("1.6.0-2019.10.10")
    1060090000

    >>> p("1.5.0-2019.10.24") == p("1.5.0-2018.05.05")
    True

    >>> p('1.2.4p1')
    1020450001

    >>> p('1.2.4')
    1020450000

    >>> p('1.2.4b1')
    1020420100

    >>> p('1.2.3i1p1')
    1020310101

    >>> p('1.2.3i1')
    1020310100

    >>> p('1.2.4p10')
    1020450010

    >>> p("1.5.0") > p("1.5.0p22")
    False

    >>> p("1.5.0-2019.10.10") > p("1.5.0p22")
    True

    >>> p("1.5.0p13") == p("1.5.0p13")
    True

    >>> p("1.5.0p13") > p("1.5.0p12")
    True

    """
    parts = v.split('.', 2)

    while len(parts) < 3:
        parts.append("0")

    var_map = {
        # identifier: (base-val, multiplier)
        's': (0, 1),  # sub
        'i': (10000, 100),  # innovation
        'b': (20000, 100),  # beta
        'p': (50000, 1),  # patch-level
        '-': (90000, 0),  # daily
        '.': (90000, 0),  # daily
    }

    def _extract_rest(_rest):
        for match in VERSION_PATTERN.finditer(_rest):
            _var_type = match.group(1) or 's'
            _num = match.group(2)
            return _var_type, int(_num), _rest[match.end():]
        # Default fallback.
        return 'p', 0, ''

    major, minor, rest = parts
    _, sub, rest = _extract_rest(rest)

    if rest.startswith("-sandbox"):
        return int('%02d%02d%02d%05d' % (int(major), int(minor), sub, 0))

    # Only add the base once, else we could do it in the loop.
    var_type, num, rest = _extract_rest(rest)
    base, multiply = var_map[var_type]
    val = base
    val += num * multiply

    while rest:
        var_type, num, rest = _extract_rest(rest)
        _, multiply = var_map[var_type]
        val += num * multiply

    return int('%02d%02d%02d%05d' % (int(major), int(minor), sub, val))
