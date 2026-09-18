#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Sequence
from typing import Self

from cmk.gui.config import active_config
from cmk.gui.graphing import (
    drawn_segments,
    DrawnSegment,
    evaluated_perfometer,
    get_temperature_unit,
    perfometer_label,
    perfometers_from_api,
    registered_metrics,
    registered_translations,
)
from cmk.gui.log import logger
from cmk.gui.logged_in import user
from cmk.gui.openapi.framework.model import api_field, api_model


@api_model
class ServicePerfometerSegment:
    """One run of a bar, drawn from the bar's left edge in the order the runs are listed."""

    share: float = api_field(
        description="Share of the bar's width this run covers, in percent", example=42.0
    )
    color: str | None = api_field(
        description="Hex color of the run; null where the bar is left unfilled", example="#ff0000"
    )


@api_model
class ServicePerfometer:
    """Perf-O-Meter of a service.

    The graphing layer projects a service's performance data onto one bar, or onto two stacked
    ones, each drawn as a sequence of colored runs and the unfilled rest. A bidirectional
    Perf-O-Meter is a single bar whose two halves grow outwards from its centre.
    """

    bars: list[list[ServicePerfometerSegment]] = api_field(
        description=(
            "Bars to draw, the upper one first. Each bar is the sequence of runs it is drawn "
            "from, and their shares add up to the full width."
        ),
        example=[[{"share": 42.0, "color": "#ff0000"}, {"share": 58.0, "color": None}]],
    )
    formatted: str = api_field(description="Label rendered on top of the bars", example="42%")

    @classmethod
    def from_perf_data(
        cls, perf_data: str, check_command: str, *, host_name: str, service_name: str
    ) -> Self | None:
        """Build the Perf-O-Meter a service's performance data resolves to, if any."""
        try:
            return cls._from_perf_data(
                perf_data, check_command, host_name=host_name, service_name=service_name
            )
        except Exception:
            logger.exception("error rendering perfometer")
            if active_config.debug:
                raise
            return None

    @classmethod
    def _from_perf_data(
        cls, perf_data: str, check_command: str, *, host_name: str, service_name: str
    ) -> Self | None:
        if (
            evaluated := evaluated_perfometer(
                perf_data,
                check_command,
                host_name=host_name,
                service_name=service_name,
                registered_perfometers=perfometers_from_api,
                registered_metrics=registered_metrics(),
                registered_translations=registered_translations(),
                debug=active_config.debug,
            )
        ) is None:
            return None

        return cls._from_bars(
            drawn_segments(evaluated),
            label=perfometer_label(
                evaluated,
                get_temperature_unit(user, active_config.default_temperature_unit),
            ),
        )

    @classmethod
    def _from_bars(cls, bars: Sequence[Sequence[DrawnSegment]], *, label: str) -> Self | None:
        if not any(segment.color is not None for bar in bars for segment in bar):
            return None

        return cls(
            bars=[
                [
                    ServicePerfometerSegment(share=segment.share, color=segment.color)
                    for segment in bar
                ]
                for bar in bars
            ],
            formatted=label,
        )
