#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from itertools import zip_longest

from cmk.ccc.i18n import _

__all__ = [
    "make_diff",
    "make_diff_text",
]

PATH_COMPONENT = str | int
PATH_COMPONENTS = Sequence[PATH_COMPONENT]
DIFF_ITEM = tuple[PATH_COMPONENTS, str]
MISSING = object()


@dataclass(frozen=True, slots=True)
class DiffPath:
    components: PATH_COMPONENTS
    formatted: str


def make_diff(old: object, new: object) -> str:
    root = [] if isinstance(old, list | dict) else ["object"]
    diffs = sorted(_diff_values(root, old, new))  # sort by path, then message
    return "\n".join(msg for _path, msg in diffs)


def make_diff_text(old: object, new: object) -> str:
    """Creates a text representing the object differences for humans"""
    if old is None or new is None:
        raise ValueError("cannot diff to None")
    return make_diff(old, new) or _("Nothing was changed.")


def _format_value(value: object) -> str:
    if isinstance(value, str):
        value = value.replace('"', '\\"')
        return f'"{value}"'
    return str(value)


def _iter_path_components(
    components: tuple[PATH_COMPONENT | PATH_COMPONENTS, ...],
) -> Iterable[PATH_COMPONENT]:
    for component in components:
        if isinstance(component, str | int):
            yield component
        else:
            yield from component


def _diff_path(*components: PATH_COMPONENT | PATH_COMPONENTS) -> DiffPath:
    flattened = list(_iter_path_components(components))
    if len(flattened) == 1 and flattened[0] == "object":
        return DiffPath(flattened, "object")
    return DiffPath(flattened, "/".join(_format_value(x) for x in flattened))


def _diff_values(path_components: PATH_COMPONENTS, old: object, new: object) -> Iterable[DIFF_ITEM]:
    if isinstance(old, dict) and isinstance(new, dict):
        yield from __diff_dict(path_components, old, new)

    elif isinstance(old, list) and isinstance(new, list):
        yield from __diff_list(path_components, old, new)

    elif isinstance(old, set) and isinstance(new, set):
        yield from __diff_set(path_components, old, new)

    elif type(old) is not type(new) or old != new:
        yield (
            path_components,
            _("Value of {diff_path} changed from {val_t1} to {val_t2}.").format(
                diff_path=_diff_path(path_components).formatted,
                val_t1=_format_value(old),
                val_t2=_format_value(new),
            ),
        )


def __diff_dict(path_components: PATH_COMPONENTS, old: dict, new: dict) -> Iterable[DIFF_ITEM]:
    for key, old_value in old.items():
        sub_path = _diff_path(path_components, key)
        if key in new:
            yield from _diff_values(sub_path.components, old_value, new[key])
        else:
            yield (
                sub_path.components,
                _("Attribute {diff_path} with value {val_t1} removed.").format(
                    diff_path=sub_path.formatted,
                    val_t1=_format_value(old_value),
                ),
            )
    for key, new_value in new.items():
        if key not in old:
            sub_path = _diff_path(path_components, key)
            yield (
                sub_path.components,
                _("Attribute {diff_path} with value {val_t2} added.").format(
                    diff_path=sub_path.formatted,
                    val_t2=_format_value(new_value),
                ),
            )


def __diff_list(path_components: PATH_COMPONENTS, old: list, new: list) -> Iterable[DIFF_ITEM]:
    for idx, (old_item, new_item) in enumerate(zip_longest(old, new, fillvalue=MISSING)):
        sub_path = _diff_path(path_components, idx)
        if new_item is MISSING:
            yield (
                sub_path.components,
                _("Item {diff_path} with value {val_t1} removed.").format(
                    diff_path=sub_path.formatted, val_t1=_format_value(old_item)
                ),
            )
        elif old_item is MISSING:
            yield (
                sub_path.components,
                _("Item {diff_path} with value {val_t2} added.").format(
                    diff_path=sub_path.formatted, val_t2=_format_value(new_item)
                ),
            )
        else:
            yield from _diff_values(sub_path.components, old_item, new_item)


def __diff_set(path_components: PATH_COMPONENTS, old: set, new: set) -> Iterable[DIFF_ITEM]:
    for removed in old - new:
        yield (
            path_components,
            _("Item {diff_path} with value {val_t1} removed.").format(
                diff_path=_diff_path(path_components).formatted, val_t1=_format_value(removed)
            ),
        )
    for added in new - old:
        yield (
            path_components,
            _("Item {diff_path} with value {val_t2} added.").format(
                diff_path=_diff_path(path_components).formatted, val_t2=_format_value(added)
            ),
        )
