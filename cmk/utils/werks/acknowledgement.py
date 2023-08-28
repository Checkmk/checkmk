#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterable, Sequence
from functools import cache
from typing import NamedTuple

import cmk.utils.paths
import cmk.utils.store as store

from . import load
from .werk import Compatibility, Werk, WerkTranslator

ACKNOWLEDGEMENT_PATH = cmk.utils.paths.var_dir + "/acknowledged_werks.mk"
TIME_FORMAT = "%Y-%m-%d %H:%M:%S"


class GuiWerk(NamedTuple):
    """
    Holds original Werk and attributes only used for the GUI
    """

    werk: Werk

    def sort_by_version_and_component(self, translator: WerkTranslator) -> tuple[str | int, ...]:
        werk_result = self.werk.sort_by_version_and_component(translator)
        result = (*werk_result[:4], int(self.acknowledged), *werk_result[4:])
        return result

    @property
    def acknowledged(self) -> bool:
        return self.werk.id in load_acknowledgements() or version_is_pre_127(self.werk.version)

    # @property
    # @cache
    # does not work with mypy: https://github.com/python/mypy/issues/5858
    # so we fall back to a function:
    def get_date_formatted(self) -> str:
        # return date formatted as string in local timezone
        return self.werk.date.astimezone().strftime(TIME_FORMAT)


def load_acknowledgements() -> set[int]:
    return set(store.load_object_from_file(ACKNOWLEDGEMENT_PATH, default=[]))


def save_acknowledgements(acknowledged_werks: list[int]) -> None:
    store.save_object_to_file(ACKNOWLEDGEMENT_PATH, acknowledged_werks)


def version_is_pre_127(version: str) -> bool:
    return version.startswith("1.2.5") or version.startswith("1.2.6")


def sort_by_date(werks: Iterable[GuiWerk]) -> list[GuiWerk]:
    return sorted(werks, key=lambda w: w.werk.date, reverse=True)


def unacknowledged_incompatible_werks() -> list[GuiWerk]:
    return sort_by_date(
        werk
        for werk in load_werk_entries()
        if werk.werk.compatible == Compatibility.NOT_COMPATIBLE and not werk.acknowledged
    )


@cache
def load_werk_entries() -> Sequence[GuiWerk]:
    werks_raw = load()
    werks = []
    for werk in werks_raw.values():
        werks.append(
            GuiWerk(
                werk=werk,
            )
        )
    return werks
