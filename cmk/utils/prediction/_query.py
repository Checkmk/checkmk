#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from pathlib import Path

from livestatus import SingleSiteConnection

from cmk.utils import pnp_cleanup
from cmk.utils.hostaddress import HostName
from cmk.utils.metrics import MetricName
from cmk.utils.servicename import ServiceName

from ._grouping import Timegroup
from ._paths import DATA_FILE_SUFFIX, INFO_FILE_SUFFIX
from ._prediction import PredictionData, PredictionInfo


@dataclass(frozen=True, kw_only=True)
class PredictionQuerier:
    livestatus_connection: SingleSiteConnection
    host_name: HostName
    service_name: ServiceName
    metric_name: MetricName

    def query_available_predictions(self) -> Iterator[PredictionInfo]:
        available_prediction_files = frozenset(
            self._filter_prediction_files_by_metric(self._query_prediction_files())
        )
        yield from (
            PredictionInfo.model_validate_json(self._query_prediction_file_content(prediction_file))
            for prediction_file in available_prediction_files
            if prediction_file.suffix == INFO_FILE_SUFFIX
            and prediction_file.with_suffix(DATA_FILE_SUFFIX) in available_prediction_files
        )

    def query_prediction_data(self, time_group: Timegroup) -> PredictionData:
        return PredictionData.model_validate_json(
            self._query_prediction_file_content(
                Path(pnp_cleanup(self.metric_name), time_group),
            )
        )

    def _filter_prediction_files_by_metric(
        self, prediction_files: Iterable[Path]
    ) -> Iterator[Path]:
        metric_dir = Path(pnp_cleanup(self.metric_name))
        yield from (
            prediction_file
            for prediction_file in prediction_files
            if metric_dir in prediction_file.parents
        )

    def _query_prediction_files(self) -> Iterator[Path]:
        yield from (
            Path(prediction_file)
            for prediction_file in self.livestatus_connection.query_row(
                (
                    "GET services\n"
                    "Columns: prediction_files\n"
                    f"Filter: host_name = {self.host_name}\n"
                    f"Filter: description = {self.service_name}"
                )
            )[0]
        )

    def _query_prediction_file_content(self, relative_file_path: Path) -> bytes:
        return b"\n".join(
            self.livestatus_connection.query_row(
                (
                    "GET services\n"
                    f"Columns: prediction_file:file:{relative_file_path}\n"
                    f"Filter: host_name = {self.host_name}\n"
                    f"Filter: description = {self.service_name}"
                )
            )
        )
