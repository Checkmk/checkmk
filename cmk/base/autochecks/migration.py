#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Deal with all sorts of legacy aand invalid formats of autochecks"""

from pathlib import Path
from typing import Any, Dict, Sequence, Tuple, Union

from cmk.utils.check_utils import maincheckify
from cmk.utils.exceptions import MKGeneralException
from cmk.utils.type_defs import Item

from .utils import AutocheckEntry


def load_unmigrated_autocheck_entries(
    path: Path, check_variables: Dict[str, Any]
) -> Sequence[AutocheckEntry]:
    try:
        with path.open(encoding="utf-8") as f:
            raw_file_content = f.read().strip()
            assert raw_file_content
    except (FileNotFoundError, AssertionError):
        return []

    try:
        # This evaluation was needed to resolve references to variables in the autocheck
        # default parameters and to evaluate data structure declarations containing references to
        # variables.
        # Since Checkmk 2.0 we have a better API and need it only for compatibility. The parameters
        # are resolved now *before* they are written to the autochecks file, and earlier autochecks
        # files are resolved during cmk-update-config.
        return [
            parse_autocheck_entry(entry)
            for entry in eval(  # pylint: disable=eval-used
                raw_file_content, check_variables, check_variables
            )
            if isinstance(entry, (tuple, dict))
        ]
    except (SyntaxError, NameError, TypeError, ValueError) as exc:
        raise MKGeneralException(f"Unable to parse autochecks file {path}: {exc}")


def parse_autocheck_entry(entry: Union[Tuple, Dict]) -> AutocheckEntry:
    check_plugin_name, item, parameters, service_labels = (
        _parse_pre_16_tuple_autocheck_entry(entry)
        if isinstance(entry, tuple)
        else _parse_dict_autocheck_entry(entry)
    )

    return AutocheckEntry.load(
        {
            "check_plugin_name": _parse_pre_20_check_plugin_name(check_plugin_name),
            "item": _parse_pre_20_item(item),
            "parameters": parameters,
            "service_labels": service_labels if isinstance(service_labels, dict) else {},
        }
    )


def _parse_dict_autocheck_entry(entry: Dict) -> Tuple[object, object, object, object]:
    if set(entry) != {"check_plugin_name", "item", "parameters", "service_labels"}:
        raise TypeError(f"Invalid autocheck: Wrong keys found: {entry!r}")

    return entry["check_plugin_name"], entry["item"], entry["parameters"], entry["service_labels"]


def _parse_pre_20_check_plugin_name(raw_name: object) -> str:
    try:
        assert isinstance(raw_name, str)
        return maincheckify(raw_name)
    except AssertionError:
        raise TypeError(f"Invalid autocheck: Check plugin type: {raw_name!r}")


def _parse_pre_16_tuple_autocheck_entry(entry: Tuple) -> Tuple[object, object, object, object]:
    try:
        # drop hostname, legacy format with host in first column
        raw_name, raw_item, raw_params = entry[1:] if len(entry) == 4 else entry
    except ValueError as exc:
        raise ValueError(f"Invalid autocheck: {entry!r}") from exc
    return raw_name, raw_item, raw_params, {}


def _parse_pre_20_item(item: object) -> Item:
    if isinstance(item, (int, float)):
        # NOTE: We exclude complex here. :-)
        return str(int(item))
    if item is None or isinstance(item, str):
        return item
    raise TypeError(f"Invalid autocheck: Item should be Optional[str]: {item!r}")
