#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections import Counter, defaultdict
from collections.abc import Iterator
from pathlib import Path
from typing import TypeVar

PACKAGE_ROOT = Path(__file__).resolve().parent.parent

COMPONENTS_FOLDER = Path(PACKAGE_ROOT, "src/components/")
UCL_FOLDER = Path(PACKAGE_ROOT, "ui-component-library/components/")

K = TypeVar("K")
V = TypeVar("V")


def unique_dict[K, V](data: Iterator[tuple[K, V]]) -> dict[K, V]:
    data_list = list(data)
    data_dict = dict(data_list)
    if len(data_list) == len(data_dict):
        return data_dict
    duplicates = [d for d, c in Counter(k for k, v in data_list).items() if c > 1]
    raise Exception(f"found duplicates: {duplicates}")


def component_remove_category_folder(all_files: dict[Path, Path]) -> Iterator[tuple[Path, Path]]:
    for relative, path in all_files.items():
        if relative.parts[0].islower():
            yield relative.relative_to(relative.parts[0]), path
        else:
            yield relative, path


def component_pick_one_from_folder(all_files: dict[Path, Path]) -> Iterator[tuple[Path, Path]]:
    by_folder: defaultdict[str, list[tuple[Path, Path]]] = defaultdict(list)
    for relative, path in all_files.items():
        if len(relative.parts) == 1:
            yield relative, path
        else:
            by_folder[relative.parts[0]].append((relative, path))

    for folder_name, contained_components in by_folder.items():
        for relative, path in contained_components:
            if path.stem == folder_name:
                yield Path(path.parts[-1]), path
                break
        else:
            raise Exception(
                f"Found a folder '{folder_name}' but no component in it with the same name"
            )


def component_remove_suffix(all_files: dict[Path, Path]) -> Iterator[tuple[str, Path]]:
    for relative, path in all_files.items():
        if len(relative.parts) == 1:
            yield relative.stem, path
        else:
            raise Exception("No folders expected at this point")


def load_component_names() -> Iterator[tuple[str, Path]]:
    # have to make some assumptions for the components:
    # 1. If there is a mixed-case vue file in a folder of the same name, it is assumed to be a single component
    # 2. If it's a lowecase folder directly below the components, its just a group and ignored
    all_files = {p.relative_to(COMPONENTS_FOLDER): p for p in COMPONENTS_FOLDER.glob("**/*.vue")}
    all_files = unique_dict(component_remove_category_folder(all_files))
    all_files = unique_dict(component_pick_one_from_folder(all_files))
    yield from component_remove_suffix(all_files)


def ucl_ignore_additional_files(all_files: dict[Path, Path]) -> Iterator[tuple[Path, Path]]:
    for relative, path in all_files.items():
        if path.name.endswith("Dev.vue") or path.name.endswith("Example.vue"):
            continue
        yield relative, path


def load_ucl_page_names() -> Iterator[tuple[str, Path]]:
    all_files = {p.relative_to(UCL_FOLDER): p for p in UCL_FOLDER.glob("**/*.vue")}
    all_files = unique_dict(ucl_ignore_additional_files(all_files))
    for relative, path in all_files.items():
        if not path.name.startswith("Ucl"):
            continue
        yield relative.stem.removeprefix("Ucl"), path


def load_ucl_helper_components() -> Iterator[tuple[str, Path]]:
    all_files = {p.relative_to(UCL_FOLDER): p for p in UCL_FOLDER.glob("**/*.vue")}
    all_files = unique_dict(ucl_ignore_additional_files(all_files))
    for relative, path in all_files.items():
        if path.name.startswith("Ucl"):
            continue
        yield relative.stem, path


def test_ucl_parity() -> None:
    """
    Files under ui-component-library/components/ have three recognised roles:

    * ``Ucl<X>.vue`` — canonical UCL page; must correspond 1:1 with a
      ``<X>`` component under src/components/.
    * ``Ucl<X>Dev.vue`` / ``Ucl<X>CodeExample.vue`` — Dev playground /
      raw-imported code-example file; not enforced for parity.
    * ``<Y>.vue`` (no ``Ucl`` prefix) — private helper imported by a sibling
      ``Ucl*Dev.vue`` page. It must NOT collide with a real component name
      and must live next to a ``Ucl*Dev.vue`` file (so an orphaned helper
      is still caught).
    """
    components: set[str] = set(unique_dict(load_component_names()))
    ucl: set[str] = set(unique_dict(load_ucl_page_names()))

    # make sure everything was found correctly
    assert len(components) > 55
    assert len(ucl) > 55

    # we don't talk about this:
    components.remove("RnbwApp")
    components.remove("RnbwCursor")

    # this is a implementation detail of CmkDropdown
    # and should probably be moved into CmkDropdown?
    components.remove("CmkSuggestions")

    # those components do not follow the usual path pattern,
    # but are stored inside CmkIcon
    ucl.remove("CmkMultitoneIcon")
    ucl.remove("CmkIconEmblem")

    assert components == ucl

    helpers = dict(unique_dict(load_ucl_helper_components()))
    for helper_name, helper_path in helpers.items():
        assert helper_name not in components, (
            f"Helper file {helper_path} shadows real component '{helper_name}'; "
            f"helpers must use a name that does not match any src/components/ entry."
        )
        sibling_dev_pages = list(helper_path.parent.glob("Ucl*Dev.vue"))
        assert sibling_dev_pages, (
            f"Helper file {helper_path} has no sibling Ucl*Dev.vue page; "
            f"helpers are only valid when imported by a Dev playground."
        )
