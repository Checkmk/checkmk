#!/usr/bin/python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2016             mk@mathias-kettner.de |
# +------------------------------------------------------------------+
#
# This file is part of Check_MK.
# The official homepage is at http://mathias-kettner.de/check_mk.
#
# check_mk is free software;  you can redistribute it and/or modify it
# under the  terms of the  GNU General Public License  as published by
# the Free Software Foundation in version 2.  check_mk is  distributed
# in the hope that it will be useful, but WITHOUT ANY WARRANTY;  with-
# out even the implied warranty of  MERCHANTABILITY  or  FITNESS FOR A
# PARTICULAR PURPOSE. See the  GNU General Public License for more de-
# tails. You should have  received  a copy of the  GNU  General Public
# License along with GNU Make; see the file  COPYING.  If  not,  write
# to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
# Boston, MA 02110-1301 USA.
"""Code for processing Check_MK werks. This is needed by several components,
so it's best place is in the central library."""

import itertools
import json

try:
    from pathlib import Path  # type: ignore
except ImportError:
    from pathlib2 import Path

import cmk.utils.paths

from cmk.utils.exceptions import MKGeneralException
from cmk.utils.i18n import _


# This class is used to avoid repeated construction of dictionaries, including
# *all* translation values.
class WerkTranslator(object):
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
            "cmc": _("The Check_MK Micro Core"),
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
        return self._classes.iteritems()

    def class_of(self, werk):
        return self._classes[werk["class"]]

    def components(self):
        return self._components.iteritems()

    def component_of(self, werk):
        c = werk["component"]
        return self._components.get(c, c)

    def levels(self):
        return self._levels.iteritems()

    def level_of(self, werk):
        return self._levels[werk["level"]]

    def compatibilities(self):
        return self._compatibilities.iteritems()

    def compatibility_of(self, werk):
        return self._compatibilities[werk["compatible"]]


def _compiled_werks_dir():
    return Path(cmk.utils.paths.share_dir, "werks")


def load():
    werks = {}
    # The suppressions are needed because of https://github.com/PyCQA/pylint/issues/1660
    for file_name in itertools.chain(
            _compiled_werks_dir().glob("werks"),  # pylint: disable=no-member
            _compiled_werks_dir().glob("werks-*")):  # pylint: disable=no-member
        werks.update(load_precompiled_werks_file(file_name))
    return werks


def load_precompiled_werks_file(path):
    with path.open() as fp:
        return {int(werk_id): werk for werk_id, werk in json.load(fp).iteritems()}


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
    # TODO: What's this? Can we simply nuke the fields below from all werks?
    "state",
    "targetversion",
}

_ALLOWED_WERK_FIELDS = _REQUIRED_WERK_FIELDS | _OPTIONAL_WERK_FIELDS


def _load_werk(path):
    werk = {
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
    with path.open("wb") as fp:
        json.dump(werks, fp, check_circular=False)


def write_as_text(werks, f, write_version=True):
    """Write the given werks to a file object

    This is used for creating a textual hange log for the released versions and the announcement mails.
    """
    translator = WerkTranslator()
    werklist = sort_by_version_and_component(werks.values())
    for version, version_group in itertools.groupby(werklist, key=lambda w: w["version"]):
        # write_version=False is used by the announcement mails
        if write_version:
            f.write("%s:\n" % version)
        for component, component_group in itertools.groupby(version_group,
                                                            key=translator.component_of):
            f.write("    %s:\n" % component.encode("utf-8"))
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

    f.write("    * %04d%s %s%s\n" % (werk["id"], prefix, werk["title"].encode("utf-8"), omit))

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


# Parses versions of Check_MK and converts them into comparable integers.
# This does not handle daily build numbers, only official release numbers.
# 1.2.4p1   -> 01020450001
# 1.2.4     -> 01020450000
# 1.2.4b1   -> 01020420100
# 1.2.3i1p1 -> 01020310101
# 1.2.3i1   -> 01020310100
def parse_check_mk_version(v):
    def extract_number(s):
        number = ''
        for i, c in enumerate(s):
            try:
                int(c)
                number += c
            except ValueError:
                s = s[i:]
                return number and int(number) or 0, s
        return number and int(number) or 0, ''

    parts = v.split('.')
    while len(parts) < 3:
        parts.append("0")

    major, minor, rest = parts
    sub, rest = extract_number(rest)

    if not rest:
        val = 50000
    elif rest[0] == 'p':
        num, rest = extract_number(rest[1:])
        val = 50000 + num
    elif rest[0] == 'i':
        num, rest = extract_number(rest[1:])
        val = 10000 + num * 100

        if rest and rest[0] == 'p':
            num, rest = extract_number(rest[1:])
            val += num
    elif rest[0] == 'b':
        num, rest = extract_number(rest[1:])
        val = 20000 + num * 100

    return int('%02d%02d%02d%05d' % (int(major), int(minor), sub, val))
