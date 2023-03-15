#!/usr/bin/env python3
# Copyright (C) 2023 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import abc
import datetime
from enum import Enum
from typing import NamedTuple, Union

from cmk.utils.exceptions import MKGeneralException
from cmk.utils.i18n import _
from cmk.utils.version import parse_check_mk_version


class WerkError(MKGeneralException):
    pass


class Edition(Enum):
    # would love to use cmk.utils.version.Edition
    # but pydantic does not understand it.
    CRE = "cre"
    CEE = "cee"
    CCE = "cce"
    CME = "cme"
    CFE = "cfe"


class Level(Enum):
    LEVEL_1 = 1
    LEVEL_2 = 2
    LEVEL_3 = 3


class Compatibility(Enum):
    COMPATIBLE = "yes"
    NOT_COMPATIBLE = "no"


class Class(Enum):
    FEATURE = "feature"
    FIX = "fix"
    SECURITY = "security"


_CLASS_SORTING_VALUE = {
    Class.FEATURE: 1,
    Class.SECURITY: 2,
    Class.FIX: 3,
}

_COMPATIBLE_SORTING_VALUE = {
    Compatibility.NOT_COMPATIBLE: 1,
    Compatibility.COMPATIBLE: 3,
}


class Werk(NamedTuple):
    compatible: Compatibility
    version: str
    title: str
    id: int
    date: datetime.datetime
    description: Union[str, "NoWiki"]
    level: Level
    class_: Class
    component: str
    edition: Edition

    def sort_by_version_and_component(self, translator: "WerkTranslator") -> tuple[str | int, ...]:
        return (
            -parse_check_mk_version(self.version),
            translator.translate_component(self.component),
            _CLASS_SORTING_VALUE.get(self.class_, 99),
            -self.level.value,
            # GuiWerk alters this tuple, and adds an element here!
            _COMPATIBLE_SORTING_VALUE.get(self.compatible, 99),
            self.title,
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

    def classes(self) -> list[tuple[str, str]]:
        return list(self._classes.items())

    def class_of(self, werk: Werk) -> str:
        return self._classes[werk.class_.value]  # TODO: remove .value

    def components(self) -> list[tuple[str, str]]:
        return list(self._components.items())

    def component_of(self, werk: Werk) -> str:
        c = werk.component
        return self._components.get(c, c)

    def translate_component(self, component: str) -> str:
        return self._components.get(component, component)

    def levels(self) -> list[tuple[int, str]]:
        return list(self._levels.items())

    def level_of(self, werk: Werk) -> str:
        return self._levels[werk.level.value]  # TODO: remove .value


class NoWiki:
    def __init__(self, value: list[str]):
        self.value = value


class RawWerk(abc.ABC):
    @abc.abstractmethod
    def to_json_dict(self) -> dict[str, object]:
        """
        returns a python dict structure that can be serialized to json
        """

    @abc.abstractmethod
    def to_werk(self) -> Werk:
        ...
