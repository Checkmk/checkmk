#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import time

import cmk.utils.render
from cmk.utils.structured_data import SDValue

from cmk.gui.htmllib.generator import HTMLWriter
from cmk.gui.i18n import _
from cmk.gui.ifaceoper import interface_oper_state_name, interface_port_types
from cmk.gui.utils.escaping import escape_text

from .registry import InvPaintFunction, InvPaintFunctions, PaintResult


def register(inv_paint_funtions: InvPaintFunctions) -> None:
    for paint_function in [
        inv_paint_generic,
        inv_paint_hz,
        inv_paint_bytes,
        inv_paint_size,
        inv_paint_bytes_rounded,
        inv_paint_number,
        inv_paint_count,
        inv_paint_nic_speed,
        inv_paint_if_oper_status,
        inv_paint_if_admin_status,
        inv_paint_if_port_type,
        inv_paint_if_available,
        inv_paint_mssql_is_clustered,
        inv_paint_mssql_node_names,
        inv_paint_ipv4_network,
        inv_paint_ip_address_type,
        inv_paint_route_type,
        inv_paint_volt,
        inv_paint_date,
        inv_paint_date_and_time,
        inv_paint_age,
        inv_paint_bool,
        inv_paint_timestamp_as_age,
        inv_paint_timestamp_as_age_days,
        inv_paint_csv_labels,
        inv_paint_container_ready,
        inv_paint_service_status,
    ]:
        # Do no overwrite paint functions from plugins
        if paint_function.__name__ not in inv_paint_funtions:
            inv_paint_funtions.register(
                InvPaintFunction(name=paint_function.__name__, func=paint_function)
            )


def inv_paint_generic(value: SDValue) -> PaintResult:
    if value == "" or value is None:
        return "", ""
    if isinstance(value, float):
        return "number", "%.2f" % value
    if isinstance(value, int):
        return "number", "%d" % value
    if isinstance(value, bool):
        return "", _("Yes") if value else _("No")
    return "", escape_text("%s" % value)


def inv_paint_hz(value: SDValue) -> PaintResult:
    if value == "" or value is None:
        return "", ""
    if isinstance(value, str):
        return "number", value
    if not isinstance(value, int | float):
        raise ValueError(value)
    return "number", cmk.utils.render.fmt_number_with_precision(value, drop_zeroes=False, unit="Hz")


def inv_paint_bytes(value: SDValue) -> PaintResult:
    if value == "" or value is None:
        return "", ""
    if isinstance(value, str):
        return "number", value
    if not isinstance(value, int | float):
        raise ValueError(value)
    if value == 0:
        return "number", "0"
    return "number", cmk.utils.render.fmt_bytes(value, precision=0)


def inv_paint_size(value: SDValue) -> PaintResult:
    if value == "" or value is None:
        return "", ""
    if isinstance(value, str):
        return "number", value
    if not isinstance(value, int | float):
        raise ValueError(value)
    return "number", cmk.utils.render.fmt_bytes(value)


def inv_paint_bytes_rounded(value: SDValue) -> PaintResult:
    if value == "" or value is None:
        return "", ""
    if isinstance(value, str):
        return "number", value
    if not isinstance(value, int | float):
        raise ValueError(value)
    if value == 0:
        return "number", "0"
    return "number", cmk.utils.render.fmt_bytes(value)


def inv_paint_number(value: SDValue) -> PaintResult:
    if value == "" or value is None:
        return "", ""
    if not isinstance(value, str | int | float):
        raise ValueError(value)
    return "number", str(value)


def inv_paint_count(value: SDValue) -> PaintResult:
    # Similar to paint_number, but is allowed to
    # abbreviate things if numbers are very large
    # (though it doesn't do so yet)
    if value == "" or value is None:
        return "", ""
    if not isinstance(value, str | int | float):
        raise ValueError(value)
    return "number", str(value)


def inv_paint_nic_speed(value: SDValue) -> PaintResult:
    if value == "" or value is None:
        return "", ""
    if not isinstance(value, str | int):
        raise ValueError(value)
    return "number", cmk.utils.render.fmt_nic_speed(value)


def inv_paint_if_oper_status(value: SDValue) -> PaintResult:
    if value == "" or value is None:
        return "", ""
    if not isinstance(value, int):
        raise ValueError(value)
    if value == 1:
        css_class = "if_state_up"
    elif value == 2:
        css_class = "if_state_down"
    else:
        css_class = "if_state_other"

    return (
        "if_state " + css_class,
        interface_oper_state_name(value, "%s" % value).replace(" ", "&nbsp;"),
    )


def inv_paint_if_admin_status(value: SDValue) -> PaintResult:
    # admin status can only be 1 or 2, matches oper status :-)
    if value == "" or value is None:
        return "", ""
    return inv_paint_if_oper_status(value)


def inv_paint_if_port_type(value: SDValue) -> PaintResult:
    if value == "" or value is None:
        return "", ""
    if not isinstance(value, int):
        raise ValueError(value)
    type_name = interface_port_types().get(value, _("unknown"))
    return "", "%d - %s" % (value, type_name)


def inv_paint_if_available(value: SDValue) -> PaintResult:
    if value == "" or value is None:
        return "", ""
    if not isinstance(value, bool):
        raise ValueError(value)
    return (
        "if_state " + (value and "if_available" or "if_not_available"),
        (value and _("free") or _("used")),
    )


def inv_paint_mssql_is_clustered(value: SDValue) -> PaintResult:
    if value == "" or value is None:
        return "", ""
    if not isinstance(value, bool):
        raise ValueError(value)
    return (
        "mssql_" + (value and "is_clustered" or "is_not_clustered"),
        (value and _("is clustered") or _("is not clustered")),
    )


def inv_paint_mssql_node_names(value: SDValue) -> PaintResult:
    if value == "" or value is None:
        return "", ""
    if not isinstance(value, str):
        raise ValueError(value)
    return "", value


def inv_paint_ipv4_network(value: SDValue) -> PaintResult:
    if value == "" or value is None:
        return "", ""
    if not isinstance(value, str):
        raise ValueError(value)
    if value == "0.0.0.0/0":
        return "", _("Default")
    return "", value


def inv_paint_ip_address_type(value: SDValue) -> PaintResult:
    if value == "" or value is None:
        return "", ""
    if not isinstance(value, str):
        raise ValueError(value)
    if value == "ipv4":
        return "", _("IPv4")
    if value == "ipv6":
        return "", _("IPv6")
    return "", value


def inv_paint_route_type(value: SDValue) -> PaintResult:
    if value == "" or value is None:
        return "", ""
    if not isinstance(value, str):
        raise ValueError(value)
    if value == "local":
        return "", _("Local route")
    return "", _("Gateway route")


def inv_paint_volt(value: SDValue) -> PaintResult:
    if value == "" or value is None:
        return "", ""
    if isinstance(value, str):
        return "number", value
    if not isinstance(value, int | float):
        raise ValueError(value)
    return "number", "%.1f V" % value


def inv_paint_date(value: SDValue) -> PaintResult:
    if value == "" or value is None:
        return "", ""
    if isinstance(value, str):
        return "number", value
    if not isinstance(value, int | float):
        raise ValueError(value)
    date_painted = time.strftime("%Y-%m-%d", time.localtime(value))
    return "number", "%s" % date_painted


def inv_paint_date_and_time(value: SDValue) -> PaintResult:
    if value == "" or value is None:
        return "", ""
    if isinstance(value, str):
        return "number", value
    if not isinstance(value, int | float):
        raise ValueError(value)
    date_painted = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(value))
    return "number", "%s" % date_painted


def inv_paint_age(value: SDValue) -> PaintResult:
    if value == "" or value is None:
        return "", ""
    if isinstance(value, str):
        return "number", value
    if not isinstance(value, int | float):
        raise ValueError(value)
    return "number", cmk.utils.render.approx_age(value)


def inv_paint_bool(value: SDValue) -> PaintResult:
    if value == "" or value is None:
        return "", ""
    if not isinstance(value, bool):
        raise ValueError(value)
    return "", (_("Yes") if value else _("No"))


def inv_paint_timestamp_as_age(value: SDValue) -> PaintResult:
    if value == "" or value is None:
        return "", ""
    if isinstance(value, str):
        return "number", value
    if not isinstance(value, int | float):
        raise ValueError(value)
    return inv_paint_age(time.time() - value)


def inv_paint_timestamp_as_age_days(value: SDValue) -> PaintResult:
    if value == "" or value is None:
        return "", ""
    if isinstance(value, str):
        return "number", value
    if not isinstance(value, int | float):
        raise ValueError(value)

    def round_to_day(ts):
        broken = time.localtime(ts)
        return int(
            time.mktime(
                (
                    broken.tm_year,
                    broken.tm_mon,
                    broken.tm_mday,
                    0,
                    0,
                    0,
                    broken.tm_wday,
                    broken.tm_yday,
                    broken.tm_isdst,
                )
            )
        )

    now_day = round_to_day(time.time())
    change_day = round_to_day(value)
    age_days = int((now_day - change_day) / 86400.0)

    css_class = "number"
    if age_days == 0:
        return css_class, _("today")
    if age_days == 1:
        return css_class, _("yesterday")
    return css_class, "%d %s" % (int(age_days), _("days ago"))


def inv_paint_csv_labels(value: SDValue) -> PaintResult:
    if value == "" or value is None:
        return "", ""
    if not isinstance(value, str):
        raise ValueError(value)
    return "labels", HTMLWriter.render_br().join(value.split(","))


def inv_paint_container_ready(value: SDValue) -> PaintResult:
    if value == "" or value is None:
        return "", ""
    if not isinstance(value, str):
        raise ValueError(value)
    if value == "yes":
        css_class = "if_state_up"
    elif value == "no":
        css_class = "if_state_down"
    else:
        css_class = "if_state_other"
    return "if_state " + css_class, value


def inv_paint_service_status(value: SDValue) -> PaintResult:
    if value == "" or value is None:
        return "", ""
    if not isinstance(value, str):
        raise ValueError(value)
    if value == "running":
        css_class = "if_state_up"
    elif value == "stopped":
        css_class = "if_state_down"
    else:
        css_class = "if_not_available"
    return "if_state " + css_class, value
