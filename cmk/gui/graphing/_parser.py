#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from dataclasses import dataclass

import cmk.utils.render as render

from cmk.gui.i18n import _

from cmk.graphing.v1 import metrics

from ._type_defs import UnitInfo


def parse_unit(unit: metrics.Unit | metrics.DecimalUnit | metrics.ScientificUnit) -> UnitInfo:
    match unit:
        case metrics.Unit.BAR:
            return UnitInfo(
                title=_("Pressure"),
                symbol="bar",
                render=lambda v: render.physical_precision(v, 4, _("bar")),
                js_render="v => cmk.number_format.physical_precision(v, 4, 'bar')",
            )
        case metrics.Unit.BIT_IEC:
            return UnitInfo(
                title=_("Bits"),
                symbol="bits",
                render=lambda v: render.fmt_bytes(
                    v, unit_prefix_type=render.IECUnitPrefixes, unit="bits"
                ),
                js_render="v => cmk.number_format.fmt_bytes(v, cmk.number_format.IECUnitPrefixes, 2, 'bits')",
            )
        case metrics.Unit.BITS_IEC_PER_SECOND:
            return UnitInfo(
                title=_("Bits per second"),
                symbol="bits/s",
                render=lambda v: (
                    render.fmt_bytes(v, unit_prefix_type=render.IECUnitPrefixes, unit="bits")
                    + _("/s")
                ),
                js_render="v => cmk.number_format.fmt_bytes(v, cmk.number_format.IECUnitPrefixes, 2, 'bits') + '/s'",
            )
        case metrics.Unit.BIT_SI:
            return UnitInfo(
                title=_("Bits"),
                symbol="bits",
                render=lambda v: render.fmt_bytes(
                    v, unit_prefix_type=render.SIUnitPrefixes, unit="bits"
                ),
                js_render="v => cmk.number_format.fmt_bytes(v, cmk.number_format.SIUnitPrefixes, 2, 'bits')",
            )
        case metrics.Unit.BITS_SI_PER_SECOND:
            return UnitInfo(
                title=_("Bits per second"),
                symbol="bits/s",
                render=lambda v: (
                    render.fmt_bytes(v, unit_prefix_type=render.SIUnitPrefixes, unit="bits")
                    + _("/s")
                ),
                js_render="v => cmk.number_format.fmt_bytes(v, cmk.number_format.SIUnitPrefixes, 2, 'bits') + '/s'",
            )
        case metrics.Unit.BYTE_IEC:
            return UnitInfo(
                title=_("Bytes"),
                symbol="bytes",
                render=lambda v: render.fmt_bytes(v, unit_prefix_type=render.IECUnitPrefixes),
                js_render="v => cmk.number_format.fmt_bytes(v, cmk.number_format.IECUnitPrefixes)",
            )
        case metrics.Unit.BYTES_IEC_PER_DAY:
            # Output in bytes/days, value is in bytes/s
            return UnitInfo(
                title=_("Bytes per day"),
                symbol="bytes/d",
                render=lambda v: (
                    render.fmt_bytes(v * 86400.0, unit_prefix_type=render.IECUnitPrefixes) + _("/d")
                ),
                js_render="v => cmk.number_format.fmt_bytes(v * 86400.0, cmk.number_format.IECUnitPrefixes) + '/d'",
            )
        case metrics.Unit.BYTES_IEC_PER_OPERATION:
            return UnitInfo(
                title=_("Bytes per operation"),
                symbol="bytes/op",
                render=lambda v: (
                    render.fmt_bytes(v, unit_prefix_type=render.IECUnitPrefixes) + _("/op")
                ),
                js_render="v => cmk.number_format.fmt_bytes(v, cmk.number_format.IECUnitPrefixes) + '/op'",
            )
        case metrics.Unit.BYTES_IEC_PER_SECOND:
            return UnitInfo(
                title=_("Bytes per second"),
                symbol="bytes/s",
                render=lambda v: (
                    render.fmt_bytes(v, unit_prefix_type=render.IECUnitPrefixes) + _("/s")
                ),
                js_render="v => cmk.number_format.fmt_bytes(v, cmk.number_format.IECUnitPrefixes) + '/s'",
            )
        case metrics.Unit.BYTE_SI:
            return UnitInfo(
                title=_("Bytes"),
                symbol="bytes",
                render=lambda v: render.fmt_bytes(v, unit_prefix_type=render.SIUnitPrefixes),
                js_render="v => cmk.number_format.fmt_bytes(v, cmk.number_format.SIUnitPrefixes)",
            )
        case metrics.Unit.BYTES_SI_PER_DAY:
            # Output in bytes/days, value is in bytes/s
            return UnitInfo(
                title=_("Bytes per day"),
                symbol="bytes/d",
                render=lambda v: (
                    render.fmt_bytes(v * 86400.0, unit_prefix_type=render.SIUnitPrefixes) + _("/d")
                ),
                js_render="v => cmk.number_format.fmt_bytes(v * 86400.0, cmk.number_format.SIUnitPrefixes) + '/d'",
            )
        case metrics.Unit.BYTES_SI_PER_OPERATION:
            return UnitInfo(
                title=_("Bytes per operation"),
                symbol="bytes/op",
                render=lambda v: (
                    render.fmt_bytes(v, unit_prefix_type=render.SIUnitPrefixes) + _("/op")
                ),
                js_render="v => cmk.number_format.fmt_bytes(v, cmk.number_format.SIUnitPrefixes) + '/op'",
            )
        case metrics.Unit.BYTES_SI_PER_SECOND:
            return UnitInfo(
                title=_("Bytes per second"),
                symbol="bytes/s",
                render=lambda v: (
                    render.fmt_bytes(v, unit_prefix_type=render.SIUnitPrefixes) + _("/s")
                ),
                js_render="v => cmk.number_format.fmt_bytes(v, cmk.number_format.SIUnitPrefixes) + '/s'",
            )
        case metrics.Unit.COUNT:
            return UnitInfo(
                title=_("Count"),
                symbol="",
                render=lambda v: render.fmt_number_with_precision(v, drop_zeroes=True),
                js_render="v => cmk.number_format.fmt_number_with_precision(v, cmk.number_format.SIUnitPrefixes, 2, true)",
            )
        case metrics.Unit.DECIBEL:
            return UnitInfo(
                title=_("Decibel"),
                symbol="dB",
                render=lambda v: render.physical_precision(v, 3, _("dB")),
                js_render="v => cmk.number_format.drop_dotzero(v) + 'dB'",
            )
        case metrics.Unit.DECIBEL_MILLIVOLT:
            return UnitInfo(
                title=_("Decibel-millivolt"),
                symbol="dBmV",
                render=lambda v: "{} {}".format(render.drop_dotzero(v), _("dBmV")),
                js_render="v => cmk.number_format.drop_dotzero(v) + ' dBmV'",
            )
        case metrics.Unit.DECIBEL_MILLIWATT:
            return UnitInfo(
                title=_("Decibel-milliwatt"),
                symbol="dBm",
                render=lambda v: "{} {}".format(render.drop_dotzero(v), _("dBm")),
                js_render="v => cmk.number_format.drop_dotzero(v) + ' dBm'",
            )
        case metrics.Unit.DOLLAR:
            return UnitInfo(
                title=_("Dollar"),
                symbol="$",
                render=lambda v: "%s $" % v,
                js_render="v =>v.toFixed(2) + ' $'",
            )
        case metrics.Unit.ELETRICAL_ENERGY:
            return UnitInfo(
                title=_("Electrical energy"),
                symbol="Wh",
                render=lambda v: render.physical_precision(v, 3, _("Wh")),
                js_render="v => cmk.number_format.physical_precision(v, 3, 'Wh')",
            )
        case metrics.Unit.EURO:
            return UnitInfo(
                title=_("Euro"),
                symbol="€",
                render=lambda v: "%s €" % v,
                js_render="v =>v.toFixed(2) + ' €'",
            )
        case metrics.Unit.LITER_PER_SECOND:
            return UnitInfo(
                title=_("Liter per second"),
                symbol="l/s",
                render=lambda v: render.physical_precision(v, 3, _("l/s")),
                js_render="v => cmk.number_format.physical_precision(v, 3, 'l/s')",
            )
        case metrics.Unit.NUMBER:
            return UnitInfo(
                title=_("Number"),
                symbol="",
                render=lambda v: render.scientific(v, 2),
                js_render="v => cmk.number_format.scientific(v, 2)",
            )
        case metrics.Unit.PARTS_PER_MILLION:
            return UnitInfo(
                title=_("Parts per million"),
                symbol="ppm",
                render=lambda v: render.physical_precision(v, 3, _("ppm")),
                js_render="v => cmk.number_format.physical_precision(v, 3, 'ppm')",
            )
        case metrics.Unit.PERCENTAGE:
            return UnitInfo(
                title=_("Percentage"),
                symbol="%",
                render=lambda v: render.percent(v, scientific_notation=True),
                js_render="v => cmk.number_format.percent(v, true)",
            )
        case metrics.Unit.PERCENTAGE_PER_METER:
            return UnitInfo(
                title=_("Percentage per meter"),
                symbol="%/m",
                render=lambda v: render.percent(v, scientific_notation=True) + _("/m"),
                js_render="v => cmk.number_format.percent(v, true) + '/m'",
            )
        case metrics.Unit.PER_SECOND:
            return UnitInfo(
                title=_("Per second"),
                symbol="1/s",
                render=lambda v: "{}{}".format(render.scientific(v, 2), _("/s")),
                js_render="v => cmk.number_format.scientific(v, 2) + '/s'",
            )
        case metrics.Unit.READ_CAPACITY_UNIT:
            return UnitInfo(
                title=_("Read capacity unit"),
                symbol="RCU",
                render=lambda v: render.fmt_number_with_precision(v, precision=3, unit="RCU"),
                js_render="v => cmk.number_format.fmt_number_with_precision(v, cmk.number_format.SIUnitPrefixes, 3, false, 'RCU')",
            )
        case metrics.Unit.REVOLUTIONS_PER_MINUTE:
            return UnitInfo(
                title=_("Revolutions per minute"),
                symbol="rpm",
                render=lambda v: render.physical_precision(v, 4, _("rpm")),
                js_render="v => cmk.number_format.physical_precision(v, 4, 'rpm')",
            )
        case metrics.Unit.SECONDS_PER_SECOND:
            return UnitInfo(
                title=_("Seconds per second"),
                symbol="s/s",
                render=lambda v: render.physical_precision(v, 3, _("s/s")),
                js_render="v => cmk.number_format.physical_precision(v, 3, 's/s')",
            )
        case metrics.Unit.VOLT_AMPERE:
            return UnitInfo(
                title=_("Electrical Apparent Power"),
                symbol="VA",
                render=lambda v: render.physical_precision(v, 3, _("VA")),
                js_render="v => cmk.number_format.physical_precision(v, 3, 'VA')",
            )
        case metrics.Unit.WRITE_CAPACITY_UNIT:
            return UnitInfo(
                title=_("Write capacity unit"),
                symbol="WCU",
                render=lambda v: render.fmt_number_with_precision(v, precision=3, unit="WCU"),
                js_render="v => cmk.number_format.fmt_number_with_precision(v, cmk.number_format.SIUnitPrefixes, 3, false, 'WCU')",
            )
        case metrics.Unit.AMPERE:
            return UnitInfo(
                title=_("Electrical Current"),
                symbol="A",
                render=lambda v: render.physical_precision(v, 3, _("A")),
                js_render="v => cmk.number_format.physical_precision(v, 3, 'A')",
            )
        case metrics.Unit.CANDELA:
            return UnitInfo(
                title=_("Luminous intensity"),
                symbol="cd",
                render=lambda v: render.physical_precision(v, 3, _("cd")),
                js_render="v => cmk.number_format.physical_precision(v, 3, 'cd')",
            )
        case metrics.Unit.KELVIN:
            return UnitInfo(
                title=_("Temperature"),
                symbol="K",
                render=lambda v: render.physical_precision(v, 3, _("K")),
                js_render="v => cmk.number_format.physical_precision(v, 3, 'K')",
            )
        case metrics.Unit.KILOGRAM:
            return UnitInfo(
                title=_("Mass"),
                symbol="kg",
                render=lambda v: render.physical_precision(v, 3, _("kg")),
                js_render="v => cmk.number_format.physical_precision(v, 3, 'kg')",
            )
        case metrics.Unit.METRE:
            return UnitInfo(
                title=_("Length"),
                symbol="m",
                render=lambda v: render.physical_precision(v, 3, _("m")),
                js_render="v => cmk.number_format.physical_precision(v, 3, 'm')",
            )
        case metrics.Unit.MOLE:
            return UnitInfo(
                title=_("Amount of substance"),
                symbol="mol",
                render=lambda v: render.physical_precision(v, 3, _("mol")),
                js_render="v => cmk.number_format.physical_precision(v, 3, 'mol')",
            )
        case metrics.Unit.SECOND:
            return UnitInfo(
                title=_("Time"),
                symbol="s",
                render=render.approx_age,
                js_render="v => cmk.number_format.approx_age",
            )
        case metrics.Unit.BECQUEREL:
            return UnitInfo(
                title=_("Radioactive activity"),
                symbol="Bq",
                render=lambda v: render.physical_precision(v, 3, _("Bq")),
                js_render="v => cmk.number_format.physical_precision(v, 3, 'Bq')",
            )
        case metrics.Unit.COULOMB:
            return UnitInfo(
                title=_("Electric charge"),
                symbol="C",
                render=lambda v: render.physical_precision(v, 3, _("C")),
                js_render="v => cmk.number_format.physical_precision(v, 3, 'C')",
            )
        case metrics.Unit.DEGREE_CELSIUS:
            return UnitInfo(
                title=_("Temperature"),
                symbol="°C",
                render=lambda v: "{} {}".format(render.drop_dotzero(v), "°C"),
                js_render="v => cmk.number_format.drop_dotzero(v) + ' °C'",
            )
        case metrics.Unit.FARAD:
            return UnitInfo(
                title=_("Capacitance"),
                symbol="F",
                render=lambda v: render.physical_precision(v, 3, _("F")),
                js_render="v => cmk.number_format.physical_precision(v, 3, 'F')",
            )
        case metrics.Unit.GRAY:
            return UnitInfo(
                title=_("Radioactive dose"),
                symbol="Gy",
                render=lambda v: render.physical_precision(v, 3, _("Gy")),
                js_render="v => cmk.number_format.physical_precision(v, 3, 'Gy')",
            )
        case metrics.Unit.HENRY:
            return UnitInfo(
                title=_("Inductance"),
                symbol="H",
                render=lambda v: render.physical_precision(v, 3, _("H")),
                js_render="v => cmk.number_format.physical_precision(v, 3, 'H')",
            )
        case metrics.Unit.HERTZ:
            return UnitInfo(
                title=_("Frequency"),
                symbol="Hz",
                render=lambda v: render.physical_precision(v, 3, _("Hz")),
                js_render="v => cmk.number_format.physical_precision(v, 3, 'Hz')",
            )
        case metrics.Unit.JOULE:
            return UnitInfo(
                title=_("Heat"),
                symbol="J",
                render=lambda v: render.physical_precision(v, 3, _("J")),
                js_render="v => cmk.number_format.physical_precision(v, 3, 'J')",
            )
        case metrics.Unit.KATAL:
            return UnitInfo(
                title=_("Catalytic activity"),
                symbol="kat",
                render=lambda v: render.physical_precision(v, 3, _("kat")),
                js_render="v => cmk.number_format.physical_precision(v, 3, 'kat')",
            )
        case metrics.Unit.LUMEN:
            return UnitInfo(
                title=_("Luminous flux"),
                symbol="lm",
                render=lambda v: render.physical_precision(v, 3, _("lm")),
                js_render="v => cmk.number_format.physical_precision(v, 3, 'lm')",
            )
        case metrics.Unit.LUX:
            return UnitInfo(
                title=_("Illuminance"),
                symbol="lx",
                render=lambda v: render.physical_precision(v, 3, _("lx")),
                js_render="v => cmk.number_format.physical_precision(v, 3, 'lx')",
            )
        case metrics.Unit.NEWTON:
            return UnitInfo(
                title=_("Force"),
                symbol="N",
                render=lambda v: render.physical_precision(v, 3, _("N")),
                js_render="v => cmk.number_format.physical_precision(v, 3, 'N')",
            )
        case metrics.Unit.OHM:
            return UnitInfo(
                title=_("Impedance"),
                symbol="Ω",
                render=lambda v: render.physical_precision(v, 3, _("Ω")),
                js_render="v => cmk.number_format.physical_precision(v, 3, 'Ω')",
            )
        case metrics.Unit.PASCAL:
            return UnitInfo(
                title=_("Pressure"),
                symbol="Pa",
                render=lambda v: render.physical_precision(v, 3, _("Pa")),
                js_render="v => cmk.number_format.physical_precision(v, 3, 'Pa')",
            )
        case metrics.Unit.RADIAN:
            return UnitInfo(
                title=_("Plane angle"),
                symbol="rad",
                render=lambda v: render.physical_precision(v, 3, _("rad")),
                js_render="v => cmk.number_format.physical_precision(v, 3, 'rad')",
            )
        case metrics.Unit.SIEMENS:
            return UnitInfo(
                title=_("Electrical conductance"),
                symbol="S",
                render=lambda v: render.physical_precision(v, 3, _("S")),
                js_render="v => cmk.number_format.physical_precision(v, 3, 'S')",
            )
        case metrics.Unit.SIEVERT:
            return UnitInfo(
                title=_("Dose equivalent"),
                symbol="Sv",
                render=lambda v: render.physical_precision(v, 3, _("Sv")),
                js_render="v => cmk.number_format.physical_precision(v, 3, 'Sv')",
            )
        case metrics.Unit.STERADIAN:
            return UnitInfo(
                title=_("Solid angle"),
                symbol="sr",
                render=lambda v: render.physical_precision(v, 3, _("sr")),
                js_render="v => cmk.number_format.physical_precision(v, 3, 'sr')",
            )
        case metrics.Unit.TESLA:
            return UnitInfo(
                title=_("Magnetic flux density"),
                symbol="T",
                render=lambda v: render.physical_precision(v, 3, _("T")),
                js_render="v => cmk.number_format.physical_precision(v, 3, 'T')",
            )
        case metrics.Unit.VOLT:
            return UnitInfo(
                title=_("Electric potential"),
                symbol="V",
                render=lambda v: render.physical_precision(v, 3, _("V")),
                js_render="v => cmk.number_format.physical_precision(v, 3, 'V')",
            )
        case metrics.Unit.WATT:
            return UnitInfo(
                title=_("Power"),
                symbol="W",
                render=lambda v: render.physical_precision(v, 3, _("W")),
                js_render="v => cmk.number_format.physical_precision(v, 3, 'W')",
            )
        case metrics.Unit.WEBER:
            return UnitInfo(
                title=_("Magnetic flux"),
                symbol="Wb",
                render=lambda v: render.physical_precision(v, 3, _("Wb")),
                js_render="v => cmk.number_format.physical_precision(v, 3, 'Wb')",
            )
        case metrics.DecimalUnit():
            return UnitInfo(
                title=unit.title.localize(_),
                symbol=unit.symbol,
                render=lambda v: render.physical_precision(v, 3, unit.symbol),
                js_render=f"v => cmk.number_format.physical_precision(v, 3, '{unit.symbol}')",
            )
        case metrics.ScientificUnit():
            return UnitInfo(
                title=unit.title.localize(_),
                symbol=unit.symbol,
                render=lambda v: "{} {}".format(render.scientific(v, 2), unit.symbol),
                js_render=f"v => cmk.number_format.scientific(v, 2) + '{unit.symbol}'",
            )


@dataclass(frozen=True)
class RGB:
    red: int
    green: int
    blue: int


def color_to_rgb(color: metrics.Color) -> RGB:
    match color:
        case metrics.Color.LIGHT_RED:
            return RGB(255, 51, 51)
        case metrics.Color.RED:
            return RGB(204, 0, 0)
        case metrics.Color.DARK_RED:
            return RGB(122, 0, 0)

        case metrics.Color.LIGHT_ORANGE:
            return RGB(255, 163, 71)
        case metrics.Color.ORANGE:
            return RGB(255, 127, 0)
        case metrics.Color.DARK_ORANGE:
            return RGB(204, 102, 0)

        case metrics.Color.LIGHT_YELLOW:
            return RGB(255, 255, 112)
        case metrics.Color.YELLOW:
            return RGB(245, 245, 0)
        case metrics.Color.DARK_YELLOW:
            return RGB(204, 204, 0)

        case metrics.Color.LIGHT_GREEN:
            return RGB(112, 255, 112)
        case metrics.Color.GREEN:
            return RGB(0, 255, 0)
        case metrics.Color.DARK_GREEN:
            return RGB(0, 143, 0)

        case metrics.Color.LIGHT_BLUE:
            return RGB(71, 71, 255)
        case metrics.Color.BLUE:
            return RGB(0, 0, 255)
        case metrics.Color.DARK_BLUE:
            return RGB(0, 0, 163)

        case metrics.Color.LIGHT_CYAN:
            return RGB(153, 255, 255)
        case metrics.Color.CYAN:
            return RGB(0, 255, 255)
        case metrics.Color.DARK_CYAN:
            return RGB(0, 184, 184)

        case metrics.Color.LIGHT_PURPLE:
            return RGB(163, 71, 255)
        case metrics.Color.PURPLE:
            return RGB(127, 0, 255)
        case metrics.Color.DARK_PURPLE:
            return RGB(82, 0, 163)

        case metrics.Color.LIGHT_PINK:
            return RGB(255, 214, 220)
        case metrics.Color.PINK:
            return RGB(255, 192, 203)
        case metrics.Color.DARK_PINK:
            return RGB(255, 153, 170)

        case metrics.Color.LIGHT_BROWN:
            return RGB(184, 92, 0)
        case metrics.Color.BROWN:
            return RGB(143, 71, 0)
        case metrics.Color.DARK_BROWN:
            return RGB(102, 51, 0)

        case metrics.Color.LIGHT_GRAY:
            return RGB(153, 153, 153)
        case metrics.Color.GRAY:
            return RGB(127, 127, 127)
        case metrics.Color.DARK_GRAY:
            return RGB(92, 92, 92)

        case metrics.Color.BLACK:
            return RGB(0, 0, 0)
        case metrics.Color.WHITE:
            return RGB(255, 255, 255)


def parse_color(color: metrics.Color) -> str:
    rgb = color_to_rgb(color)
    return f"#{rgb.red:02x}{rgb.green:02x}{rgb.blue:02x}"
