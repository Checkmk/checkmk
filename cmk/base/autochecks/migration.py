#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Deal with all sorts of legacy aand invalid formats of autochecks"""

from typing import Sequence, Tuple

from cmk.utils.check_utils import maincheckify
from cmk.utils.type_defs import CheckPluginName

from cmk.base.check_utils import AutocheckService


def parse_pre_20_check_plugin_name(raw_name: object) -> CheckPluginName:
    try:
        assert isinstance(raw_name, str)
        return CheckPluginName(maincheckify(raw_name))
    except (AssertionError, TypeError, ValueError):
        raise TypeError(f"Invalid autocheck: Check plugin type: {raw_name!r}")


def parse_pre_16_tuple_autocheck_entry(entry: Tuple) -> Tuple[object, object, object]:
    try:
        # drop hostname, legacy format with host in first column
        raw_name, raw_item, raw_params = entry[1:] if len(entry) == 4 else entry
    except ValueError as exc:
        raise ValueError(f"Invalid autocheck: {entry!r}") from exc
    return raw_name, raw_item, raw_params


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
