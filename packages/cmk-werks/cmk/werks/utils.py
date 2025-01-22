#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import argparse
import itertools
from collections.abc import Iterable, Iterator
from functools import partial
from pathlib import Path
from typing import IO

from pydantic import RootModel, TypeAdapter

from cmk.ccc.i18n import _
from cmk.ccc.version import __version__, parse_check_mk_version, Version
from cmk.werks import load_werk
from cmk.werks.models import Class, Compatibility, Edition, Werk, WerkV1

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


def path_dir(value: str) -> Path:
    result = Path(value)
    if not result.exists():
        raise argparse.ArgumentTypeError(f"File or directory does not exist: {result}")
    if not result.is_dir():
        raise argparse.ArgumentTypeError(f"{result} is not a directory")
    return result


def main_precompile(args: argparse.Namespace) -> None:
    werks_list = load_raw_files(args.werk_dir)

    filter_by_edition = (
        Edition(args.filter_by_edition) if args.filter_by_edition is not None else None
    )
    current_version = Version.from_str(__version__)

    def _filter(werk: Werk) -> bool:
        if filter_by_edition is not None and werk.edition != filter_by_edition:
            return False
        # only include werks of this major version:
        if Version.from_str(werk.version).base != current_version.base:
            return False
        return True

    werks = {werk.id: werk for werk in werks_list if _filter(werk)}

    write_precompiled_werks(args.destination, werks)


def main_changelog(args: argparse.Namespace) -> None:
    werks: dict[int, Werk] = {}
    for path in (Path(p) for p in args.precompiled_werk):
        werks.update(load_precompiled_werks_file(path))

    with open(args.destination, "w", encoding="utf-8") as f:
        write_as_text(werks, f)


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


def has_content(description: str) -> bool:
    return bool(description.strip())


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


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command")
    subparsers.required = True

    parser_changelog = subparsers.add_parser("changelog", help="Show who worked on a werk")
    parser_changelog.add_argument("destination")
    parser_changelog.add_argument("precompiled_werk", nargs="+")
    parser_changelog.set_defaults(func=main_changelog)

    parser_precompile = subparsers.add_parser(
        "precompile", help="Collect werk files of current major version into json."
    )
    parser_precompile.add_argument("werk_dir", type=path_dir, help=".werk folder in the git root")
    parser_precompile.add_argument("destination", type=Path)
    parser_precompile.add_argument(
        "--filter-by-edition",
        default=None,
        choices=list(x.value for x in Edition),
    )
    parser_precompile.set_defaults(func=main_precompile)

    return parser.parse_args()


def main():
    args = parse_arguments()
    args.func(args)


if __name__ == "__main__":
    main()
