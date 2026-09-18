#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from functools import cached_property
from pathlib import Path
from typing import Protocol

from cmk.agent_based.prediction_backend import PredictionInfo
from cmk.ccc.hostaddress import HostName
from cmk.livestatus_client import SingleSiteConnection
from cmk.livestatus_client.expressions import And, LqSafe
from cmk.livestatus_client.queries import Query
from cmk.livestatus_client.tables.services import Services
from cmk.utils.prediction import (
    iter_complete_info_files,
    PredictionData,
    relative_data_file,
)
from cmk.utils.servicename import ServiceName


class PredictionQuerierProtocol(Protocol):
    def query_predicted_metrics(self) -> Sequence[str]: ...

    def query_available_predictions(self, metric: str) -> Iterator[PredictionInfo]: ...

    def query_prediction_data(self, meta: PredictionInfo) -> PredictionData: ...


@dataclass(frozen=True, kw_only=True)
class PredictionQuerier:
    livestatus_connection: SingleSiteConnection
    host_name: HostName
    service_name: ServiceName

    def query_available_predictions(self, metric: str) -> Iterator[PredictionInfo]:
        yield from (
            PredictionInfo.model_validate_json(self._query_prediction_file_content(info_file))
            for info_file in iter_complete_info_files(metric, self._prediction_files)
        )

    def query_predicted_metrics(self) -> Sequence[str]:
        return sorted(
            {
                prediction_file.parts[0]
                for prediction_file in self._prediction_files
                if prediction_file.parts
            }
        )

    def query_prediction_data(self, meta: PredictionInfo) -> PredictionData:
        rel_filename = relative_data_file(meta)
        return PredictionData.model_validate_json(self._query_prediction_file_content(rel_filename))

    def _service_filter(self) -> And:
        return And(
            Services.host_name == LqSafe(self.host_name),
            Services.description == LqSafe(self.service_name),
        )

    @cached_property
    def _prediction_files(self) -> Sequence[Path]:
        query = Query(
            [Services.prediction_files],
            self._service_filter(),
        )
        return [
            Path(prediction_file)
            for prediction_file in self.livestatus_connection.query_row(query)[0]
        ]

    def _query_prediction_file_content(self, relative_file_path: Path) -> bytes:
        query = Query(
            [Services.prediction_file.dynamic("file", str(relative_file_path))],
            self._service_filter(),
        )
        return b"\n".join(self.livestatus_connection.query_row(query))
