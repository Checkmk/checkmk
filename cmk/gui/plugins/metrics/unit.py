#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import cmk.utils.render

from cmk.gui.i18n import _

from cmk.gui.plugins.metrics import (
    unit_info,)

# TODO Graphingsystem:
# - Default-Template: Wenn im Graph kein "range" angegeben ist, aber
# in der Unit eine "range"-Angabe ist, dann soll diese genommen werden.
# Und dann sämtliche Schablonen, die nur wegen Range
# 0..100 da sind, wieder durch generic ersetzen.

# Metric definitions for Checkmk's checks

#   .--Units---------------------------------------------------------------.
#   |                        _   _       _ _                               |
#   |                       | | | |_ __ (_) |_ ___                         |
#   |                       | | | | '_ \| | __/ __|                        |
#   |                       | |_| | | | | | |_\__ \                        |
#   |                        \___/|_| |_|_|\__|___/                        |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |  Definition of units of measurement.                                 |
#   '----------------------------------------------------------------------'
# Optional attributes of units:
#
#   stepping: FIXME: Describe this
#
#   graph_unit: Compute a common unit for the whole graph. This is an optional
#               feature to solve the problem that some unit names are too long
#               to be shown on the left of the screen together with the values.
#               For fixing this the "graph unit" is available which is displayed
#               on the top left of the graph and is used for the whole graph. So
#               once a "graph unit" is computed, it does not need to be shown
#               beside each label.
#               This has to be set to a function which recevies a list of values,
#               then computes the optimal unit for the given values and then
#               returns a two element tuple. The first element is the "graph unit"
#               and the second is a list containing all of the values rendered with
#               the graph unit.

# TODO: Move fundamental units like "" to main file.

unit_info[""] = {
    "title": "",
    "description": _("Floating point number"),
    "symbol": "",
    "render": lambda v: cmk.utils.render.scientific(v, 2),
}

unit_info["count"] = {
    "title": _("Count"),
    "symbol": "",
    "render": lambda v: cmk.utils.render.fmt_number_with_precision(v, drop_zeroes=True),
    "stepping": "integer",  # for vertical graph labels
}

# value ranges from 0.0 ... 100.0
unit_info["%"] = {
    "title": _("%"),
    "description": _("Percentage (0...100)"),
    "symbol": _("%"),
    "render": lambda v: cmk.utils.render.percent(v, scientific_notation=True),
}

unit_info["s"] = {
    "title": _("sec"),
    "description": _("Timespan or Duration in seconds"),
    "symbol": _("s"),
    "render": cmk.utils.render.approx_age,
    "stepping": "time",  # for vertical graph labels
}

unit_info["1/s"] = {
    "title": _("per second"),
    "description": _("Frequency (displayed in events/s)"),
    "symbol": _("/s"),
    "render": lambda v: "%s%s" % (cmk.utils.render.drop_dotzero(v), _("/s")),
}

unit_info["hz"] = {
    "title": _("Hz"),
    "symbol": _("Hz"),
    "description": _("Frequency (displayed in Hz)"),
    "render": lambda v: cmk.utils.render.physical_precision(v, 3, _("Hz")),
}

unit_info["bytes"] = {
    "title": _("Bytes"),
    "symbol": _("B"),
    "render": cmk.utils.render.fmt_bytes,
    "stepping": "binary",  # for vertical graph labels
}

unit_info["bytes/s"] = {
    "title": _("Bytes per second"),
    "symbol": _("B/s"),
    "render": lambda v: cmk.utils.render.fmt_bytes(v) + _("/s"),
    "stepping": "binary",  # for vertical graph labels
}


def physical_precision_list(values, precision, unit_symbol):
    if not values:
        reference = 0
    else:
        reference = min([abs(v) for v in values])

    scale_symbol, places_after_comma, scale_factor = cmk.utils.render.calculate_physical_precision(
        reference, precision)

    scaled_values = []
    for value in values:
        scaled_value = float(value) / scale_factor
        scaled_values.append(("%%.%df" % places_after_comma) % scaled_value)

    return "%s%s" % (scale_symbol, unit_symbol), scaled_values


unit_info["bits/s"] = {
    "title": _("Bits per second"),
    "symbol": _("bits/s"),
    "render": lambda v: cmk.utils.render.physical_precision(v, 3, _("bit/s")),
    "graph_unit": lambda v: physical_precision_list(v, 3, _("bit/s")),
}


def bytes_human_readable_list(values, *args, **kwargs):
    if not values:
        reference = 0
    else:
        reference = min([abs(v) for v in values])

    scale_factor, scale_prefix = cmk.utils.render.scale_factor_prefix(reference, 1024.0)
    precision = kwargs.get("precision", 2)

    scaled_values = ["%.*f" % (precision, float(value) / scale_factor) for value in values]

    unit_txt = kwargs.get("unit", "B")

    return scale_prefix + unit_txt, scaled_values


# Output in bytes/days, value is in bytes/s
unit_info["bytes/d"] = {
    "title": _("Bytes per day"),
    "symbol": _("B/d"),
    "render": lambda v: cmk.utils.render.fmt_bytes(v * 86400.0) + "/d",
    "graph_unit": lambda values: bytes_human_readable_list([v * 86400.0 for v in values],
                                                           unit=_("B/d")),
    "stepping": "binary",  # for vertical graph labels
}

unit_info["c"] = {
    "title": _("Degree Celsius"),
    "symbol": u"°C",
    "render": lambda v: "%s %s" % (cmk.utils.render.drop_dotzero(v), u"°C"),
}

unit_info["a"] = {
    "title": _("Electrical Current (Amperage)"),
    "symbol": _("A"),
    "render": lambda v: cmk.utils.render.physical_precision(v, 3, _("A")),
}

unit_info["v"] = {
    "title": _("Electrical Tension (Voltage)"),
    "symbol": _("V"),
    "render": lambda v: cmk.utils.render.physical_precision(v, 3, _("V")),
}

unit_info["w"] = {
    "title": _("Electrical Power"),
    "symbol": _("W"),
    "render": lambda v: cmk.utils.render.physical_precision(v, 3, _("W")),
}

unit_info["va"] = {
    "title": _("Electrical Apparent Power"),
    "symbol": _("VA"),
    "render": lambda v: cmk.utils.render.physical_precision(v, 3, _("VA")),
}

unit_info["wh"] = {
    "title": _("Electrical Energy"),
    "symbol": _("Wh"),
    "render": lambda v: cmk.utils.render.physical_precision(v, 3, _("Wh")),
}

unit_info["dbm"] = {
    "title": _("Decibel-milliwatts"),
    "symbol": _("dBm"),
    "render": lambda v: "%s %s" % (cmk.utils.render.drop_dotzero(v), _("dBm")),
}

unit_info["dbmv"] = {
    "title": _("Decibel-millivolt"),
    "symbol": _("dBmV"),
    "render": lambda v: "%s %s" % (cmk.utils.render.drop_dotzero(v), _("dBmV")),
}

unit_info["db"] = {
    "title": _("Decibel"),
    "symbol": _("dB"),
    "render": lambda v: cmk.utils.render.physical_precision(v, 3, _("dB")),
}

unit_info["ppm"] = {
    "title": _("ppm"),
    "symbol": _("ppm"),
    "description": _("Parts per Million"),
    "render": lambda v: cmk.utils.render.physical_precision(v, 3, _("ppm")),
}

# 'Percent obscuration per meter'-Obscuration for any atmospheric phenomenon, e.g. smoke, dust, snow
unit_info["%/m"] = {
    "title": _("Percent Per Meter"),
    "symbol": _("%/m"),
    "render": lambda v: cmk.utils.render.percent(v, scientific_notation=True) + _("/m"),
}

unit_info["bar"] = {
    "title": _("Bar"),
    "symbol": _("bar"),
    "render": lambda v: cmk.utils.render.physical_precision(v, 4, _("bar")),
}

unit_info["pa"] = {
    "title": _("Pascal"),
    "symbol": _("Pa"),
    "render": lambda v: cmk.utils.render.physical_precision(v, 3, _("Pa")),
}

unit_info["l/s"] = {
    "title": _("Liters per second"),
    "symbol": _("l/s"),
    "render": lambda v: cmk.utils.render.physical_precision(v, 3, _("l/s")),
}

unit_info["rpm"] = {
    "title": _("Revolutions per minute"),
    "symbol": _("rpm"),
    "render": lambda v: cmk.utils.render.physical_precision(v, 4, _("rpm")),
}

unit_info['bytes/op'] = {
    'title': _('Read size per operation'),
    'symbol': 'bytes/op',
    'color': '#4080c0',
    "render": cmk.utils.render.fmt_bytes,
}

unit_info['EUR'] = {
    "title": _("Euro"),
    "symbol": u"€",
    "render": lambda v: u"%s €" % v,
}

unit_info['RCU'] = {
    "title": _("RCU"),
    "symbol": _("RCU"),
    "description": _("Read Capacity Units"),
    "render": lambda v: cmk.utils.render.fmt_number_with_precision(v, precision=3, unit="RCU"),
}

unit_info['WCU'] = {
    "title": _("WCU"),
    "symbol": _("WCU"),
    "description": _("Write Capacity Units"),
    "render": lambda v: cmk.utils.render.fmt_number_with_precision(v, precision=3, unit="WCU"),
}
