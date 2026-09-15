#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterable, Iterator
from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from cmk.agent_based.prediction_backend import PredictionInfo

_DATA_FILE_SUFFIX: Final = ""
_INFO_FILE_SUFFIX: Final = ".info"
_NAME_TEMPLATE: Final = (
    "{meta.metric}/{meta.params.period}-{meta.valid_interval[0]}-{meta.direction}"
)


@dataclass(frozen=True, kw_only=True)
class PredictionFiles:
    info: Path
    data: Path

    def unlink(self) -> None:
        for path in (self.info, self.data):
            with suppress(OSError):
                path.unlink()


def relative_data_file(meta: PredictionInfo) -> Path:
    return Path(_NAME_TEMPLATE.format(meta=meta)).with_suffix(_DATA_FILE_SUFFIX)


def meta_file_template(directory: Path) -> str:
    safe_directory = str(directory).replace("{", "{{").replace("}", "}}")
    return f"{safe_directory}/{_NAME_TEMPLATE}{_INFO_FILE_SUFFIX}"


def iter_prediction_files(directory: Path) -> Iterator[PredictionFiles]:
    if not directory.exists():
        return
    for info_file in directory.rglob(f"*{_INFO_FILE_SUFFIX}"):
        if info_file.is_dir():
            continue
        yield PredictionFiles(info=info_file, data=info_file.with_suffix(_DATA_FILE_SUFFIX))


def iter_complete_info_files(metric: str, prediction_files: Iterable[Path]) -> Iterator[Path]:
    of_metric = frozenset(
        prediction_file for prediction_file in prediction_files if metric in prediction_file.parts
    )
    yield from (
        prediction_file
        for prediction_file in of_metric
        if prediction_file.suffix == _INFO_FILE_SUFFIX
        and prediction_file.with_suffix(_DATA_FILE_SUFFIX) in of_metric
    )
