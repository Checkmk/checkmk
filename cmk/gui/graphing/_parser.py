#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import cmk.utils.render as render

from cmk.gui.i18n import _

from cmk.graphing.v1 import Color, PhysicalUnit, ScientificUnit, Unit

from ._type_defs import UnitInfo


def parse_unit(unit: Unit | PhysicalUnit | ScientificUnit) -> UnitInfo:
    match unit:
        case Unit.BAR:
            return UnitInfo(
                title=_("Pressure"),
                symbol=unit.value,
                render=lambda v: render.physical_precision(v, 4, _("bar")),
                js_render="v => cmk.number_format.physical_precision(v, 4, 'bar')",
            )
        case Unit.BITS_IEC:
            return UnitInfo(
                title=_("Bits"),
                symbol=unit.value,
                render=lambda v: render.fmt_bytes(
                    v, unit_prefix_type=render.IECUnitPrefixes, unit="bits"
                ),
                js_render="v => cmk.number_format.fmt_bytes(v, cmk.number_format.IECUnitPrefixes, 2, 'bits')",
            )
        case Unit.BITS_IEC_PER_SECOND:
            return UnitInfo(
                title=_("Bits per second"),
                symbol=unit.value,
                render=lambda v: (
                    render.fmt_bytes(v, unit_prefix_type=render.IECUnitPrefixes, unit="bits")
                    + _("/s")
                ),
                js_render="v => cmk.number_format.fmt_bytes(v, cmk.number_format.IECUnitPrefixes, 2, 'bits') + '/s'",
            )
        case Unit.BITS_SI:
            return UnitInfo(
                title=_("Bits"),
                symbol=unit.value,
                render=lambda v: render.fmt_bytes(
                    v, unit_prefix_type=render.SIUnitPrefixes, unit="bits"
                ),
                js_render="v => cmk.number_format.fmt_bytes(v, cmk.number_format.SIUnitPrefixes, 2, 'bits')",
            )
        case Unit.BITS_SI_PER_SECOND:
            return UnitInfo(
                title=_("Bits per second"),
                symbol=unit.value,
                render=lambda v: (
                    render.fmt_bytes(v, unit_prefix_type=render.SIUnitPrefixes, unit="bits")
                    + _("/s")
                ),
                js_render="v => cmk.number_format.fmt_bytes(v, cmk.number_format.SIUnitPrefixes, 2, 'bits') + '/s'",
            )
        case Unit.BYTES_IEC:
            return UnitInfo(
                title=_("Bytes"),
                symbol=unit.value,
                render=lambda v: render.fmt_bytes(v, unit_prefix_type=render.IECUnitPrefixes),
                js_render="v => cmk.number_format.fmt_bytes(v, cmk.number_format.IECUnitPrefixes)",
            )
        case Unit.BYTES_IEC_PER_DAY:
            # Output in bytes/days, value is in bytes/s
            return UnitInfo(
                title=_("Bytes per day"),
                symbol=unit.value,
                render=lambda v: (
                    render.fmt_bytes(v * 86400.0, unit_prefix_type=render.IECUnitPrefixes) + _("/d")
                ),
                js_render="v => cmk.number_format.fmt_bytes(v * 86400.0, cmk.number_format.IECUnitPrefixes) + '/d'",
            )
        case Unit.BYTES_IEC_PER_OPERATION:
            return UnitInfo(
                title=_("Bytes per operation"),
                symbol=unit.value,
                render=lambda v: (
                    render.fmt_bytes(v, unit_prefix_type=render.IECUnitPrefixes) + _("/op")
                ),
                js_render="v => cmk.number_format.fmt_bytes(v, cmk.number_format.IECUnitPrefixes) + '/op'",
            )
        case Unit.BYTES_IEC_PER_SECOND:
            return UnitInfo(
                title=_("Bytes per second"),
                symbol=unit.value,
                render=lambda v: (
                    render.fmt_bytes(v, unit_prefix_type=render.IECUnitPrefixes) + _("/s")
                ),
                js_render="v => cmk.number_format.fmt_bytes(v, cmk.number_format.IECUnitPrefixes) + '/s'",
            )
        case Unit.BYTES_SI:
            return UnitInfo(
                title=_("Bytes"),
                symbol=unit.value,
                render=lambda v: render.fmt_bytes(v, unit_prefix_type=render.SIUnitPrefixes),
                js_render="v => cmk.number_format.fmt_bytes(v, cmk.number_format.SIUnitPrefixes)",
            )
        case Unit.BYTES_SI_PER_DAY:
            # Output in bytes/days, value is in bytes/s
            return UnitInfo(
                title=_("Bytes per day"),
                symbol=unit.value,
                render=lambda v: (
                    render.fmt_bytes(v * 86400.0, unit_prefix_type=render.SIUnitPrefixes) + _("/d")
                ),
                js_render="v => cmk.number_format.fmt_bytes(v * 86400.0, cmk.number_format.SIUnitPrefixes) + '/d'",
            )
        case Unit.BYTES_SI_PER_OPERATION:
            return UnitInfo(
                title=_("Bytes per operation"),
                symbol=unit.value,
                render=lambda v: (
                    render.fmt_bytes(v, unit_prefix_type=render.SIUnitPrefixes) + _("/op")
                ),
                js_render="v => cmk.number_format.fmt_bytes(v, cmk.number_format.SIUnitPrefixes) + '/op'",
            )
        case Unit.BYTES_SI_PER_SECOND:
            return UnitInfo(
                title=_("Bytes per second"),
                symbol=unit.value,
                render=lambda v: (
                    render.fmt_bytes(v, unit_prefix_type=render.SIUnitPrefixes) + _("/s")
                ),
                js_render="v => cmk.number_format.fmt_bytes(v, cmk.number_format.SIUnitPrefixes) + '/s'",
            )
        case Unit.COUNT:
            return UnitInfo(
                title=_("Count"),
                symbol="",
                render=lambda v: render.fmt_number_with_precision(v, drop_zeroes=True),
                js_render="v => cmk.number_format.fmt_number_with_precision(v, cmk.number_format.SIUnitPrefixes, 2, true)",
            )
        case Unit.DECIBEL:
            return UnitInfo(
                title=_("Decibel"),
                symbol=unit.value,
                render=lambda v: render.physical_precision(v, 3, _("dB")),
                js_render="v => cmk.number_format.drop_dotzero(v) + 'dB'",
            )
        case Unit.DECIBEL_MILLIVOLT:
            return UnitInfo(
                title=_("Decibel-millivolt"),
                symbol=unit.value,
                render=lambda v: "{} {}".format(render.drop_dotzero(v), _("dBmV")),
                js_render="v => cmk.number_format.drop_dotzero(v) + ' dBmV'",
            )
        case Unit.DECIBEL_MILLIWATT:
            return UnitInfo(
                title=_("Decibel-milliwatt"),
                symbol=unit.value,
                render=lambda v: "{} {}".format(render.drop_dotzero(v), _("dBm")),
                js_render="v => cmk.number_format.drop_dotzero(v) + ' dBm'",
            )
        case Unit.DOLLAR:
            return UnitInfo(
                title=_("Dollar"),
                symbol=unit.value,
                render=lambda v: "%s $" % v,
                js_render="v =>v.toFixed(2) + ' $'",
            )
        case Unit.ELETRICAL_ENERGY:
            return UnitInfo(
                title=_("Electrical energy"),
                symbol=unit.value,
                render=lambda v: render.physical_precision(v, 3, _("Wh")),
                js_render="v => cmk.number_format.physical_precision(v, 3, 'Wh')",
            )
        case Unit.EURO:
            return UnitInfo(
                title=_("Euro"),
                symbol=unit.value,
                render=lambda v: "%s €" % v,
                js_render="v =>v.toFixed(2) + ' €'",
            )
        case Unit.LITER_PER_SECOND:
            return UnitInfo(
                title=_("Liter per second"),
                symbol=unit.value,
                render=lambda v: render.physical_precision(v, 3, _("l/s")),
                js_render="v => cmk.number_format.physical_precision(v, 3, 'l/s')",
            )
        case Unit.NUMBER:
            return UnitInfo(
                title=_("Number"),
                symbol="",
                render=lambda v: render.scientific(v, 2),
                js_render="v => cmk.number_format.scientific(v, 2)",
            )
        case Unit.PARTS_PER_MILLION:
            return UnitInfo(
                title=_("Parts per million"),
                symbol=unit.value,
                render=lambda v: render.physical_precision(v, 3, _("ppm")),
                js_render="v => cmk.number_format.physical_precision(v, 3, 'ppm')",
            )
        case Unit.PERCENTAGE:
            return UnitInfo(
                title=_("Percentage"),
                symbol=unit.value,
                render=lambda v: render.percent(v, scientific_notation=True),
                js_render="v => cmk.number_format.percent(v, true)",
            )
        case Unit.PERCENTAGE_PER_METER:
            return UnitInfo(
                title=_("Percentage per meter"),
                symbol=unit.value,
                render=lambda v: render.percent(v, scientific_notation=True) + _("/m"),
                js_render="v => cmk.number_format.percent(v, true) + '/m'",
            )
        case Unit.PER_SECOND:
            return UnitInfo(
                title=_("Per second"),
                symbol=unit.value,
                render=lambda v: "{}{}".format(render.scientific(v, 2), _("/s")),
                js_render="v => cmk.number_format.scientific(v, 2) + '/s'",
            )
        case Unit.READ_CAPACITY_UNIT:
            return UnitInfo(
                title=_("Read capacity unit"),
                symbol=unit.value,
                render=lambda v: render.fmt_number_with_precision(v, precision=3, unit="RCU"),
                js_render="v => cmk.number_format.fmt_number_with_precision(v, cmk.number_format.SIUnitPrefixes, 3, false, 'RCU')",
            )
        case Unit.REVOLUTIONS_PER_MINUTE:
            return UnitInfo(
                title=_("Revolutions per minute"),
                symbol=unit.value,
                render=lambda v: render.physical_precision(v, 4, _("rpm")),
                js_render="v => cmk.number_format.physical_precision(v, 4, 'rpm')",
            )
        case Unit.SECONDS_PER_SECOND:
            return UnitInfo(
                title=_("Seconds per second"),
                symbol=unit.value,
                render=lambda v: render.physical_precision(v, 3, _("s/s")),
                js_render="v => cmk.number_format.physical_precision(v, 3, 's/s')",
            )
        case Unit.VOLT_AMPERE:
            return UnitInfo(
                title=_("Electrical Apparent Power"),
                symbol=unit.value,
                render=lambda v: render.physical_precision(v, 3, _("VA")),
                js_render="v => cmk.number_format.physical_precision(v, 3, 'VA')",
            )
        case Unit.WRITE_CAPACITY_UNIT:
            return UnitInfo(
                title=_("Write capacity unit"),
                symbol=unit.value,
                render=lambda v: render.fmt_number_with_precision(v, precision=3, unit="WCU"),
                js_render="v => cmk.number_format.fmt_number_with_precision(v, cmk.number_format.SIUnitPrefixes, 3, false, 'WCU')",
            )
        case Unit.AMPERE:
            return UnitInfo(
                title=_("Electrical Current"),
                symbol=unit.value,
                render=lambda v: render.physical_precision(v, 3, _("A")),
                js_render="v => cmk.number_format.physical_precision(v, 3, 'A')",
            )
        case Unit.CANDELA:
            return UnitInfo(
                title=_("Luminous intensity"),
                symbol=unit.value,
                render=lambda v: render.physical_precision(v, 3, _("cd")),
                js_render="v => cmk.number_format.physical_precision(v, 3, 'cd')",
            )
        case Unit.KELVIN:
            return UnitInfo(
                title=_("Temperature"),
                symbol=unit.value,
                render=lambda v: render.physical_precision(v, 3, _("K")),
                js_render="v => cmk.number_format.physical_precision(v, 3, 'K')",
            )
        case Unit.KILOGRAM:
            return UnitInfo(
                title=_("Mass"),
                symbol=unit.value,
                render=lambda v: render.physical_precision(v, 3, _("kg")),
                js_render="v => cmk.number_format.physical_precision(v, 3, 'kg')",
            )
        case Unit.METRE:
            return UnitInfo(
                title=_("Length"),
                symbol=unit.value,
                render=lambda v: render.physical_precision(v, 3, _("m")),
                js_render="v => cmk.number_format.physical_precision(v, 3, 'm')",
            )
        case Unit.MOLE:
            return UnitInfo(
                title=_("Amount of substance"),
                symbol=unit.value,
                render=lambda v: render.physical_precision(v, 3, _("mol")),
                js_render="v => cmk.number_format.physical_precision(v, 3, 'mol')",
            )
        case Unit.SECOND:
            return UnitInfo(
                title=_("Time"),
                symbol=unit.value,
                render=render.approx_age,
                js_render="v => cmk.number_format.approx_age",
            )
        case Unit.BECQUEREL:
            return UnitInfo(
                title=_("Radioactive activity"),
                symbol=unit.value,
                render=lambda v: render.physical_precision(v, 3, _("Bq")),
                js_render="v => cmk.number_format.physical_precision(v, 3, 'Bq')",
            )
        case Unit.COULOMB:
            return UnitInfo(
                title=_("Electric charge"),
                symbol=unit.value,
                render=lambda v: render.physical_precision(v, 3, _("C")),
                js_render="v => cmk.number_format.physical_precision(v, 3, 'C')",
            )
        case Unit.DEGREE_CELSIUS:
            return UnitInfo(
                title=_("Temperature"),
                symbol=unit.value,
                render=lambda v: "{} {}".format(render.drop_dotzero(v), "°C"),
                js_render="v => cmk.number_format.drop_dotzero(v) + ' °C'",
            )
        case Unit.FARAD:
            return UnitInfo(
                title=_("Capacitance"),
                symbol=unit.value,
                render=lambda v: render.physical_precision(v, 3, _("F")),
                js_render="v => cmk.number_format.physical_precision(v, 3, 'F')",
            )
        case Unit.GRAY:
            return UnitInfo(
                title=_("Radioactive dose"),
                symbol=unit.value,
                render=lambda v: render.physical_precision(v, 3, _("Gy")),
                js_render="v => cmk.number_format.physical_precision(v, 3, 'Gy')",
            )
        case Unit.HENRY:
            return UnitInfo(
                title=_("Inductance"),
                symbol=unit.value,
                render=lambda v: render.physical_precision(v, 3, _("H")),
                js_render="v => cmk.number_format.physical_precision(v, 3, 'H')",
            )
        case Unit.HERTZ:
            return UnitInfo(
                title=_("Frequency"),
                symbol=unit.value,
                render=lambda v: render.physical_precision(v, 3, _("Hz")),
                js_render="v => cmk.number_format.physical_precision(v, 3, 'Hz')",
            )
        case Unit.JOULE:
            return UnitInfo(
                title=_("Heat"),
                symbol=unit.value,
                render=lambda v: render.physical_precision(v, 3, _("J")),
                js_render="v => cmk.number_format.physical_precision(v, 3, 'J')",
            )
        case Unit.KATAL:
            return UnitInfo(
                title=_("Catalytic activity"),
                symbol=unit.value,
                render=lambda v: render.physical_precision(v, 3, _("kat")),
                js_render="v => cmk.number_format.physical_precision(v, 3, 'kat')",
            )
        case Unit.LUMEN:
            return UnitInfo(
                title=_("Luminous flux"),
                symbol=unit.value,
                render=lambda v: render.physical_precision(v, 3, _("lm")),
                js_render="v => cmk.number_format.physical_precision(v, 3, 'lm')",
            )
        case Unit.LUX:
            return UnitInfo(
                title=_("Illuminance"),
                symbol=unit.value,
                render=lambda v: render.physical_precision(v, 3, _("lx")),
                js_render="v => cmk.number_format.physical_precision(v, 3, 'lx')",
            )
        case Unit.NEWTON:
            return UnitInfo(
                title=_("Force"),
                symbol=unit.value,
                render=lambda v: render.physical_precision(v, 3, _("N")),
                js_render="v => cmk.number_format.physical_precision(v, 3, 'N')",
            )
        case Unit.OHM:
            return UnitInfo(
                title=_("Impedance"),
                symbol=unit.value,
                render=lambda v: render.physical_precision(v, 3, _("Ω")),
                js_render="v => cmk.number_format.physical_precision(v, 3, 'Ω')",
            )
        case Unit.PASCAL:
            return UnitInfo(
                title=_("Pressure"),
                symbol=unit.value,
                render=lambda v: render.physical_precision(v, 3, _("Pa")),
                js_render="v => cmk.number_format.physical_precision(v, 3, 'Pa')",
            )
        case Unit.RADIAN:
            return UnitInfo(
                title=_("Plane angle"),
                symbol=unit.value,
                render=lambda v: render.physical_precision(v, 3, _("rad")),
                js_render="v => cmk.number_format.physical_precision(v, 3, 'rad')",
            )
        case Unit.SIEMENS:
            return UnitInfo(
                title=_("Electrical conductance"),
                symbol=unit.value,
                render=lambda v: render.physical_precision(v, 3, _("S")),
                js_render="v => cmk.number_format.physical_precision(v, 3, 'S')",
            )
        case Unit.SIEVERT:
            return UnitInfo(
                title=_("Dose equivalent"),
                symbol=unit.value,
                render=lambda v: render.physical_precision(v, 3, _("Sv")),
                js_render="v => cmk.number_format.physical_precision(v, 3, 'Sv')",
            )
        case Unit.STERADIAN:
            return UnitInfo(
                title=_("Solid angle"),
                symbol=unit.value,
                render=lambda v: render.physical_precision(v, 3, _("sr")),
                js_render="v => cmk.number_format.physical_precision(v, 3, 'sr')",
            )
        case Unit.TESLA:
            return UnitInfo(
                title=_("Magnetic flux density"),
                symbol=unit.value,
                render=lambda v: render.physical_precision(v, 3, _("T")),
                js_render="v => cmk.number_format.physical_precision(v, 3, 'T')",
            )
        case Unit.VOLT:
            return UnitInfo(
                title=_("Electric potential"),
                symbol=unit.value,
                render=lambda v: render.physical_precision(v, 3, _("V")),
                js_render="v => cmk.number_format.physical_precision(v, 3, 'V')",
            )
        case Unit.WATT:
            return UnitInfo(
                title=_("Power"),
                symbol=unit.value,
                render=lambda v: render.physical_precision(v, 3, _("W")),
                js_render="v => cmk.number_format.physical_precision(v, 3, 'W')",
            )
        case Unit.WEBER:
            return UnitInfo(
                title=_("Magnetic flux"),
                symbol=unit.value,
                render=lambda v: render.physical_precision(v, 3, _("Wb")),
                js_render="v => cmk.number_format.physical_precision(v, 3, 'Wb')",
            )
        case PhysicalUnit():
            return UnitInfo(
                title=unit.title.localize(_),
                symbol=unit.symbol,
                render=lambda v: render.physical_precision(v, 3, unit.symbol),
                js_render=f"v => cmk.number_format.physical_precision(v, 3, '{unit.symbol}')",
            )
        case ScientificUnit():
            return UnitInfo(
                title=unit.title.localize(_),
                symbol=unit.symbol,
                render=lambda v: "{} {}".format(render.scientific(v, 2), unit.symbol),
                js_render=f"v => cmk.number_format.scientific(v, 2) + '{unit.symbol}'",
            )


def parse_color(color: Color) -> str:
    return f"#{color.value.red:02x}{color.value.green:02x}{color.value.blue:02x}"
