#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Module to hold shared code for filesystem check parameter module internals"""

from collections.abc import Callable, Mapping, MutableMapping, Sequence
from enum import Enum
from typing import Any, Literal

from cmk.gui.form_specs.generators.alternative_utils import enable_deprecated_alternative
from cmk.gui.form_specs.generators.tuple_utils import TupleLevels
from cmk.gui.form_specs.unstable import (
    SingleChoiceElementExtended,
    SingleChoiceExtended,
)
from cmk.gui.form_specs.unstable.legacy_converter import (
    TransformDataForLegacyFormatOrRecomposeFunction,
    Tuple,
)
from cmk.gui.i18n import _
from cmk.rulesets.v1 import Help, Label, Message, Title
from cmk.rulesets.v1.form_specs import (
    BooleanChoice,
    CascadingSingleChoice,
    CascadingSingleChoiceElement,
    DataSize,
    DefaultValue,
    DictElement,
    Dictionary,
    FixedValue,
    Float,
    IECMagnitude,
    Integer,
    List,
    Percentage,
    SingleChoice,
    SingleChoiceElement,
    validators,
)
from cmk.rulesets.v1.form_specs.validators import ValidationError

ParamType = Mapping[str, Any]
MutableParamType = MutableMapping[str, Any]


class FilesystemElements(Enum):
    levels = "levels"
    levels_percent = "levels_percent"  # sansymphony_pool
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
# In the dynamic case, the levels are stores in a list where the second element
# represents the levels and the conditions above apply.
def _match_dual_level_type(value):
    if isinstance(value, list):
        for entry in value:
            if entry[1][0] < 0 or entry[1][1] < 0:
                return 1
        return 0
    if value[0] < 0 or value[1] < 0:
        return 1
    return 0


def _get_free_used_dynamic_form_spec(
    level_perspective: Literal["used", "free"],
    percentage_levels: tuple[float, float],
    *,
    do_include_absolutes: bool = True,
) -> TransformDataForLegacyFormatOrRecomposeFunction:
    if level_perspective == "used":
        title = _("used space")
        course = _("above")
    else:
        title = _("free space")
        course = _("below")

    vs_subgroup: list[CascadingSingleChoiceElement] = [
        CascadingSingleChoiceElement(
            name="alternative_percentage",
            title=Title("Percentage"),
            parameter_form=TupleLevels(
                elements=[
                    Percentage(
                        title=Title("Warning if %s") % course,
                        custom_validate=[
                            validators.NumberInRange(
                                min_value=0.0 if level_perspective == "used" else 0.0001,
                                error_msg=Message("Percentage field can not be empty"),
                            )
                        ],
                        prefill=DefaultValue(percentage_levels[0]),
                    ),
                    Percentage(
                        title=Title("Critical if %s") % course,
                        custom_validate=[
                            validators.NumberInRange(
                                min_value=0.0 if level_perspective == "used" else 0.0001,
                                error_msg=Message("Percentage field can not be empty"),
                            )
                        ],
                        prefill=DefaultValue(percentage_levels[1]),
                    ),
                ],
            ),
        )
    ]
    if do_include_absolutes is True:
        vs_subgroup.append(
            CascadingSingleChoiceElement(
                name="alternative_absolute",
                title=Title("Absolute"),
                parameter_form=TupleLevels(
                    elements=[
                        Integer(
                            title=Title("Warning if %s") % course,
                            unit_symbol="MB",
                            custom_validate=[
                                validators.NumberInRange(
                                    min_value=0 if level_perspective == "used" else 1,
                                    error_msg=Message("Integer field can not be empty"),
                                )
                            ],
                        ),
                        Integer(
                            title=Title("Critical if %s") % course,
                            unit_symbol="MB",
                            custom_validate=[
                                validators.NumberInRange(
                                    min_value=0 if level_perspective == "used" else 1,
                                    error_msg=Message("Integer field can not be empty"),
                                )
                            ],
                        ),
                    ],
                ),
            )
        )

    def validate_dynamic_levels(value: object) -> None:
        assert isinstance(value, list | tuple)
        if [v for v in value if v[0] < 0]:
            raise ValidationError(
                message=Message("You need to specify levels of at least 0 bytes.")
            )

    return enable_deprecated_alternative(
        wrapped_form_spec=CascadingSingleChoice(
            title=Title("Levels for %s") % title,
            prefill=DefaultValue("alternative_percentage"),
            elements=vs_subgroup
            + [
                CascadingSingleChoiceElement(
                    name="alternative_dynamic",
                    title=Title("Dynamic levels"),
                    parameter_form=List(
                        element_template=Tuple(
                            layout="horizontal",
                            elements=[
                                DataSize(
                                    title=Title("Systems larger than"),
                                    displayed_magnitudes=(
                                        IECMagnitude.BYTE,
                                        IECMagnitude.KIBI,
                                        IECMagnitude.MEBI,
                                        IECMagnitude.GIBI,
                                        IECMagnitude.TEBI,
                                    ),
                                ),
                                enable_deprecated_alternative(
                                    wrapped_form_spec=CascadingSingleChoice(elements=vs_subgroup)
                                ),
                            ],
                        ),
                        custom_validate=[
                            validators.LengthInRange(
                                min_value=1, error_msg=Message("Select at least one element")
                            ),
                            validate_dynamic_levels,
                        ],
                    ),
                )
            ],
        )
    )


def _tuple_convert(val: tuple[float, ...]) -> tuple[float, ...]:
    return tuple(-x for x in val)


def _transform_filesystem_free(value: object) -> object:
    if isinstance(value, tuple):
        return _tuple_convert(value)

    assert isinstance(value, list | tuple)
    result = []
    for item in value:
        result.append((item[0], _tuple_convert(item[1])))
    return result


def _filesystem_levels_elements(
    do_include_absolutes: bool = True,
) -> Mapping[str, DictElement]:
    return {
        "levels": DictElement(
            parameter_form=enable_deprecated_alternative(
                match_function=_match_dual_level_type,
                wrapped_form_spec=CascadingSingleChoice(
                    title=Title("Levels for used/free space"),
                    prefill=DefaultValue("alternative_used"),
                    elements=[
                        CascadingSingleChoiceElement(
                            name="alternative_used",
                            title=Title("Levels for used space"),
                            parameter_form=_get_free_used_dynamic_form_spec(
                                "used",
                                percentage_levels=(80.0, 90.0),
                                do_include_absolutes=do_include_absolutes,
                            ),
                        ),
                        CascadingSingleChoiceElement(
                            name="alternative_free",
                            title=Title("Levels for free space"),
                            parameter_form=TransformDataForLegacyFormatOrRecomposeFunction(
                                wrapped_form_spec=_get_free_used_dynamic_form_spec(
                                    "free",
                                    percentage_levels=(20.0, 10.0),
                                    do_include_absolutes=do_include_absolutes,
                                ),
                                title=Title("Levels for free space"),
                                from_disk=_transform_filesystem_free,
                                to_disk=_transform_filesystem_free,
                            ),
                        ),
                    ],
                ),
            ),
        ),
    }


def _filesystem_levels_percent_only() -> Mapping[str, DictElement]:
    return _filesystem_levels_elements(do_include_absolutes=False)


def _filesystem_show_levels_elements() -> Mapping[str, DictElement]:
    return {
        "show_levels": DictElement(
            parameter_form=SingleChoice(
                title=Title("Display warn/crit levels in check output..."),
                elements=[
                    SingleChoiceElement(
                        name="onproblem", title=Title("Only if the status is non-OK")
                    ),
                    SingleChoiceElement(
                        name="onmagic",
                        title=Title("If the status is non-OK or a magic factor is set"),
                    ),
                    SingleChoiceElement(name="always", title=Title("Always")),
                ],
                prefill=DefaultValue("onmagic"),
            ),
        )
    }


def _filesystem_reserved_elements() -> Mapping[str, DictElement]:
    return {
        "show_reserved": DictElement(
            parameter_form=SingleChoiceExtended(
                title=Title("Show space reserved for the <tt>root</tt> user"),
                help_text=Help(
                    "Checkmk treats space that is reserved for the <tt>root</tt> user on Linux and Unix as "
                    "used space. Usually, 5% are being reserved for root when a new filesystem is being created. "
                    "With this option you can have Checkmk display the current amount of reserved but yet unused "
                    "space."
                ),
                elements=[
                    SingleChoiceElementExtended(name=True, title=Title("Show reserved space")),
                    SingleChoiceElementExtended(
                        name=False, title=Title("Do now show reserved space")
                    ),
                ],
            ),
        ),
        "subtract_reserved": DictElement(
            parameter_form=SingleChoiceExtended(
                title=Title(
                    "Exclude space reserved for the <tt>root</tt> user from calculation of used space"
                ),
                help_text=Help(
                    "By default Checkmk treats space that is reserved for the <tt>root</tt> user on Linux and Unix as "
                    "used space. Usually, 5% are being reserved for root when a new filesystem is being created. "
                    "With this option you can have Checkmk exclude the current amount of reserved but yet unused "
                    "space from the calculations regarding the used space percentage."
                ),
                elements=[
                    SingleChoiceElementExtended(name=False, title=Title("Include reserved space")),
                    SingleChoiceElementExtended(name=True, title=Title("Exclude reserved space")),
                ],
            ),
        ),
    }


def _filesystem_volume_name() -> Mapping[str, DictElement]:
    return {
        "show_volume_name": DictElement(
            parameter_form=BooleanChoice(
                title=Title("Show volume name in service output"),
                label=Label("Enable"),
                prefill=DefaultValue(False),
            ),
        )
    }


def _filesystem_inodes_elements() -> Mapping[str, DictElement]:
    return {
        "inodes_levels": DictElement(
            parameter_form=enable_deprecated_alternative(
                wrapped_form_spec=CascadingSingleChoice(
                    title=Title("Levels for Inodes"),
                    help_text=Help(
                        "The number of remaining inodes on the filesystem. "
                        "Please note that this setting has no effect on some filesystem checks."
                    ),
                    elements=[
                        CascadingSingleChoiceElement(
                            name="alternative_percentage_free",
                            title=Title("Percentage free"),
                            parameter_form=TupleLevels(
                                title=Title("Percentage free"),
                                elements=[
                                    Percentage(
                                        title=Title("Warning if less than"),
                                        prefill=DefaultValue(10.0),
                                    ),
                                    Percentage(
                                        title=Title("Critical if less than"),
                                        prefill=DefaultValue(5.0),
                                    ),
                                ],
                            ),
                        ),
                        CascadingSingleChoiceElement(
                            name="alternative_absolute_free",
                            title=Title("Absolute free"),
                            parameter_form=TupleLevels(
                                title=Title("Absolute free"),
                                elements=[
                                    Integer(
                                        title=Title("Warning if less than"),
                                        unit_symbol="inodes",
                                        prefill=DefaultValue(10000),
                                        custom_validate=[
                                            validators.NumberInRange(
                                                min_value=0,
                                                error_msg=Message("Integer field can not be empty"),
                                            )
                                        ],
                                    ),
                                    Integer(
                                        title=Title("Critical if less than"),
                                        unit_symbol="inodes",
                                        prefill=DefaultValue(5000),
                                        custom_validate=[
                                            validators.NumberInRange(
                                                min_value=0,
                                                error_msg=Message("Integer field can not be empty"),
                                            )
                                        ],
                                    ),
                                ],
                            ),
                        ),
                        CascadingSingleChoiceElement(
                            name="alternative_ignore",
                            title=Title("Ignore levels"),
                            parameter_form=FixedValue(
                                value=None,
                                label=Label("No levels on inodes"),
                                title=Title("Ignore levels"),
                            ),
                        ),
                    ],
                    prefill=DefaultValue("alternative_percentage_free"),
                )
            )
        ),
        "show_inodes": DictElement(
            parameter_form=SingleChoice(
                title=Title("Display inode usage in check output..."),
                elements=[
                    SingleChoiceElement(name="onproblem", title=Title("Only in case of a problem")),
                    SingleChoiceElement(
                        name="onlow",
                        title=Title("Only in case of a problem or if inodes are below 50%"),
                    ),
                    SingleChoiceElement(name="always", title=Title("Always")),
                ],
                prefill=DefaultValue("onlow"),
            ),
        ),
    }


def _filesystem_magic_elements() -> Mapping[str, DictElement]:
    return {
        "magic": DictElement(
            parameter_form=Float(
                title=Title("Magic factor (automatic level adaptation for large filesystems)"),
                prefill=DefaultValue(0.8),
                custom_validate=[
                    validators.NumberInRange(
                        min_value=0.1,
                        max_value=1.0,
                        error_msg=Message("Float field can not be empty"),
                    )
                ],
            ),
        ),
        "magic_normsize": DictElement(
            parameter_form=Integer(
                title=Title("Reference size for magic factor"),
                prefill=DefaultValue(20),
                unit_symbol="GB",
                custom_validate=[
                    validators.NumberInRange(
                        min_value=1, error_msg=Message("Integer field can not be empty")
                    )
                ],
            ),
        ),
        "levels_low": DictElement(
            parameter_form=TupleLevels(
                title=Title("Minimum levels if using magic factor"),
                help_text=Help(
                    "The filesystem levels will never fall below these values, when using "
                    "the magic factor and the filesystem is very small."
                ),
                elements=[
                    Percentage(title=Title("Warning at usage"), prefill=DefaultValue(50.0)),
                    Percentage(
                        title=Title("Critical at usage"),
                        prefill=DefaultValue(60.0),
                    ),
                ],
            ),
        ),
    }


def size_trend_elements() -> Mapping[str, DictElement]:
    return {
        "trend_range": DictElement(
            parameter_form=Integer(
                title=Title("Time Range for trend computation"),
                prefill=DefaultValue(24),
                unit_symbol="hours",
                custom_validate=[
                    validators.NumberInRange(
                        min_value=1, error_msg=Message("Integer field can not be empty")
                    )
                ],
            ),
        ),
        "trend_bytes": DictElement(
            parameter_form=TupleLevels(
                title=Title("Levels on trends per time range"),
                elements=[
                    DataSize(
                        title=Title("Warning at"),
                        displayed_magnitudes=(
                            IECMagnitude.BYTE,
                            IECMagnitude.KIBI,
                            IECMagnitude.MEBI,
                            IECMagnitude.GIBI,
                            IECMagnitude.TEBI,
                        ),
                        prefill=DefaultValue(100 * 1024**2),
                    ),
                    DataSize(
                        title=Title("Critical at"),
                        displayed_magnitudes=(
                            IECMagnitude.BYTE,
                            IECMagnitude.KIBI,
                            IECMagnitude.MEBI,
                            IECMagnitude.GIBI,
                            IECMagnitude.TEBI,
                        ),
                        prefill=DefaultValue(200 * 1024**2),
                    ),
                ],
            ),
        ),
        "trend_perc": DictElement(
            parameter_form=TupleLevels(
                title=Title("Levels for the percentual growth per time range"),
                elements=[
                    Percentage(title=Title("Warning at"), prefill=DefaultValue(5)),
                    Percentage(
                        title=Title("Critical at"),
                        prefill=DefaultValue(10.0),
                    ),
                ],
            ),
        ),
        "trend_shrinking_bytes": DictElement(
            parameter_form=TupleLevels(
                title=Title("Levels on decreasing trends in MB per time range"),
                elements=[
                    DataSize(
                        title=Title("Warning at"),
                        displayed_magnitudes=(
                            IECMagnitude.BYTE,
                            IECMagnitude.KIBI,
                            IECMagnitude.MEBI,
                            IECMagnitude.GIBI,
                            IECMagnitude.TEBI,
                        ),
                        prefill=DefaultValue(1 * 1024**3),
                    ),
                    DataSize(
                        title=Title("Critical at"),
                        displayed_magnitudes=(
                            IECMagnitude.BYTE,
                            IECMagnitude.KIBI,
                            IECMagnitude.MEBI,
                            IECMagnitude.GIBI,
                            IECMagnitude.TEBI,
                        ),
                        prefill=DefaultValue(4 * 1024**3),
                    ),
                ],
            ),
        ),
        "trend_shrinking_perc": DictElement(
            parameter_form=TupleLevels(
                title=Title("Levels for the percentual shrinking per time range"),
                elements=[
                    Percentage(title=Title("Warning at"), prefill=DefaultValue(5)),
                    Percentage(
                        title=Title("Critical at"),
                        prefill=DefaultValue(10),
                    ),
                ],
            ),
        ),
        "trend_timeleft": DictElement(
            parameter_form=TupleLevels(
                title=Title("Levels on the time left until full"),
                elements=[
                    Integer(
                        title=Title("Warning if below"),
                        unit_symbol="hours",
                        prefill=DefaultValue(12),
                    ),
                    Integer(
                        title=Title("Critical if below"),
                        unit_symbol="hours",
                        prefill=DefaultValue(6),
                    ),
                ],
            ),
        ),
        "trend_showtimeleft": DictElement(
            parameter_form=BooleanChoice(
                title=Title("Display time left in check output"),
                label=Label("Enable"),
                help_text=Help(
                    "Normally, the time left until the disk is full is only displayed when "
                    "the configured levels have been breached. If you set this option "
                    "the check always reports this information"
                ),
            ),
        ),
        "trend_perfdata": DictElement(
            parameter_form=BooleanChoice(
                title=Title("Trend performance data"),
                label=Label("Enable generation of performance data from trends"),
            ),
        ),
    }


FILESYSTEM_ELEMENTS_SELECTOR: Mapping[
    FilesystemElements, Callable[[], Mapping[str, DictElement]]
] = {
    FilesystemElements.levels: _filesystem_levels_elements,
    FilesystemElements.levels_percent: _filesystem_levels_percent_only,
    FilesystemElements.show_levels: _filesystem_show_levels_elements,
    FilesystemElements.reserved: _filesystem_reserved_elements,
    FilesystemElements.volume_name: _filesystem_volume_name,
    FilesystemElements.inodes: _filesystem_inodes_elements,
    FilesystemElements.magic_factor: _filesystem_magic_elements,
    FilesystemElements.size_trend: size_trend_elements,
}


def fs_filesystem(
    *,
    elements: Sequence[FilesystemElements] | None = None,
    extra_elements: Mapping[str, DictElement] | None = None,
    ignored_keys: Sequence[str] | None = None,
    title: Title | None = None,
) -> Dictionary:
    if extra_elements is None:
        extra_elements = {}

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

    dict_elements: dict[str, DictElement] = {}
    for element in elements:
        dict_elements.update(FILESYSTEM_ELEMENTS_SELECTOR[element]())
    dict_elements.update(extra_elements)

    if ignored_keys is None:
        ignored_keys = (
            "patterns",
            "include_volume_name",
            "item_appearance",
            "grouping_behaviour",
            "mountpoint_for_block_devices",
        )

    return Dictionary(
        title=title,
        elements=dict_elements,
        ignored_elements=tuple(ignored_keys),
    )
