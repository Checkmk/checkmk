#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import time

from livestatus import lqencode
import cmk.gui.sites as sites
from cmk.gui.utils.url_encoder import HTTPVariables

from cmk.utils.render import date_and_time
from cmk.gui.exceptions import MKTimeout, MKGeneralException, MKUserError
from cmk.gui.i18n import _
from cmk.gui.globals import html
from cmk.gui.visuals import get_filter_headers
from cmk.gui.valuespec import (
    CascadingDropdown,
    Dictionary,
    DropdownChoice,
    TextUnicode,
    Timerange,
)
from cmk.gui.figures import ABCDataGenerator


class BarChartDataGenerator(ABCDataGenerator):
    """Contains code to generate the data for a barchart dashlet
       The dashlet logic/visualization is specified in ABCFigureDashlet
    """
    @classmethod
    def generate_response_data(cls, properties, context):
        data_rows, _column_headers = cls._get_data(properties, context)
        bar_elements = cls._create_bar_elements(data_rows, properties, context)
        return cls._create_bar_chart_config(bar_elements, properties, context)

    @classmethod
    def _get_data(cls, properties, context, return_column_headers=True):
        raise NotImplementedError()

    @classmethod
    def bar_chart_vs_components(cls):
        # Specifies the properties for this data generator
        return [
            ("time_range", Timerange(
                title=_("Time range"),
                default_value='d0',
            )),
            ("time_resolution",
             DropdownChoice(
                 title=_("Time resolution"),
                 choices=[("h", _("Show per hour")), ("d", _("Show per day"))],
                 default_value="h",
             )),
            ("bar_chart_title",
             CascadingDropdown(
                 title=_("Bar chart title"),
                 orientation="horizontal",
                 choices=[
                     ("show", _("Show default title")),
                     ("hide", _("Hide title")),
                     ("custom", _("Set a custom title"), TextUnicode(default_value="")),
                 ],
                 default_value="show",
             )),
        ]

    @classmethod
    def bar_chart_title(cls, properties, context):
        title_config = properties["bar_chart_title"]
        if title_config == "show":
            return cls.default_bar_chart_title(properties, context)
        if title_config == "hide":
            return ""
        if isinstance(title_config, tuple) and title_config[0] == "custom" and isinstance(
                title_config[1], str):
            return title_config[1]
        raise MKUserError("bar_chart_title",
                          _("Invalid bar chart title config \"%r\" given" % (title_config,)))

    @classmethod
    def default_bar_chart_title(cls, properties, context):
        raise NotImplementedError()

    @classmethod
    def _create_bar_chart_config(cls, bar_elements, properties, context):
        return {"title": cls.bar_chart_title(properties, context), "elements": bar_elements}

    @classmethod
    def _int_time_range_from_rangespec(cls, rangespec):
        time_range, _range_title = Timerange().compute_range(rangespec)
        return [int(t) for t in time_range]

    @classmethod
    def _timestep_from_resolution(cls, resolution):
        if resolution == "h":
            return 60 * 60
        if resolution == "d":
            return 60 * 60 * 24
        raise MKUserError("resolution", _("Invalid time resolution key \"%s\" given" % resolution))

    @classmethod
    def _create_bar_elements(cls, data_rows, properties, context):
        """Return a list of dicts specified as follows:
        bar_elements = [{
            "start_time": 1234567891,
            "end_time": 1234567892,
            "value": 15,
            "tooltip": "time frame information text",
            "url": "https://url/to/specific/data/view",
            <optional_detail>
        }, ... ]"""
        bar_elements = cls._initialize_bar_elements(properties)
        return cls._populate_bar_elements(data_rows, bar_elements, properties, context)

    @classmethod
    def _initialize_bar_elements(cls, properties):
        """Return a list of dicts where each dict represents a time frame with
        respect to the given time range and resolution. All non-time values are
        set to an initial value (0 / "" / [])."""
        time_range = cls._int_time_range_from_rangespec(properties["time_range"])
        basic_timestep = cls._timestep_from_resolution(properties["time_resolution"])
        timestamps = cls._forge_timestamps(time_range, basic_timestep)
        bar_elements = []
        for i, timestamp in enumerate(timestamps):
            if i == len(timestamps) - 1:
                end_time = time_range[1]
            else:
                end_time = timestamps[i + 1] - 1
            bar_elements.append({
                "start_time": timestamp,
                "end_time": end_time,
                "value": 0,
            })
        return bar_elements

    @classmethod
    def _forge_timestamps(cls, time_range, timestep):
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

    @classmethod
    def _populate_bar_elements(cls, data_rows, bar_elements, properties, context):
        data_rows.sort(key=lambda x: x[4])
        row_offset = 0
        for time_frame in bar_elements:
            for row in data_rows[row_offset:]:
                if row[4] >= time_frame["end_time"]:
                    break
                row_offset += 1
                time_frame["value"] += 1
            tooltip, url = cls._forge_tooltip_and_url(time_frame, properties, context)
            cls._update_tooltip_and_url(time_frame, tooltip, url)
        return bar_elements

    @classmethod
    def _forge_tooltip_and_url(cls, time_frame, properties, context):
        return None, None

    @classmethod
    def _update_tooltip_and_url(cls, time_frame, tooltip, url):
        if tooltip:
            time_frame["tooltip"] = tooltip
        if url:
            time_frame["url"] = url


class BarBarChartDataGenerator(BarChartDataGenerator):
    @classmethod
    def _create_barbar_chart_config(cls, bar_chart_config, properties, context):
        bar_elements = bar_chart_config["elements"]

        grouping_indices = cls._get_grouping_indices(bar_elements, properties)
        grouped_elements = []
        for start, end in grouping_indices:
            grouped_elements.append({
                "start_time": bar_elements[start]["start_time"],
                "end_time": bar_elements[end]["end_time"],
                "value": sum([e["value"] for e in bar_elements[start:end + 1]]),
            })
        for time_frame in grouped_elements:
            tooltip, url = cls._forge_tooltip_and_url(time_frame, properties, context)
            cls._update_tooltip_and_url(time_frame, tooltip, url)

        bar_chart_config["grouped_elements"] = grouped_elements
        return bar_chart_config

    @classmethod
    def _get_grouping_indices(cls, bar_elements, properties):
        timestep = cls._timestep_from_resolution(properties["time_resolution"])
        start_new_group = cls._get_start_new_group_function(timestep)
        grouping_indices = []
        tmp_start_index = 0
        for i, elem in enumerate(bar_elements):
            if i > 0 and start_new_group(elem["start_time"]):
                grouping_indices.append([tmp_start_index, i - 1])
                tmp_start_index = i
        if not grouping_indices or grouping_indices[-1][0] != tmp_start_index:
            grouping_indices.append([tmp_start_index, len(bar_elements) - 1])
        return grouping_indices

    @classmethod
    def _get_start_new_group_function(cls, timestep):
        if timestep == 3600:
            return lambda x: time.localtime(x).tm_hour % 12 == 0
        if timestep == 86400:
            return lambda x: time.localtime(x).tm_wday % 7 == 0
        raise MKUserError("timestep", _("Invalid timestep \"%d\" given" % timestep))

    @classmethod
    def generate_response_data(cls, properties, context):
        bar_chart_config = super(BarBarChartDataGenerator,
                                 cls).generate_response_data(properties, context)
        # Add grouped_elements
        response = cls._create_barbar_chart_config(bar_chart_config, properties, context)

        # TODO KO: remove legacy grouped_elements and generate data in "new_response" style

        # This converts the barbar data to the new format
        elements = []
        for element in response["elements"]:
            element["timestamp"] = element["start_time"]
            element["tag"] = "bar"
            elements.append(element)

        for element in response["grouped_elements"]:
            element["timestamp"] = element["start_time"]
            element["tag"] = "barbar"
            elements.append(element)

        if properties["time_resolution"] == "h":
            per_string = {"bar": "hour", "barbar": "12 hours"}
        else:
            per_string = {"bar": "day", "barbar": "week"}

        new_response = {
            "title": response["title"],
            "plot_definitions": [{
                "plot_type": "bar",
                "css_classes": ["bar_chart", "barbar_chart"],
                "color": "blue",
                "id": "id_barbar",
                "label": _("%s per %s") % (response["title"], per_string["barbar"]),
                "use_tags": ["barbar"]
            }, {
                "plot_type": "bar",
                "css_classes": ["bar_chart"],
                "color": "green",
                "id": "id_bar",
                "label": _("%s per %s") % (response["title"], per_string["bar"]),
                "use_tags": ["bar"]
            }],
            "data": elements
        }
        return new_response


class ABCEventBarChartDataGenerator(BarBarChartDataGenerator):
    """ Generates the data for host/service alert/notifications bar charts """
    @classmethod
    def log_type(cls):
        raise NotImplementedError()

    @classmethod
    def log_class(cls):
        raise NotImplementedError()

    @classmethod
    def filter_infos(cls):
        return ["host", "service"]

    @classmethod
    def vs_parameters(cls):
        # Specifies the properties for this data generator
        return Dictionary(
            title=_("Properties"),
            render="form",
            optional_keys=[],
            elements=super(ABCEventBarChartDataGenerator, cls).bar_chart_vs_components() +
            [("log_target",
              DropdownChoice(
                  title=_("Host or service %ss" % cls.log_type()),
                  choices=[("host", _("Show %ss for hosts" % cls.log_type())),
                           ("service", _("Show %ss for services" % cls.log_type()))],
                  default_value="service",
              ))])

    @classmethod
    def _get_data(cls, properties, context, return_column_headers=True):
        time_range = cls._int_time_range_from_rangespec(properties["time_range"])
        # TODO KO: check typing
        c_headers = "ColumnHeaders: on\n" if return_column_headers else ""
        filter_headers, only_sites = get_filter_headers("log", cls.filter_infos(), context)

        query = ("GET log\n"
                 "Columns: log_state host_name service_description log_type log_time\n"
                 "%s"
                 "Filter: class = %d\n"
                 "Filter: log_time >= %f\n"
                 "Filter: log_time <= %f\n"
                 "Filter: log_type ~ %s .*\n"
                 "%s" % (c_headers, cls.log_class(), time_range[0], time_range[1],
                         lqencode(properties["log_target"].upper()), lqencode(filter_headers)))

        try:
            if only_sites:
                sites.live().set_only_sites(only_sites)
            rows = sites.live().query(query)
        except MKTimeout:
            raise
        except Exception:
            raise MKGeneralException(_("The query returned no data."))
        finally:
            sites.live().set_only_sites(None)

        # TODO: hdrs has the funny type Union[str, LivestatusRow], is this really what we want?
        hdrs = rows.pop(0) if return_column_headers else ""
        return rows, hdrs

    @classmethod
    def _forge_tooltip_and_url(cls, time_frame, properties, context):
        time_range = cls._int_time_range_from_rangespec(properties["time_range"])
        end_time = min(time_frame["end_time"], time_range[1])
        from_time_str = date_and_time(time_frame["start_time"])
        to_time_str = date_and_time(end_time)
        # TODO: Can this be simplified by passing a list as argument to html.render_table()?
        tooltip = html.render_table(
            html.render_tr(html.render_td(_("From:")) + html.render_td(from_time_str)) +
            html.render_tr(html.render_td(_("To:")) + html.render_td(to_time_str)) +  #
            html.render_tr(
                html.render_td("%ss:" % properties["log_target"].capitalize()) +
                html.render_td(time_frame["value"])))

        args = []  # type: HTTPVariables
        # Generic filters
        args.append(("filled_in", "filter"))
        args.append(("view_name", "events"))
        args.append(("logtime_from", str(time_frame["start_time"])))
        args.append(("logtime_from_range", "unix"))
        args.append(("logtime_until", str(end_time)))
        args.append(("logtime_until_range", "unix"))
        args.append(("logclass%d" % cls.log_class(), "on"))

        # Target filters
        if properties["log_target"] == "host":
            args.append(("logst_h0", "on"))
            args.append(("logst_h1", "on"))
            args.append(("logst_h2", "on"))
        else:
            args.append(("logst_s0", "on"))
            args.append(("logst_s1", "on"))
            args.append(("logst_s2", "on"))
            args.append(("logst_s3", "on"))

        # Context
        for fil in context.values():
            for k, f in fil.iteritems():
                args.append((k, f))

        return tooltip, html.makeuri_contextless(args, filename="view.py")
