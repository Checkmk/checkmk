#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Iterable
from functools import partial
from typing import Literal

from cmk.utils.i18n import _
from cmk.utils.version import parse_check_mk_version

from cmk.werks.models import Class, Compatibility, Werk, WerkV2Base, WerkV3

_CLASS_SORTING_VALUE = {
    Class.FEATURE: 1,
    Class.SECURITY: 2,
    Class.FIX: 3,
}

_COMPATIBLE_SORTING_VALUE = {
    Compatibility.NOT_COMPATIBLE: 1,
    Compatibility.COMPATIBLE: 3,
}


class WebsiteWerk(WerkV2Base):
    # ATTENTION! If you change this model, you have to inform
    # the website team first! They rely on those fields.
    """
    This Model is used to built up a file containing all werks.
    The file is called all_werks.json or all_werks_v2.json
    """

    versions: dict[str, str]
    product: Literal["cmk", "cma", "checkmk_kube_agent"]


def get_sort_key_by_version_and_component(
    translator: "WerkTranslator", werk: Werk | WerkV3
) -> tuple[str | int, ...]:
    return (
        -parse_check_mk_version(werk.version),
        translator.translate_component(werk.component),
        _CLASS_SORTING_VALUE.get(werk.class_, 99),
        -werk.level.value,
        # GuiWerk alters this tuple, and adds an element here!
        _COMPATIBLE_SORTING_VALUE.get(werk.compatible, 99),
        werk.title,
    )


def sort_by_version_and_component(werks: Iterable[Werk | WerkV3]) -> list[Werk | WerkV3]:
    translator = WerkTranslator()
    return sorted(werks, key=partial(get_sort_key_by_version_and_component, translator))


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
            "agents": _("Agent Bakery"),
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

    def classes(self) -> list[tuple[str, str]]:
        return list(self._classes.items())

    def class_of(self, werk: Werk | WerkV3) -> str:
        return self._classes[werk.class_.value]  # TODO: remove .value

    def components(self) -> list[tuple[str, str]]:
        return list(self._components.items())

    def component_of(self, werk: Werk | WerkV3) -> str:
        c = werk.component
        return self._components.get(c, c)

    def translate_component(self, component: str) -> str:
        return self._components.get(component, component)

    def levels(self) -> list[tuple[int, str]]:
        return list(self._levels.items())

    def level_of(self, werk: Werk) -> str:
        return self._levels[werk.level.value]  # TODO: remove .value
