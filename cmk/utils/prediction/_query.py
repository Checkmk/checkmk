#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

from livestatus import Query as OldQuery
from livestatus import SingleSiteConnection

from cmk.agent_based.prediction_backend import PredictionInfo
from cmk.ccc.hostaddress import HostName
from cmk.livestatus_client.expressions import And, LqSafe
from cmk.livestatus_client.queries import Query
from cmk.livestatus_client.tables.services import Services
from cmk.utils.servicename import ServiceName

from ._prediction import PredictionData, PredictionStore


@dataclass(frozen=True, kw_only=True)
class PredictionQuerier:
    livestatus_connection: SingleSiteConnection
    host_name: HostName
    service_name: ServiceName

    def query_available_predictions(self, metric: str) -> Iterator[PredictionInfo]:
        available_prediction_files = frozenset(
            PredictionStore.filter_prediction_files_by_metric(
                metric, self._query_prediction_files()
            )
        )
        yield from (
            PredictionInfo.model_validate_json(self._query_prediction_file_content(prediction_file))
            for prediction_file in available_prediction_files
            if prediction_file.suffix == PredictionStore.INFO_FILE_SUFFIX
            and prediction_file.with_suffix(PredictionStore.DATA_FILE_SUFFIX)
            in available_prediction_files
        )

    def query_prediction_data(self, meta: PredictionInfo) -> PredictionData:
        rel_filename = PredictionStore.relative_data_file(meta)
        return PredictionData.model_validate_json(self._query_prediction_file_content(rel_filename))

    def _service_filter(self) -> And:
        return And(
            Services.host_name == LqSafe(self.host_name),
            Services.description == LqSafe(self.service_name),
        )

    def _query_prediction_files(self) -> Iterator[Path]:
        query = Query(
            [Services.prediction_files],
            self._service_filter(),
        )
        yield from (
            Path(prediction_file)
            for prediction_file in self.livestatus_connection.query_row(OldQuery(query))[0]
        )

    def _query_prediction_file_content(self, relative_file_path: Path) -> bytes:
        # Dynamic column names are not supported by the query builder, so we have to string-based query here.
        return b"\n".join(
            self.livestatus_connection.query_row(
                "GET services\n"
                f"Columns: prediction_file:file:{relative_file_path}\n"
                f"Filter: host_name = {LqSafe(self.host_name)}\n"
                f"Filter: description = {LqSafe(self.service_name)}"
            )
        )
