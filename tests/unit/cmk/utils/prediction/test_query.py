#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from livestatus import LocalConnection

from cmk.ccc.hostaddress import HostName

from cmk.utils.livestatus_helpers.testing import MockLiveStatusConnection, SiteName
from cmk.utils.prediction import DataStat, PredictionData
from cmk.utils.prediction._query import PredictionQuerier
from cmk.utils.servicename import ServiceName

from cmk.agent_based.prediction_backend import PredictionInfo, PredictionParameters


class TestPredictionQuerier:
    def test_query_available_predictions(
        self, patch_omd_site: None, mock_livestatus: MockLiveStatusConnection
    ) -> None:
        metric = "metric"
        querier = self._prediction_querier()
        expected_prediction_info = PredictionInfo(
            valid_interval=(0, 200),
            metric=metric,
            direction="upper",
            params=PredictionParameters(
                period="day",
                horizon=20,
                levels=("stdev", (2, 4)),
            ),
        )
        mock_livestatus.add_table(
            "services",
            [
                {
                    "host_name": str(querier.host_name),
                    "description": str(querier.service_name),
                    "prediction_files": [
                        f"{metric}/everyday-lower.info",
                        f"{metric}/everyday-lower",
                        f"{metric}/strange-lower.info",
                        "other_metric/everyday-lower.info",
                        "other_metric/everyday-lower",
                    ],
                    f"prediction_file:file:{metric}/everyday-lower.info": expected_prediction_info.model_dump_json().encode(),
                }
            ],
            site=SiteName("NO_SITE"),
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
            f"Columns: prediction_file:file:{metric}/everyday-lower.info\n"
            f"Filter: host_name = {querier.host_name}\n"
            f"Filter: description = {querier.service_name}\n"
            "ColumnHeaders: off"
        )
        assert list(querier.query_available_predictions(metric)) == [expected_prediction_info]

    def test_query_prediction_data(
        self, patch_omd_site: None, mock_livestatus: MockLiveStatusConnection
    ) -> None:
        metric = "metric"
        querier = self._prediction_querier()
        prediciton_info = PredictionInfo(
            valid_interval=(1234, 5678),
            metric=metric,
            direction="lower",
            params=PredictionParameters(period="day", horizon=0, levels=("absolute", (10, 20))),
        )
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
            start=1,
            step=2,
        )
        mock_livestatus.add_table(
            "services",
            [
                {
                    "host_name": str(querier.host_name),
                    "description": str(querier.service_name),
                    f"prediction_file:file:{metric}/day-1234-lower": expected_prediction_data.model_dump_json().encode(),
                }
            ],
            site=SiteName("NO_SITE"),
        )
        mock_livestatus.expect_query(
            "GET services\n"
            f"Columns: prediction_file:file:{metric}/day-1234-lower\n"
            f"Filter: host_name = {querier.host_name}\n"
            f"Filter: description = {querier.service_name}\n"
            "ColumnHeaders: off"
        )
        assert querier.query_prediction_data(prediciton_info) == expected_prediction_data

    @staticmethod
    def _prediction_querier() -> PredictionQuerier:
        return PredictionQuerier(
            livestatus_connection=LocalConnection(),
            host_name=HostName("host"),
            service_name=ServiceName("service"),
        )
