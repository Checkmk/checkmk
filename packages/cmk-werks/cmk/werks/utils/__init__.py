#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import itertools
from collections.abc import Iterable, Iterator
from functools import partial
from pathlib import Path
from typing import IO

from pydantic import RootModel, TypeAdapter

from cmk.ccc.version import parse_check_mk_version
from cmk.werks import load_werk
from cmk.werks.models import Class, Compatibility, EditionV2, EditionV3, WerkV1, WerkV2, WerkV3

Werks = RootModel[dict[int, WerkV2 | WerkV3]]

_CLASS_SORTING_VALUE = {
    Class.FEATURE: 1,
    Class.SECURITY: 2,
    Class.FIX: 3,
}

_COMPATIBLE_SORTING_VALUE = {
    Compatibility.NOT_COMPATIBLE: 1,
    Compatibility.COMPATIBLE: 3,
}


def load_precompiled_werks_file(path: Path) -> dict[int, WerkV2 | WerkV3]:
    # ? what is the content of these files, to which the path shows
    # There is no performance issue with this TypeAdapter call
    # nosemgrep: type-adapter-detected
    adapter = TypeAdapter(dict[int, WerkV3 | WerkV2 | WerkV1])
    with path.open("r", encoding="utf-8") as f:

        def generator() -> Iterator[tuple[int, WerkV2 | WerkV3]]:
            for werk_id, werk in adapter.validate_json(f.read()).items():
                if isinstance(werk, WerkV1):
                    yield werk_id, werk.to_werk()
                else:
                    yield werk_id, werk

        return dict(generator())


def get_sort_key_by_version_and_component(
    translator: "WerkTranslator", werk: WerkV2 | WerkV3
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


def sort_by_version_and_component(werks: Iterable[WerkV2 | WerkV3]) -> list[WerkV2 | WerkV3]:
    translator = WerkTranslator()
    return sorted(werks, key=partial(get_sort_key_by_version_and_component, translator))


# This class is used to avoid repeated construction of dictionaries, including
# *all* translation values.
class WerkTranslator:
    def __init__(self) -> None:
        super().__init__()
        self._classes = {
            "feature": "New feature",
            "fix": "Bug fix",
            "security": "Security fix",
        }
        self._components = {
            # CRE
            "core": "Core & setup",
            "checks": "Checks & agents",
            "multisite": "User interface",
            "wato": "Setup",
            "notifications": "Notifications",
            "bi": "BI",
            "reporting": "Reporting & availability",
            "ec": "Event console",
            "livestatus": "Livestatus",
            "liveproxy": "Livestatus proxy",
            "inv": "HW/SW Inventory",
            "rest-api": "REST API",
            # CEE
            "cmc": "The Checkmk Micro Core",
            "setup": "Setup, site management",
            "config": "Configuration generation",
            "inline-snmp": "Inline SNMP",
            "agents": "Agent Bakery",
            "metrics": "Metrics system",
            "alerts": "Alert handlers",
            "dcd": "Dynamic host configuration",
            "ntopng_integration": "Ntopng integration",
            # CMK-OMD
            "omd": "Site management",
            "rpm": "RPM packaging",
            "deb": "DEB packaging",
            "nagvis": "NagVis",
            "packages": "Other components",
            "distros": "Linux distributions",
        }
        self._levels = {
            1: "Trivial change",
            2: "Prominent change",
            3: "Major change",
        }

    def classes(self) -> list[tuple[str, str]]:
        return list(self._classes.items())

    def class_of(self, werk: WerkV2 | WerkV3) -> str:
        return self._classes[werk.class_.value]  # TODO: remove .value

    def components(self) -> list[tuple[str, str]]:
        return list(self._components.items())

    def component_of(self, werk: WerkV2 | WerkV3) -> str:
        c = werk.component
        return self._components.get(c, c)

    def translate_component(self, component: str) -> str:
        return self._components.get(component, component)

    def levels(self) -> list[tuple[int, str]]:
        return list(self._levels.items())

    def level_of(self, werk: WerkV2 | WerkV3) -> str:
        return self._levels[werk.level.value]  # TODO: remove .value


def edition_v2_to_v3(edition: EditionV2) -> EditionV3:
    mapping = {
        EditionV2.CRE: EditionV3.COMMUNITY,
        EditionV2.CEE: EditionV3.PRO,
        EditionV2.CCE: EditionV3.ULTIMATE,
        EditionV2.CME: EditionV3.ULTIMATEMT,
        EditionV2.CSE: EditionV3.CLOUD,
    }
    return mapping[edition]


def load_raw_files(werks_dir: Path) -> list[WerkV2 | WerkV3]:
    werks: list[WerkV2 | WerkV3] = []
    for file_name in werks_dir.glob("[0-9]*"):
        try:
            werks.append(load_werk(file_content=file_name.read_text(), file_name=file_name.name))
        except Exception as e:
            raise RuntimeError(f"Could not parse werk {file_name.absolute()}") from e
    return werks


def write_precompiled_werks(path: Path, werks: dict[int, WerkV2 | WerkV3]) -> None:
    with path.open("w", encoding="utf-8") as fp:
        fp.write(Werks.model_validate(werks).model_dump_json(by_alias=True))


def has_content(description: str) -> bool:
    return bool(description.strip())


# this function is used from the bauwelt repo. TODO: move script from bauwelt into this repo
# TODO: use a jinja template for this, and move it to .announce
def write_as_text(
    werks: dict[int, WerkV2 | WerkV3], f: IO[str], write_version: bool = True
) -> None:
    """Write the given werks to a file object

    This is used for creating a textual hange log for the released versions.
    """
    # TODO: reuse code from  .announce and replace with two jinja templates,
    # one for txt, one for markdown
    translator = WerkTranslator()
    werklist = sort_by_version_and_component(werks.values())
    for version, version_group in itertools.groupby(werklist, key=lambda w: w.version):
        # write_version=False is used by the announcement mails
        if write_version:
            f.write(f"{version}:\n")
        for component, component_group in itertools.groupby(
            version_group, key=translator.component_of
        ):
            f.write(f"    {component}:\n")
            for werk in component_group:
                write_werk_as_text(f, werk)
            f.write("\n")
        f.write("\n")


def write_werk_as_text(f: IO[str], werk: WerkV2 | WerkV3) -> None:
    # TODO: use jinja templates of .announce
    prefix = ""
    if werk.class_ == Class.FIX:
        prefix = " FIX:"
    elif werk.class_ == Class.SECURITY:
        prefix = " SEC:"

    # See following commits...
    if has_content(werk.description):
        omit = "..."
    else:
        omit = ""

    f.write(f"    * {werk.id:0>4}{prefix} {werk.title}{omit}\n")

    if werk.compatible == Compatibility.NOT_COMPATIBLE:
        f.write("            NOTE: Please refer to the migration notes!\n")
