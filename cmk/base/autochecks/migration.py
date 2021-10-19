#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Deal with all sorts of legacy aand invalid formats of autochecks"""

from typing import Dict, Iterable, Sequence, Tuple, Union

from cmk.utils.check_utils import maincheckify
from cmk.utils.type_defs import CheckPluginName, Item, LegacyCheckParameters

from cmk.base.check_utils import AutocheckService
from cmk.base.discovered_labels import ServiceLabel

from .utils import AutocheckEntry


def parse_autocheck_entry(entry: Union[Tuple, Dict]) -> AutocheckEntry:
    check_plugin_name, item, parameters, dict_service_labels = (
        _parse_pre_16_tuple_autocheck_entry(entry)
        if isinstance(entry, tuple)
        else _parse_dict_autocheck_entry(entry)
    )

    return AutocheckEntry(
        check_plugin_name=_parse_pre_20_check_plugin_name(check_plugin_name),
        item=_parse_pre_20_item(item),
        discovered_parameters=_parse_parameters(parameters),
        service_labels={
            l.name: l for l in _parse_discovered_service_label_from_dict(dict_service_labels)
        },
    )


def _parse_dict_autocheck_entry(entry: Dict) -> Tuple[object, object, object, object]:
    if set(entry) != {"check_plugin_name", "item", "parameters", "service_labels"}:
        raise TypeError(f"Invalid autocheck: Wrong keys found: {entry!r}")

    return entry["check_plugin_name"], entry["item"], entry["parameters"], entry["service_labels"]


def _parse_pre_20_check_plugin_name(raw_name: object) -> CheckPluginName:
    try:
        assert isinstance(raw_name, str)
        return CheckPluginName(maincheckify(raw_name))
    except (AssertionError, TypeError, ValueError):
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


def _parse_parameters(parameters: object) -> LegacyCheckParameters:
    # Make sure it's a 'LegacyCheckParameters' (mainly done for mypy).
    if parameters is None or isinstance(parameters, (dict, tuple, list, str)):
        return parameters
    # I have no idea what else it could be (LegacyCheckParameters is quite pointless).
    raise ValueError(f"Invalid autocheck: invalid parameters: {parameters!r}")


def _parse_discovered_service_label_from_dict(
    dict_service_labels: object,
) -> Iterable[ServiceLabel]:
    if not isinstance(dict_service_labels, dict):
        return
    yield from (
        ServiceLabel(str(key), str(value))
        for key, value in dict_service_labels.items()
        if key is not None
    )


def deduplicate_autochecks(autochecks: Sequence[AutocheckService]) -> Sequence[AutocheckService]:
    """Cleanup duplicates that versions pre 1.6.0p8 may have introduced in the autochecks file

    The first service is kept:

    >>> deduplicate_autochecks([
    ...    AutocheckService(CheckPluginName('a'), None, "desctiption 1", None),
    ...    AutocheckService(CheckPluginName('a'), None, "description 2", None),
    ... ])[0].description
    'desctiption 1'

    """
    return list({a.id(): a for a in reversed(autochecks)}.values())
