#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import ast
import json
from collections.abc import Sequence
from logging import Logger
from pathlib import Path

import cmk.utils.paths

from cmk.update_config.registry import update_action_registry, UpdateAction


def _is_json(raw: str) -> bool:
    try:
        _ = json.loads(raw)
    except json.JSONDecodeError:
        return False
    return True


def _ls(counters_path: Path) -> Sequence[Path]:
    try:
        return list(counters_path.iterdir())
    except FileNotFoundError:
        return ()


class ConvertCounters(UpdateAction):
    def __call__(self, logger: Logger) -> None:
        self.convert_counter_files(Path(cmk.utils.paths.counters_dir), logger)

    @staticmethod
    def convert_counter_files(counters_path: Path, logger: Logger) -> None:
        msg_temp = "    '%s': %s"
        for f in _ls(counters_path):
            if not (content := f.read_text().strip()):
                logger.debug(msg_temp, "skipped (empty)", f)
                continue

            if _is_json(content):
                logger.debug(msg_temp, "skipped (already JSON)", f)
                continue

            logger.debug(msg_temp, "converting", f)
            try:
                f.write_text(
                    json.dumps(
                        [(k, repr(v)) for k, v in ast.literal_eval(content).items()],
                    )
                )
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
