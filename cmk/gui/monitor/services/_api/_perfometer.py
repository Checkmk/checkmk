#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Sequence
from typing import Self

from cmk.gui.config import active_config
from cmk.gui.graphing import (
    get_first_matching_perfometer,
    get_temperature_unit,
    metrics_from_api,
    parse_perf_data,
    perfometers_from_api,
    translate_metrics,
)
from cmk.gui.log import logger
from cmk.gui.logged_in import user
from cmk.gui.openapi.framework.model import api_field, api_model
from cmk.gui.view_utils import get_themed_perfometer_bg_color

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
    def from_perf_data(cls, perf_data: str, check_command: str) -> Self | None:
        """Build the Perf-O-Meter a service's performance data resolves to, if any."""
        try:
            return cls._from_perf_data(perf_data, check_command)
        except Exception:
            logger.exception("error rendering perfometer")
            if active_config.debug:
                raise
            return None

    @classmethod
    def _from_perf_data(cls, perf_data: str, check_command: str) -> Self | None:
        if not (perf_data_string := perf_data.strip()):
            return None

        temperature_unit = get_temperature_unit(user, active_config.default_temperature_unit)
        parsed_perf_data, parsed_check_command = parse_perf_data(
            perf_data_string, check_command, debug=active_config.debug
        )
        if not parsed_perf_data:
            return None

        if not (
            renderer := get_first_matching_perfometer(
                translate_metrics(
                    parsed_perf_data,
                    parsed_check_command,
                    metrics_from_api,
                    temperature_unit=temperature_unit,
                ),
                metrics_from_api,
                perfometers_from_api,
            )
        ):
            return None

        if not (stack := renderer.get_stack(temperature_unit)):
            return None

        return cls._from_segments(stack[0], label=renderer.get_label(temperature_unit))

    @classmethod
    def _from_segments(
        cls, segments: Sequence[tuple[int | float, str]], *, label: str
    ) -> Self | None:
        background_color = get_themed_perfometer_bg_color()
        filled = [(share, color) for share, color in segments if color != background_color]
        if not filled:
            return None

        return cls(
            value=sum(share for share, _color in filled),
            value_range=ServicePerfometerRange(min=_EMPTY_AT, max=_FULL_AT),
            formatted=label,
            color=filled[0][1],
        )
