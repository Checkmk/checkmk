#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Module to hold shared code for check parameter module internals"""

from typing import List, Tuple as _Tuple
from cmk.gui.i18n import _
from cmk.gui.exceptions import MKUserError
from cmk.gui.valuespec import (
    Alternative,
    CascadingDropdown,
    Checkbox,
    Dictionary,
    DropdownChoice,
    Filesize,
    FixedValue,
    Float,
    Integer,
    ListOf,
    Optional,
    Percentage,
    Transform,
    Tuple,
    ValueSpec,
)
from cmk.gui.plugins.wato import PredictiveLevels


# Match and transform functions for level configurations like
# -- used absolute,        positive int   (2, 4)
# -- used percentage,      positive float (2.0, 4.0)
# -- available absolute,   negative int   (-2, -4)
# -- available percentage, negative float (-2.0, -4.0)
# (4 alternatives)
def match_dual_level_type(value):
    if isinstance(value, list):
        for entry in value:
            if entry[1][0] < 0 or entry[1][1] < 0:
                return 1
        return 0
    if value[0] < 0 or value[1] < 0:
        return 1
    return 0


def get_free_used_dynamic_valuespec(what, name, default_value=(80.0, 90.0)):
    if what == "used":
        title = _("used space")
        course = _("above")
    else:
        title = _("free space")
        course = _("below")

    vs_subgroup: List[ValueSpec] = [
        Tuple(title=_("Percentage %s") % title,
              elements=[
                  Percentage(title=_("Warning if %s") % course, unit="%", minvalue=0.0),
                  Percentage(title=_("Critical if %s") % course, unit="%", minvalue=0.0),
              ]),
        Tuple(title=_("Absolute %s") % title,
              elements=[
                  Integer(title=_("Warning if %s") % course, unit=_("MB"), minvalue=0),
                  Integer(title=_("Critical if %s") % course, unit=_("MB"), minvalue=0),
              ])
    ]

    def validate_dynamic_levels(value, varprefix):
        if [v for v in value if v[0] < 0]:
            raise MKUserError(varprefix, _("You need to specify levels " "of at least 0 bytes."))

    return Alternative(
        title=_("Levels for %s %s") % (name, title),
        show_alternative_title=True,
        default_value=default_value,
        elements=vs_subgroup + [
            ListOf(
                Tuple(orientation="horizontal",
                      elements=[
                          Filesize(title=_("%s larger than") % name.title()),
                          Alternative(elements=vs_subgroup)
                      ]),
                title=_('Dynamic levels'),
                allow_empty=False,
                validate=validate_dynamic_levels,
            )
        ],
    )


def transform_filesystem_free(value):
    tuple_convert = lambda val: tuple(-x for x in val)

    if isinstance(value, tuple):
        return tuple_convert(value)

    result = []
    for item in value:
        result.append((item[0], tuple_convert(item[1])))
    return result


fs_levels_elements = [
    ("levels",
     Alternative(
         title=_("Levels for filesystem"),
         show_alternative_title=True,
         default_value=(80.0, 90.0),
         match=match_dual_level_type,
         elements=[
             get_free_used_dynamic_valuespec("used", "filesystem"),
             Transform(
                 get_free_used_dynamic_valuespec("free", "filesystem", default_value=(20.0, 10.0)),
                 title=_("Levels for filesystem free space"),
                 forth=transform_filesystem_free,
                 back=transform_filesystem_free,
             )
         ],
     )),
    ("show_levels",
     DropdownChoice(
         title=_("Display warn/crit levels in check output..."),
         choices=[
             ("onproblem", _("Only if the status is non-OK")),
             ("onmagic", _("If the status is non-OK or a magic factor is set")),
             ("always", _("Always")),
         ],
         default_value="onmagic",
     )),
]

# Note: This hack is only required on very old filesystem checks (prior August 2013)
fs_levels_elements_hack: List[_Tuple[str, ValueSpec]] = [
    # Beware: this is a nasty hack that helps us to detect new-style parameters.
    # Something hat has todo with float/int conversion and has not been documented
    # by the one who implemented this.
    ("flex_levels", FixedValue(
        None,
        totext="",
        title="",
    )),
]

fs_reserved_elements: List[_Tuple[str, ValueSpec]] = [
    ("show_reserved",
     DropdownChoice(
         title=_("Show space reserved for the <tt>root</tt> user"),
         help=
         _("Check_MK treats space that is reserved for the <tt>root</tt> user on Linux and Unix as "
           "used space. Usually, 5% are being reserved for root when a new filesystem is being created. "
           "With this option you can have Check_MK display the current amount of reserved but yet unused "
           "space."),
         choices=[
             (True, _("Show reserved space")),
             (False, _("Do now show reserved space")),
         ])),
    ("subtract_reserved",
     DropdownChoice(
         title=_(
             "Exclude space reserved for the <tt>root</tt> user from calculation of used space"),
         help=
         _("By default Check_MK treats space that is reserved for the <tt>root</tt> user on Linux and Unix as "
           "used space. Usually, 5% are being reserved for root when a new filesystem is being created. "
           "With this option you can have Check_MK exclude the current amount of reserved but yet unused "
           "space from the calculations regarding the used space percentage."),
         choices=[
             (False, _("Include reserved space")),
             (True, _("Exclude reserved space")),
         ])),
]

fs_inodes_elements = [
    ("inodes_levels",
     Alternative(
         title=_("Levels for Inodes"),
         help=_("The number of remaining inodes on the filesystem. "
                "Please note that this setting has no effect on some filesystem checks."),
         elements=[
             Tuple(title=_("Percentage free"),
                   elements=[
                       Percentage(title=_("Warning if less than")),
                       Percentage(title=_("Critical if less than")),
                   ]),
             Tuple(
                 title=_("Absolute free"),
                 elements=[
                     Integer(title=_("Warning if less than"),
                             size=10,
                             unit=_("inodes"),
                             minvalue=0,
                             default_value=10000),
                     Integer(title=_("Critical if less than"),
                             size=10,
                             unit=_("inodes"),
                             minvalue=0,
                             default_value=5000),
                 ],
             ),
             FixedValue(
                 None,
                 totext="",
                 title=_("Ignore levels"),
             ),
         ],
         default_value=(10.0, 5.0),
     )),
    ("show_inodes",
     DropdownChoice(
         title=_("Display inode usage in check output..."),
         choices=[
             ("onproblem", _("Only in case of a problem")),
             ("onlow", _("Only in case of a problem or if inodes are below 50%")),
             ("always", _("Always")),
         ],
         default_value="onlow",
     ))
]

fs_magic_elements = [
    ("magic",
     Float(title=_("Magic factor (automatic level adaptation for large filesystems)"),
           default_value=0.8,
           minvalue=0.1,
           maxvalue=1.0)),
    ("magic_normsize",
     Integer(title=_("Reference size for magic factor"), default_value=20, minvalue=1,
             unit=_("GB"))),
    ("levels_low",
     Tuple(title=_("Minimum levels if using magic factor"),
           help=_("The filesystem levels will never fall below these values, when using "
                  "the magic factor and the filesystem is very small."),
           elements=[
               Percentage(title=_("Warning at"),
                          unit=_("% usage"),
                          allow_int=True,
                          default_value=50),
               Percentage(title=_("Critical at"),
                          unit=_("% usage"),
                          allow_int=True,
                          default_value=60)
           ]))
]

size_trend_elements = [
    ("trend_range",
     Optional(Integer(title=_("Time Range for trend computation"),
                      default_value=24,
                      minvalue=1,
                      unit=_("hours")),
              title=_("Trend computation"),
              label=_("Enable trend computation"))),
    ("trend_mb",
     Tuple(title=_("Levels on trends in MB per time range"),
           elements=[
               Integer(title=_("Warning at"), unit=_("MB / range"), default_value=100),
               Integer(title=_("Critical at"), unit=_("MB / range"), default_value=200)
           ])),
    ("trend_perc",
     Tuple(title=_("Levels for the percentual growth per time range"),
           elements=[
               Percentage(
                   title=_("Warning at"),
                   unit=_("% / range"),
                   default_value=5,
               ),
               Percentage(
                   title=_("Critical at"),
                   unit=_("% / range"),
                   default_value=10,
               ),
           ])),
    ("trend_timeleft",
     Tuple(title=_("Levels on the time left until full"),
           elements=[
               Integer(
                   title=_("Warning if below"),
                   unit=_("hours"),
                   default_value=12,
               ),
               Integer(
                   title=_("Critical if below"),
                   unit=_("hours"),
                   default_value=6,
               ),
           ])),
    ("trend_showtimeleft",
     Checkbox(title=_("Display time left in check output"),
              label=_("Enable"),
              help=_("Normally, the time left until the disk is full is only displayed when "
                     "the configured levels have been breached. If you set this option "
                     "the check always reports this information"))),
    ("trend_perfdata",
     Checkbox(title=_("Trend performance data"),
              label=_("Enable generation of performance data from trends"))),
]

filesystem_elements: List[_Tuple[str, ValueSpec]] = fs_levels_elements \
                    + fs_levels_elements_hack \
                    + fs_reserved_elements \
                    + fs_inodes_elements \
                    + fs_magic_elements \
                    + size_trend_elements


def vs_filesystem(extra_elements=None):
    if extra_elements is None:
        extra_elements = []
    return Dictionary(
        help=_("This ruleset allows to set parameters for space and inodes usage"),
        elements=filesystem_elements + extra_elements,
        hidden_keys=["flex_levels"],
        ignored_keys=["patterns"],
    )


def vs_interface_traffic():
    def vs_abs_perc():
        return CascadingDropdown(orientation="horizontal",
                                 choices=[("perc",
                                           _("Percentual levels (in relation to port speed)"),
                                           Tuple(orientation="float",
                                                 show_titles=False,
                                                 elements=[
                                                     Percentage(label=_("Warning at")),
                                                     Percentage(label=_("Critical at")),
                                                 ])),
                                          ("abs", _("Absolute levels in bits or bytes per second"),
                                           Tuple(orientation="float",
                                                 show_titles=False,
                                                 elements=[
                                                     Integer(label=_("Warning at")),
                                                     Integer(label=_("Critical at")),
                                                 ])),
                                          ("predictive", _("Predictive Levels (only on CMC)"),
                                           PredictiveLevels())])

    return CascadingDropdown(orientation="horizontal",
                             choices=[
                                 ("upper", _("Upper"), vs_abs_perc()),
                                 ("lower", _("Lower"), vs_abs_perc()),
                             ])
