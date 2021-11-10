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
from typing import Any, Dict

from six import ensure_str

import cmk.utils.paths
from cmk.utils.exceptions import MKGeneralException
from cmk.utils.i18n import _
from cmk.utils.version import parse_check_mk_version


# This class is used to avoid repeated construction of dictionaries, including
# *all* translation values.
class WerkTranslator:
    def __init__(self):
        super().__init__()
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
            "wato": _("Setup"),
            "notifications": _("Notifications"),
            "bi": _("BI"),
            "reporting": _("Reporting & availability"),
            "ec": _("Event console"),
            "livestatus": _("Livestatus"),
            "liveproxy": _("Livestatus proxy"),
            "inv": _("HW/SW inventory"),
            "rest-api": _("REST API"),
            # CEE
            "cmc": _("The Checkmk Micro Core"),
            "setup": _("Setup, site management"),
            "config": _("Configuration generation"),
            "inline-snmp": _("Inline SNMP"),
            "agents": _("Agent bakery"),
            "metrics": _("Metrics system"),
            "alerts": _("Alert handlers"),
            "dcd": _("Dynamic host configuration"),
            "ntopng_integration": _("Ntopng integration"),
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
    for file_name in itertools.chain(
        _compiled_werks_dir().glob("werks"), _compiled_werks_dir().glob("werks-*")
    ):
        werks.update(load_precompiled_werks_file(file_name))
    return werks


def load_precompiled_werks_file(path):
    # ? what is the content of these files, to which the path shows
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
            raise MKGeneralException(_('Failed to load werk "%s": %s') % (werk_id, e))
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
        fp.write(json.dumps(werks, check_circular=False))


def write_as_text(werks, f, write_version=True):
    """Write the given werks to a file object

    This is used for creating a textual hange log for the released versions and the announcement mails.
    """
    translator = WerkTranslator()
    werklist = sort_by_version_and_component(werks.values())
    for version, version_group in itertools.groupby(werklist, key=lambda w: w["version"]):
        # write_version=False is used by the announcement mails
        if write_version:
            f.write("%s:\n" % ensure_str(version))  # pylint: disable= six-ensure-str-bin-call
        for component, component_group in itertools.groupby(
            version_group, key=translator.component_of
        ):
            f.write("    %s:\n" % ensure_str(component))  # pylint: disable= six-ensure-str-bin-call
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
    # ? exact type of werk is not known; it depends again on the werklist dictionary
    f.write(
        "    * %04d%s %s%s\n"
        % (
            werk["id"],
            prefix,
            ensure_str(werk["title"]),  # pylint: disable= six-ensure-str-bin-call
            omit,
        )
    )

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
    return sorted(
        werks,
        key=lambda w: (
            -parse_check_mk_version(w["version"]),
            translator.component_of(w),
            _CLASS_SORTING_VALUE.get(w["class"], 99),
            -w["level"],
            _COMPATIBLE_SORTING_VALUE.get(w["compatible"], 99),
            w["title"],
        ),
    )


def sort_by_date(werks):
    return sorted(werks, key=lambda w: w["date"], reverse=True)
