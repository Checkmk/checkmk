#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import List
import time

from cmk.gui.exceptions import MKUserError
from cmk.gui.i18n import _
from cmk.gui.valuespec import Timerange
from cmk.gui.plugins.dashboard import ABCDataGenerator


class BarChartDataGenerator(ABCDataGenerator):
    """Contains code to generate the data for a barchart dashlet
       The dashlet logic/visualization is specified in ABCFigureDashlet
    """
    def generate_response_data(self, properties, context, settings):
        data_rows = self._get_data(properties, context)
        bar_elements = self._create_bar_elements(data_rows, properties, context)
        response = self._create_bar_chart_config(bar_elements, properties, context, settings)

        mode_properties = properties["render_mode"][1]
        per_string = _("hour") if mode_properties["time_resolution"] == "h" else _("day")
        return {
            "plot_definitions": [{
                "plot_type": "bar",
                "css_classes": ["bar_chart"],
                "id": "id_bar",
                "label": _("per %s") % per_string,
                "use_tags": ["bar"]
            }],
            "data": response["elements"],
        }

    def _get_data(self, properties, context):
        raise NotImplementedError()

    def _create_bar_chart_config(self, bar_elements, properties, context, settings):
        return {"elements": bar_elements}

    def _int_time_range_from_rangespec(self, rangespec):
        time_range, _range_title = Timerange().compute_range(rangespec)
        return [int(t) for t in time_range]

    def _timestep_from_resolution(self, resolution):
        if resolution == "h":
            return 60 * 60
        if resolution == "d":
            return 60 * 60 * 24
        raise MKUserError("resolution", _("Invalid time resolution key \"%s\" given" % resolution))

    def _create_bar_elements(self, data_rows, properties, context):
        """Return a list of dicts specified as follows:
        bar_elements = [{
            "timestamp": 1234567891,
            "ending_timestamp": 1234567892,
            "value": 15,
            "tag": "bar",
            "tooltip": "time frame information text",
            "url": "https://url/to/specific/data/view",
            <optional_detail>
        }, ... ]"""
        bar_elements = self._initialize_bar_elements(properties)
        return self._populate_bar_elements(data_rows, bar_elements, properties, context)

    def _initialize_bar_elements(self, properties):
        """Return a list of dicts where each dict represents a time frame with
        respect to the given time range and resolution. All non-time values are
        set to an initial value (0 / "" / [])."""
        mode_properties = properties["render_mode"][1]
        time_range = self._int_time_range_from_rangespec(mode_properties["time_range"])
        basic_timestep = self._timestep_from_resolution(mode_properties["time_resolution"])
        timestamps = self._forge_timestamps(time_range, basic_timestep)
        bar_elements = []
        for i, timestamp in enumerate(timestamps):
            if i == len(timestamps) - 1:
                ending_timestamp = time_range[1]
            else:
                ending_timestamp = timestamps[i + 1] - 1
            bar_elements.append({
                "timestamp": timestamp,
                "ending_timestamp": ending_timestamp,
                "value": 0,
                "tag": "bar",
            })
        return bar_elements

    def _forge_timestamps(self, time_range, timestep):
        """Forge timestamps within the given time range where the first and last
        timestep may be smaller than the given timestep. Yielding 'inner'
        timestamps rounded to the hour."""
        timestamps = [time_range[0]]
        # Adding 3600 (1h) because timestamp 0 corresponds to
        # 1970-01-01 01:00 (not 00:00)
        t = time_range[0] + timestep - (time_range[0] + 3600) % timestep
        while t < time_range[1]:
            if timestep == 86400:
                t -= time.localtime(t).tm_hour * 3600
            timestamps.append(t)
            t += timestep
        return timestamps

    def _populate_bar_elements(self, data_rows, bar_elements, properties, context):
        data_rows.sort(key=lambda x: x[4])
        row_offset = 0
        for time_frame in bar_elements:
            for row in data_rows[row_offset:]:
                if row[4] >= time_frame["ending_timestamp"]:
                    break
                row_offset += 1
                time_frame["value"] += 1
            tooltip, url = self._forge_tooltip_and_url(time_frame, properties, context)
            self._update_tooltip_and_url(time_frame, tooltip, url)
        return bar_elements

    def _forge_tooltip_and_url(self, time_frame, properties, context):
        return None, None

    def _update_tooltip_and_url(self, time_frame, tooltip, url):
        if tooltip:
            time_frame["tooltip"] = tooltip
        if url:
            time_frame["url"] = url


class BarBarChartDataGenerator(BarChartDataGenerator):
    def _create_barbar_chart_config(self, bar_chart_config, properties, context):
        bar_elements = bar_chart_config["elements"]

        grouping_indices = self._get_grouping_indices(bar_elements, properties)
        barbar_elements = []
        for start, end in grouping_indices:
            barbar_elements.append({
                "timestamp": bar_elements[start]["timestamp"],
                "ending_timestamp": bar_elements[end]["ending_timestamp"],
                "value": sum([e["value"] for e in bar_elements[start:end + 1]]),
                "tag": "barbar",
            })
        for time_frame in barbar_elements:
            tooltip, url = self._forge_tooltip_and_url(time_frame, properties, context)
            self._update_tooltip_and_url(time_frame, tooltip, url)

        bar_chart_config["elements"].extend(barbar_elements)
        return bar_chart_config

    def _get_grouping_indices(self, bar_elements, properties):
        mode_properties = properties["render_mode"][1]
        timestep = self._timestep_from_resolution(mode_properties["time_resolution"])
        start_new_group = self._get_start_new_group_function(timestep)
        grouping_indices = []
        tmp_start_index = 0
        for i, elem in enumerate(bar_elements):
            if i > 0 and start_new_group(elem["timestamp"]):
                grouping_indices.append([tmp_start_index, i - 1])
                tmp_start_index = i
        if not grouping_indices or grouping_indices[-1][0] != tmp_start_index:
            grouping_indices.append([tmp_start_index, len(bar_elements) - 1])
        return grouping_indices

    def _get_start_new_group_function(self, timestep):
        if timestep == 3600:
            return lambda x: time.localtime(x).tm_hour % 12 == 0
        if timestep == 86400:
            return lambda x: time.localtime(x).tm_wday % 7 == 0
        raise MKUserError("timestep", _("Invalid timestep \"%d\" given" % timestep))

    def generate_response_data(self, properties, context, settings):
        bar_chart_config = super(BarBarChartDataGenerator,
                                 self).generate_response_data(properties, context, settings)
        # Add barbar elements
        response = self._create_barbar_chart_config(bar_chart_config, properties, context)

        mode_properties = properties["render_mode"][1]
        if mode_properties["time_resolution"] == "h":
            per_string = {"bar": "hour", "barbar": "12 hours"}
        else:
            per_string = {"bar": "day", "barbar": "week"}
        new_response = {
            "plot_definitions": [{
                "plot_type": "bar",
                "css_classes": ["bar_chart", "barbar_chart"],
                "id": "id_barbar",
                "label": _("per %s") % per_string["barbar"],
                "use_tags": ["barbar"]
            }, {
                "plot_type": "bar",
                "css_classes": ["bar_chart"],
                "id": "id_bar",
                "label": _("per %s") % per_string["bar"],
                "use_tags": ["bar"]
            }],
            "data": response["elements"]
        }
        return new_response
