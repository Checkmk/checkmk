#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from livestatus import LocalConnection

from cmk.utils.hostaddress import HostName
from cmk.utils.livestatus_helpers.testing import MockLiveStatusConnection, SiteName
from cmk.utils.metrics import MetricName
from cmk.utils.prediction import (
    DataStat,
    PredictionData,
    PredictionInfo,
    PredictionParameters,
    Timegroup,
)
from cmk.utils.prediction._query import PredictionQuerier
from cmk.utils.servicename import ServiceName


class TestPredictionQuerier:
    def test_query_available_predictions(self, mock_livestatus: MockLiveStatusConnection) -> None:
        querier = self._prediction_querier()
        expected_prediction_info = PredictionInfo(
            name=Timegroup("everyday"),
            time=123,
            range=(0, 200),
            dsname=str(querier.metric_name),
            params=PredictionParameters(
                period="day",
                horizon=20,
            ),
        )
        mock_livestatus.add_table(
            "services",
            [
                {
                    "host_name": str(querier.host_name),
                    "description": str(querier.service_name),
                    "prediction_files": [
                        f"{querier.metric_name}/everyday.info",
                        f"{querier.metric_name}/everyday",
                        f"{querier.metric_name}/strange.info",
                        "other_metric/everyday.info",
                        "other_metric/everyday",
                    ],
                    f"prediction_file:file:{querier.metric_name}/everyday.info": expected_prediction_info.json().encode(),
                }
            ],
            site=SiteName("local"),
        )
        mock_livestatus.expect_query(
            "GET services\n"
            f"Columns: prediction_files\n"
            f"Filter: host_name = {querier.host_name}\n"
            f"Filter: description = {querier.service_name}\n"
            "ColumnHeaders: off"
        )
        mock_livestatus.expect_query(
            "GET services\n"
            f"Columns: prediction_file:file:{querier.metric_name}/everyday.info\n"
            f"Filter: host_name = {querier.host_name}\n"
            f"Filter: description = {querier.service_name}\n"
            "ColumnHeaders: off"
        )
        assert list(querier.query_available_predictions()) == [expected_prediction_info]

    def test_query_prediction_data(self, mock_livestatus: MockLiveStatusConnection) -> None:
        querier = self._prediction_querier()
        expected_prediction_data = PredictionData(
            points=[
                DataStat(
                    average=1,
                    min_=0,
                    max_=1,
                    stdev=0.5,
                ),
                None,
            ],
            data_twindow=[1],
            step=2,
        )
        mock_livestatus.add_table(
            "services",
            [
                {
                    "host_name": str(querier.host_name),
                    "description": str(querier.service_name),
                    f"prediction_file:file:{querier.metric_name}/everyday": expected_prediction_data.json().encode(),
                }
            ],
            site=SiteName("local"),
        )
        mock_livestatus.expect_query(
            "GET services\n"
            f"Columns: prediction_file:file:{querier.metric_name}/everyday\n"
            f"Filter: host_name = {querier.host_name}\n"
            f"Filter: description = {querier.service_name}\n"
            "ColumnHeaders: off"
        )
        assert querier.query_prediction_data(Timegroup("everyday")) == expected_prediction_data

    @staticmethod
    def _prediction_querier() -> PredictionQuerier:
        return PredictionQuerier(
            livestatus_connection=LocalConnection(),
            host_name=HostName("host"),
            service_name=ServiceName("service"),
            metric_name=MetricName("metric"),
        )
