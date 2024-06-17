#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import ast
import json
from logging import Logger
from pathlib import Path

import cmk.utils.paths

from cmk.update_config.registry import update_action_registry, UpdateAction


class ConvertCounters(UpdateAction):
    def __call__(self, logger: Logger) -> None:
        self.convert_counter_files(Path(cmk.utils.paths.counters_dir))

    @staticmethod
    def convert_counter_files(counters_path: Path) -> None:

        def is_json(raw: str) -> bool:
            try:
                _ = json.loads(raw)
            except json.JSONDecodeError:
                return False
            return True

        for f in counters_path.iterdir():
            content = f.read_text()

            if is_json(content):
                continue

            f.write_text(
                json.dumps(
                    [(k, repr(v)) for k, v in ast.literal_eval(content).items()],
                )
            )


update_action_registry.register(
    ConvertCounters(
        name="counters_conversion",
        title="Convert counter files",
        sort_index=101,  # can run whenever
    )
)
