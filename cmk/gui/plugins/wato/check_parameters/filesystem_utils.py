#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Module to hold shared code for filesystem check parameter module internals"""

from enum import Enum
from typing import Any, Callable, List, Literal, Mapping, MutableMapping, Optional, Sequence, Union

from cmk.gui.exceptions import MKUserError
from cmk.gui.i18n import _
from cmk.gui.valuespec import (
    Alternative,
    Checkbox,
    Dictionary,
    DictionaryEntry,
    DropdownChoice,
    Filesize,
    FixedValue,
    Float,
    Integer,
    ListOf,
    Percentage,
    Transform,
    Tuple,
    ValueSpec,
)

ParamType = Mapping[str, Any]
MutableParamType = MutableMapping[str, Any]


class FilesystemElements(Enum):
    levels = "levels"
    levels_unbound = "levels_unbound"  # These are percentage levels with no maximum value.
    # I assume this is due to overprovisioning of virtual filesystems, see netapp_volumes
    show_levels = "show_levels"  # TODO: deprecate
    magic_factor = "magic_factor"
    reserved = "reserved"
    inodes = "inodes"
    size_trend = "size_trend"
    volume_name = "volume_name"


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


def _get_free_used_dynamic_valuespec(
    level_perspective: Literal["used", "free"],
    default_value=(80.0, 90.0),
    *,
    maxvalue: Union[None, float],
) -> ValueSpec:
    if level_perspective == "used":
        title = _("used space")
        course = _("above")

    else:
        title = _("free space")
        course = _("below")

    vs_subgroup: List[ValueSpec] = [
        Tuple(
            title=_("Percentage"),
            elements=[
                Percentage(
                    title=_("Warning if %s") % course,
                    unit="%",
                    minvalue=0.0 if level_perspective == "used" else 0.0001,
                    maxvalue=maxvalue,
                ),
                Percentage(
                    title=_("Critical if %s") % course,
                    unit="%",
                    minvalue=0.0 if level_perspective == "used" else 0.0001,
                    maxvalue=maxvalue,
                ),
            ],
        ),
        Tuple(
            title=_("Absolute"),
            elements=[
                Integer(
                    title=_("Warning if %s") % course,
                    unit=_("MB"),
                    minvalue=0 if level_perspective == "used" else 1,
                ),
                Integer(
                    title=_("Critical if %s") % course,
                    unit=_("MB"),
                    minvalue=0 if level_perspective == "used" else 1,
                ),
            ],
        ),
    ]

    def validate_dynamic_levels(value, varprefix):
        if [v for v in value if v[0] < 0]:
            raise MKUserError(varprefix, _("You need to specify levels of at least 0 bytes."))

    return Alternative(
        title=_("Levels for %s") % title,
        show_alternative_title=True,
        default_value=default_value,
        elements=vs_subgroup
        + [
            ListOf(
                valuespec=Tuple(
                    orientation="horizontal",
                    elements=[
                        Filesize(title=_("Systems larger than")),
                        Alternative(elements=vs_subgroup),
                    ],
                ),
                title=_("Dynamic levels"),
                allow_empty=False,
                validate=validate_dynamic_levels,
            )
        ],
    )


def _tuple_convert(val: tuple[float, ...]) -> tuple[float, ...]:
    return tuple(-x for x in val)


def _transform_filesystem_free(value):

    if isinstance(value, tuple):
        return _tuple_convert(value)

    result = []
    for item in value:
        result.append((item[0], _tuple_convert(item[1])))
    return result


def _filesystem_levels_elements(maxvalue: Optional[float] = 101.0) -> List[DictionaryEntry]:
    return [
        (
            "levels",
            Alternative(
                title=_("Levels for used/free space"),
                show_alternative_title=True,
                default_value=(80.0, 90.0),
                match=match_dual_level_type,
                elements=[
                    _get_free_used_dynamic_valuespec("used", maxvalue=maxvalue),
                    Transform(
                        valuespec=_get_free_used_dynamic_valuespec(
                            "free",
                            default_value=(20.0, 10.0),
                            maxvalue=maxvalue,
                        ),
                        title=_("Levels for free space"),
                        forth=_transform_filesystem_free,
                        back=_transform_filesystem_free,
                    ),
                ],
            ),
        ),
    ]


def _filesystem_levels_elements_bound() -> List[DictionaryEntry]:
    return _filesystem_levels_elements()


def _filesystem_levels_elements_unbound() -> List[DictionaryEntry]:
    return _filesystem_levels_elements(maxvalue=None)


def _filesystem_show_levels_elements() -> List[DictionaryEntry]:
    return [
        (
            "show_levels",
            DropdownChoice(
                title=_("Display warn/crit levels in check output..."),
                choices=[
                    ("onproblem", _("Only if the status is non-OK")),
                    ("onmagic", _("If the status is non-OK or a magic factor is set")),
                    ("always", _("Always")),
                ],
                default_value="onmagic",
            ),
        ),
    ]


# Note: This hack is only required on very old filesystem checks (prior August 2013)
def _filesystem_levels_elements_hack() -> List[DictionaryEntry]:
    return [
        # Beware: this is a nasty hack that helps us to detect new-style parameters.
        # Something hat has todo with float/int conversion and has not been documented
        # by the one who implemented this.
        (
            "flex_levels",
            FixedValue(
                value=None,
                totext="",
                title="",
            ),
        ),
    ]


def _filesystem_reserved_elements() -> List[DictionaryEntry]:
    return [
        (
            "show_reserved",
            DropdownChoice(
                title=_("Show space reserved for the <tt>root</tt> user"),
                help=_(
                    "Check_MK treats space that is reserved for the <tt>root</tt> user on Linux and Unix as "
                    "used space. Usually, 5% are being reserved for root when a new filesystem is being created. "
                    "With this option you can have Check_MK display the current amount of reserved but yet unused "
                    "space."
                ),
                choices=[
                    (True, _("Show reserved space")),
                    (False, _("Do now show reserved space")),
                ],
            ),
        ),
        (
            "subtract_reserved",
            DropdownChoice(
                title=_(
                    "Exclude space reserved for the <tt>root</tt> user from calculation of used space"
                ),
                help=_(
                    "By default Check_MK treats space that is reserved for the <tt>root</tt> user on Linux and Unix as "
                    "used space. Usually, 5% are being reserved for root when a new filesystem is being created. "
                    "With this option you can have Check_MK exclude the current amount of reserved but yet unused "
                    "space from the calculations regarding the used space percentage."
                ),
                choices=[
                    (False, _("Include reserved space")),
                    (True, _("Exclude reserved space")),
                ],
            ),
        ),
    ]


def _filesystem_volume_name() -> List[DictionaryEntry]:
    return [
        (
            "show_volume_name",
            Checkbox(
                title=_("Show volume name in service output"),
                label="Enable",
                default_value=False,
            ),
        ),
    ]


def _filesystem_inodes_elements() -> List[DictionaryEntry]:
    return [
        (
            "inodes_levels",
            Alternative(
                title=_("Levels for Inodes"),
                help=_(
                    "The number of remaining inodes on the filesystem. "
                    "Please note that this setting has no effect on some filesystem checks."
                ),
                elements=[
                    Tuple(
                        title=_("Percentage free"),
                        elements=[
                            Percentage(title=_("Warning if less than")),
                            Percentage(title=_("Critical if less than")),
                        ],
                    ),
                    Tuple(
                        title=_("Absolute free"),
                        elements=[
                            Integer(
                                title=_("Warning if less than"),
                                size=10,
                                unit=_("inodes"),
                                minvalue=0,
                                default_value=10000,
                            ),
                            Integer(
                                title=_("Critical if less than"),
                                size=10,
                                unit=_("inodes"),
                                minvalue=0,
                                default_value=5000,
                            ),
                        ],
                    ),
                    FixedValue(
                        value=None,
                        totext="",
                        title=_("Ignore levels"),
                    ),
                ],
                default_value=(10.0, 5.0),
            ),
        ),
        (
            "show_inodes",
            DropdownChoice(
                title=_("Display inode usage in check output..."),
                choices=[
                    ("onproblem", _("Only in case of a problem")),
                    ("onlow", _("Only in case of a problem or if inodes are below 50%")),
                    ("always", _("Always")),
                ],
                default_value="onlow",
            ),
        ),
    ]


def _filesystem_magic_elements() -> List[DictionaryEntry]:
    return [
        (
            "magic",
            Float(
                title=_("Magic factor (automatic level adaptation for large filesystems)"),
                default_value=0.8,
                minvalue=0.1,
                maxvalue=1.0,
            ),
        ),
        (
            "magic_normsize",
            Integer(
                title=_("Reference size for magic factor"),
                default_value=20,
                minvalue=1,
                unit=_("GB"),
            ),
        ),
        (
            "levels_low",
            Tuple(
                title=_("Minimum levels if using magic factor"),
                help=_(
                    "The filesystem levels will never fall below these values, when using "
                    "the magic factor and the filesystem is very small."
                ),
                elements=[
                    Percentage(
                        title=_("Warning at"),
                        # xgettext: no-python-format
                        unit=_("% usage"),
                        allow_int=True,
                        default_value=50,
                    ),
                    Percentage(
                        title=_("Critical at"),
                        # xgettext: no-python-format
                        unit=_("% usage"),
                        allow_int=True,
                        default_value=60,
                    ),
                ],
            ),
        ),
    ]


def size_trend_elements() -> List[DictionaryEntry]:
    return [
        (
            "trend_range",
            Integer(
                title=_("Time Range for trend computation"),
                default_value=24,
                minvalue=1,
                unit=_("hours"),
            ),
        ),
        (
            "trend_bytes",
            Tuple(
                title=_("Levels on trends per time range"),
                elements=[
                    Filesize(title=_("Warning at"), default_value=100 * 1024**2),
                    Filesize(title=_("Critical at"), default_value=200 * 1024**2),
                ],
            ),
        ),
        (
            "trend_perc",
            Tuple(
                title=_("Levels for the percentual growth per time range"),
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
                ],
            ),
        ),
        (
            "trend_shrinking_bytes",
            Tuple(
                title=_("Levels on decreasing trends in MB per time range"),
                elements=[
                    Filesize(title=_("Warning at"), default_value=1 * 1024**3),
                    Filesize(title=_("Critical at"), default_value=4 * 1024**3),
                ],
            ),
        ),
        (
            "trend_shrinking_perc",
            Tuple(
                title=_("Levels for the percentual shrinking per time range"),
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
                ],
            ),
        ),
        (
            "trend_timeleft",
            Tuple(
                title=_("Levels on the time left until full"),
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
                ],
            ),
        ),
        (
            "trend_showtimeleft",
            Checkbox(
                title=_("Display time left in check output"),
                label=_("Enable"),
                help=_(
                    "Normally, the time left until the disk is full is only displayed when "
                    "the configured levels have been breached. If you set this option "
                    "the check always reports this information"
                ),
            ),
        ),
        (
            "trend_perfdata",
            Checkbox(
                title=_("Trend performance data"),
                label=_("Enable generation of performance data from trends"),
            ),
        ),
    ]


FILESYSTEM_ELEMENTS_SELECTOR: Mapping[FilesystemElements, Callable[[], List[DictionaryEntry]]] = {
    FilesystemElements.levels: _filesystem_levels_elements_bound,
    FilesystemElements.levels_unbound: _filesystem_levels_elements_unbound,
    FilesystemElements.show_levels: _filesystem_show_levels_elements,
    FilesystemElements.reserved: _filesystem_reserved_elements,
    FilesystemElements.volume_name: _filesystem_volume_name,
    FilesystemElements.inodes: _filesystem_inodes_elements,
    FilesystemElements.magic_factor: _filesystem_magic_elements,
    FilesystemElements.size_trend: size_trend_elements,
}


def vs_filesystem(
    *,
    elements: Optional[Sequence[FilesystemElements]] = None,
    extra_elements: Optional[List[DictionaryEntry]] = None,
    ignored_keys: Optional[Sequence[str]] = None,
) -> Dictionary:

    if extra_elements is None:
        extra_elements = []

    if elements is None:
        elements = [
            FilesystemElements.levels,
            FilesystemElements.show_levels,
            FilesystemElements.magic_factor,
            FilesystemElements.reserved,
            FilesystemElements.inodes,
            FilesystemElements.size_trend,
            FilesystemElements.volume_name,
        ]
        # some hack, see corresponding valuespec element definition
        extra_elements += _filesystem_levels_elements_hack()

    dictionary_valuespec_elements = [
        elem  #
        for elems in [FILESYSTEM_ELEMENTS_SELECTOR[e]() for e in elements]  #
        for elem in elems
    ] + extra_elements

    if ignored_keys is None:
        ignored_keys = [
            "patterns",
            "include_volume_name",
            "item_appearance",
            "grouping_behaviour",
            "mountpoint_for_block_devices",
        ]

    return Dictionary(
        elements=dictionary_valuespec_elements,
        hidden_keys=[
            # some hack, see corresponding valuespec element definition
            "flex_levels"
        ],
        ignored_keys=ignored_keys,
    )
