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

from cmk.ccc.i18n import _
from cmk.ccc.version import parse_check_mk_version
from cmk.werks import load_werk
from cmk.werks.models import Class, Compatibility, Werk, WerkV1, Edition, EditionV3

Werks = RootModel[dict[int, Werk]]

_CLASS_SORTING_VALUE = {
    Class.FEATURE: 1,
    Class.SECURITY: 2,
    Class.FIX: 3,
}

_COMPATIBLE_SORTING_VALUE = {
    Compatibility.NOT_COMPATIBLE: 1,
    Compatibility.COMPATIBLE: 3,
}


def load_precompiled_werks_file(path: Path) -> dict[int, Werk]:
    # ? what is the content of these files, to which the path shows
    # There is no performance issue with this TypeAdapter call
    # nosemgrep: type-adapter-detected
    adapter = TypeAdapter(dict[int, Werk | WerkV1])
    with path.open("r", encoding="utf-8") as f:

        def generator() -> Iterator[tuple[int, Werk]]:
            for werk_id, werk in adapter.validate_json(f.read()).items():
                if isinstance(werk, WerkV1):
                    yield werk_id, werk.to_werk()
                else:
                    yield werk_id, werk

        return dict(generator())


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
            "inv": _("HW/SW Inventory"),
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


def edition_v3_to_v2(edition: EditionV3) -> Edition:
    mapping = {
        EditionV3.COMMUNITY: Edition.CRE,
        EditionV3.PRO: Edition.CEE,
        EditionV3.ULTIMATE: Edition.CCE,
        EditionV3.ULTIMATEMT: Edition.CME,
        EditionV3.CLOUD: Edition.CSE,
    }
    return mapping[edition]


def load_raw_files(werks_dir: Path) -> list[Werk]:
    werks: list[Werk] = []
    for file_name in werks_dir.glob("[0-9]*"):
        try:
            werks.append(load_werk(file_content=file_name.read_text(), file_name=file_name.name))
        except Exception as e:
            raise RuntimeError(f"Could not parse werk {file_name.absolute()}") from e
    return werks


def write_precompiled_werks(path: Path, werks: dict[int, Werk]) -> None:
    with path.open("w", encoding="utf-8") as fp:
        fp.write(Werks.model_validate(werks).model_dump_json(by_alias=True))


def has_content(description: str) -> bool:
    return bool(description.strip())


# this function is used from the bauwelt repo. TODO: move script from bauwelt into this repo
# TODO: use a jinja template for this, and move it to .announce
def write_as_text(werks: dict[int, Werk], f: IO[str], write_version: bool = True) -> None:
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


def write_werk_as_text(f: IO[str], werk: Werk) -> None:
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
