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

_EMPTY_AT = 0.0
_FULL_AT = 100.0


@api_model
class ServicePerfometerRange:
    """Bounds the Perf-O-Meter's value is to be read against."""

    min: float = api_field(description="Value of an entirely empty bar", example=_EMPTY_AT)
    max: float = api_field(description="Value of an entirely filled bar", example=_FULL_AT)


@api_model
class ServicePerfometer:
    """Perf-O-Meter of a service, flattened into a single filled bar.

    The graphing layer projects a service's performance data onto a stack of colored segments;
    what is exposed here is the share of the bar those segments fill, together with the label and
    the leading segment's color.
    """

    value: float = api_field(description="Filled share of the bar", example=42.0)
    value_range: ServicePerfometerRange = api_field(
        description="Bounds the value is to be read against"
    )
    formatted: str = api_field(description="Label rendered on top of the bar", example="42%")
    color: str = api_field(description="Hex color of the filled part", example="#ff0000")

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

        return cls._from_segments(
            drawn_segments(evaluated)[0],
            label=perfometer_label(
                evaluated,
                get_temperature_unit(user, active_config.default_temperature_unit),
            ),
        )

    @classmethod
    def _from_segments(cls, segments: Sequence[DrawnSegment], *, label: str) -> Self | None:
        filled = [
            (segment.share, color) for segment in segments if (color := segment.color) is not None
        ]
        if not filled:
            return None

        return cls(
            value=sum(share for share, _color in filled),
            value_range=ServicePerfometerRange(min=_EMPTY_AT, max=_FULL_AT),
            formatted=label,
            color=filled[0][1],
        )
