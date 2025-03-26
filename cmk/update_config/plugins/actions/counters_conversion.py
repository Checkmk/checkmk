#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import ast
import json
from collections.abc import Mapping, Sequence
from logging import Logger
from pathlib import Path
from typing import override

import cmk.utils.paths

from cmk.update_config.registry import update_action_registry, UpdateAction


def _analyze_content(raw: str) -> tuple[bool, bool]:
    try:
        stores = json.loads(raw)
    except json.JSONDecodeError:
        return False, False
    return True, not stores or len(stores[0][0]) == 3


def _convert_from_2_4_beta_state(
    raw: str,
) -> Mapping[tuple[str, str, str | None], Mapping[str, str]]:
    stores = json.loads(raw)
    new: dict[tuple[str, str, str | None], dict[str, str]] = {}
    for (host, plugin, item, key), value in stores:
        new.setdefault((host, plugin, item), {})[key] = value
    return new


def _convert_from_2_3_state(raw: str) -> Mapping[tuple[str, str, str | None], Mapping[str, str]]:
    new: dict[tuple[str, str, str | None], dict[str, str]] = {}
    for (host, plugin, item, key), v in ast.literal_eval(raw).items():
        new.setdefault((host, plugin, item), {})[key] = repr(v)
    return new


def _ls(counters_path: Path) -> Sequence[Path]:
    try:
        return list(counters_path.iterdir())
    except FileNotFoundError:
        return ()


class ConvertCounters(UpdateAction):
    @override
    def __call__(self, logger: Logger) -> None:
        self.convert_counter_files(Path(cmk.utils.paths.counters_dir), logger)

    @staticmethod
    def convert_counter_files(counters_path: Path, logger: Logger) -> None:
        msg_temp = "    '%s': %s"
        for f in _ls(counters_path):
            if not (content := f.read_text().strip()):
                logger.debug(msg_temp, "skipped (empty)", f)
                continue

            is_json, is_latest = _analyze_content(content)
            if is_latest:
                logger.debug(msg_temp, "skipped (already new format)", f)
                continue

            logger.debug(msg_temp, "converting", f)
            try:
                new = (
                    _convert_from_2_4_beta_state(content)
                    if is_json
                    else _convert_from_2_3_state(content)
                )
                f.write_text(json.dumps(list(new.items())))
            except Exception as exc:
                # We've seen this conversion fail upon what seemed to be partially written files.
                # After the fact, we've never seen any traces of them.
                # At least continue with all the other files.
                logger.warning(msg_temp, f"failed ({exc})", f)


update_action_registry.register(
    ConvertCounters(
        name="counters_conversion",
        title="Convert counter files",
        # Run this action quite early on. In case the update is aborted before this is run,
        # all hosts using counters can not be monitored anymore _at all_.
        sort_index=21,
    )
)
