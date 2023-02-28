#!/usr/bin/env python3
# Copyright (C) 2023 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


# We need the typing_extensions TypedDict in order to have NotRequired to fill
# the __optional_keys__ instead of __required_keys__. IMHO this can be imported
# from typing directly as soon as we are on 3.11
from typing_extensions import NotRequired, TypedDict

from cmk.utils.i18n import _

# The class attribute cannot be set with the class-style definition
Werk = TypedDict(
    "Werk",
    {
        "class": str,
        "component": str,
        "date": int,
        "level": int,
        "title": str,
        "version": str,
        "compatible": str,
        "edition": str,
        "knowledge": NotRequired[
            str
        ],  # TODO: What's this? Can we simply nuke the fields below from all werks?
        "state": NotRequired[str],
        "id": NotRequired[int],
        "targetversion": NotRequired[str],
        "description": list[str],
    },
)

# This class is used to avoid repeated construction of dictionaries, including
# *all* translation values.
class WerkTranslator:
    def __init__(self) -> None:
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

    def classes(self) -> list[tuple[str, str]]:
        return list(self._classes.items())

    def class_of(self, werk: Werk) -> str:
        return self._classes[werk["class"]]

    def components(self) -> list[tuple[str, str]]:
        return list(self._components.items())

    def component_of(self, werk: Werk) -> str:
        c = werk["component"]
        return self._components.get(c, c)

    def levels(self) -> list[tuple[int, str]]:
        return list(self._levels.items())

    def level_of(self, werk: Werk) -> str:
        return self._levels[werk["level"]]

    def compatibilities(self) -> list[tuple[str, str]]:
        return list(self._compatibilities.items())

    def compatibility_of(self, werk: Werk) -> str:
        return self._compatibilities[werk["compatible"]]
