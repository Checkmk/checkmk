#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from cmk.agent_based.v1 import Metric, Result, State
from cmk.agent_based.v1.type_defs import StringTable
from cmk.plugins.aws.agent_based.aws_reservation_utilization import (
    check_aws_reservation_utilization,
    parse_aws_reservation_utilization,
    ReservationUtilization,
    UtilizationParams,
)


def example_agent_output() -> StringTable:
    return [
        [
            '[{"TimePeriod":',
            '{"Start":',
            '"2024-02-10",',
            '"End":',
            '"2024-02-11"},',
            '"Total":',
            '{"UtilizationPercentage":',
            '"100",',
            '"UtilizationPercentageInUnits":',
            '"100",',
            '"PurchasedHours":',
            '"72",',
            '"PurchasedUnits":',
            '"576",',
            '"TotalActualHours":',
            '"72",',
            '"TotalActualUnits":',
            '"576",',
            '"UnusedHours":',
            '"0",',
            '"UnusedUnits":',
            '"0",',
            '"OnDemandCostOfRIHoursUsed":',
            '"12.4416",',
            '"NetRISavings":',
            '"4.6008",',
            '"TotalPotentialRISavings":',
            '"4.6008",',
            '"AmortizedUpfrontFee":',
            '"0",',
            '"AmortizedRecurringFee":',
            '"7.8408",',
            '"TotalAmortizedFee":',
            '"7.8408",',
            '"RICostForUnusedHours":',
            '"0",',
            '"RealizedSavings":',
            '"4.6008",',
            '"UnrealizedSavings":',
            '"0"}},',
            '{"TimePeriod":',
            '{"Start":',
            '"2024-02-11",',
            '"End":',
            '"2024-02-12"},',
            '"Total":',
            '{"UtilizationPercentage":',
            '"50",',
            '"UtilizationPercentageInUnits":',
            '"50",',
            '"PurchasedHours":',
            '"12",',
            '"PurchasedUnits":',
            '"12",',
            '"TotalActualHours":',
            '"6",',
            '"TotalActualUnits":',
            '"6",',
            '"UnusedHours":',
            '"6",',
            '"UnusedUnits":',
            '"6",',
            '"OnDemandCostOfRIHoursUsed":',
            '"12.4416",',
            '"NetRISavings":',
            '"4.6008",',
            '"TotalPotentialRISavings":',
            '"4.6008",',
            '"AmortizedUpfrontFee":',
            '"0",',
            '"AmortizedRecurringFee":',
            '"7.8408",',
            '"TotalAmortizedFee":',
            '"7.8408",',
            '"RICostForUnusedHours":',
            '"0",',
            '"RealizedSavings":',
            '"4.6008",',
            '"UnrealizedSavings":',
            '"0"}}]',
        ]
    ]


def test_aws_ebs_parsing() -> None:
    parsed = parse_aws_reservation_utilization(example_agent_output())
    assert parsed == {
        "2024-02-10": ReservationUtilization(
            UtilizationPercentage=100.0, PurchasedHours=72.0, TotalActualHours=72.0
        ),
        "2024-02-11": ReservationUtilization(
            UtilizationPercentage=50.0, PurchasedHours=12.0, TotalActualHours=6.0
        ),
    }


def test_check_aws_reservation_utilization() -> None:
    parsed = parse_aws_reservation_utilization(example_agent_output())
    params = UtilizationParams(levels_utilization_percent=None)

    results = list(check_aws_reservation_utilization(params, parsed))

    assert results == [
        Result(state=State.OK, summary="(2024-02-11) Total Reservation Utilization: 50.00%"),
        Metric("aws_total_reservation_utilization", 50.0),
        Result(
            state=State.OK,
            summary="Reserved Hours: 12",
        ),
        Result(
            state=State.OK,
            summary="Actual Hours: 6",
        ),
    ]


def test_check_aws_reservation_utilization_with_param() -> None:
    parsed = parse_aws_reservation_utilization(example_agent_output())
    params = UtilizationParams(levels_utilization_percent=(95.0, 90.0))

    results = list(check_aws_reservation_utilization(params, parsed))

    expected_summary = (
        "(2024-02-11) Total Reservation Utilization: 50.00% (warn/crit below 95.00%/90.00%)"
    )
    assert Result(state=State.CRIT, summary=expected_summary) in results
