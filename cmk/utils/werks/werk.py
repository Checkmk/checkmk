#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import datetime
from collections.abc import Iterable
from enum import Enum
from functools import partial
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from cmk.utils.exceptions import MKGeneralException
from cmk.utils.i18n import _
from cmk.utils.version import parse_check_mk_version


class WerkError(MKGeneralException, TypeError):
    pass


class Edition(Enum):
    # would love to use cmk.utils.version.Edition
    # but pydantic does not understand it.
    CRE = "cre"
    CSE = "cse"
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


class WerkV2Base(BaseModel):
    # ATTENTION! If you change this model, you have to inform
    # the website team first! They rely on those fields.

    model_config = ConfigDict(extra="forbid")

    werk_version: Literal["2"] = Field(default="2", alias="__version__")
    id: int
    class_: Class = Field(alias="class")
    component: str
    level: Level
    date: datetime.datetime
    compatible: Compatibility
    edition: Edition
    description: str
    title: str

    @field_validator("level", mode="before")
    def parse_level(cls, v: str) -> Level:  # pylint: disable=no-self-argument
        try:
            return Level(int(v))
        except ValueError:
            raise ValueError(f"Expected level to be in (1, 2, 3). Got {v} instead")

    # TODO: CMK-14587
    # @field_validator("component")
    # def parse_component(cls, v: str) -> str:  # pylint: disable=no-self-argument
    #     components = {k for k, _ in WerkTranslator().components()}
    #     if v not in components:
    #         raise TypeError(f"Component {v} not know. Choose from: {components}")
    #     return v

    def to_json_dict(self) -> dict[str, object]:
        return self.model_dump(by_alias=True, mode="json")


class Werk(WerkV2Base):
    version: str

    # old werks contain some illegal versions
    # the next refactoring will move this code away from cmk, so we won't have access to Version
    # so we may also disable this right now.
    # @validator("version")
    # def parse_version(cls, v: str) -> str:  # pylint: disable=no-self-argument
    #     Version.from_str(v)
    #     return v

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> "Werk":
        return cls.model_validate(data)


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
    translator: "WerkTranslator", werk: Werk
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


def sort_by_version_and_component(werks: Iterable[Werk]) -> list[Werk]:
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
