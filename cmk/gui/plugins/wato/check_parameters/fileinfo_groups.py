#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Mapping
from typing import cast

from cmk.gui.plugins.wato.check_parameters.fileinfo_utils import (
    get_fileinfo_negative_age_tolerance_element,
)
from cmk.rulesets.v1 import Help, Label, Title
from cmk.rulesets.v1.form_specs import (
    CascadingSingleChoice,
    CascadingSingleChoiceElement,
    DataSize,
    DefaultValue,
    DictElement,
    Dictionary,
    FieldSize,
    InputHint,
    Integer,
    LevelDirection,
    LevelsType,
    List,
    MatchingScope,
    migrate_to_float_simple_levels,
    migrate_to_integer_simple_levels,
    RegularExpression,
    ServiceState,
    SIMagnitude,
    SimpleLevels,
    String,
    TimeMagnitude,
    TimeSpan,
)
from cmk.rulesets.v1.rule_specs import (
    CheckParameters,
    DiscoveryParameters,
    EnforcedService,
    HostAndItemCondition,
    Topic,
)

DISPLAYED_MAGNITUDES_TIME = [
    TimeMagnitude.DAY,
    TimeMagnitude.HOUR,
    TimeMagnitude.MINUTE,
    TimeMagnitude.SECOND,
]

DISPLAYED_MAGNITUDES_DATA = [
    SIMagnitude.BYTE,
    SIMagnitude.KILO,
    SIMagnitude.MEGA,
    SIMagnitude.GIGA,
    SIMagnitude.TERA,
]


def _get_fileinfo_groups_help():
    return Help(
        "Checks <tt>fileinfo</tt> and <tt>sap_hana_fileinfo</tt> monitor "
        "the age and size of a single file. Each file information that is sent "
        "by the agent will create one service. By defining grouping "
        "patterns you can switch to checks <tt>fileinfo.groups</tt> or "
        "<tt>sap_hana_fileinfo.groups</tt>. These checks monitor a list of files at once. "
        "You can set levels not only for the total size and the age of the oldest/youngest "
        "file but also on the count. You can define one or several "
        "patterns for a group containing <tt>*</tt> and <tt>?</tt>, for example "
        "<tt>/var/log/apache/*.log</tt>. Please see Python's fnmatch for more "
        "information regarding globbing patterns and special characters. "
        "If the pattern begins with a tilde then this pattern is interpreted as "
        "a regular expression instead of as a filename globbing pattern and "
        "<tt>*</tt> and <tt>?</tt> are treated differently. "
        "For files contained in a group "
        "the discovery will automatically create a group service instead "
        "of single services for each file. This rule also applies when "
        "you use manually configured checks instead of inventorized ones. "
        "Furthermore, the current time/date in a configurable format "
        "may be included in the include pattern. The syntax is as follows: "
        "$DATE:format-spec$ or $YESTERDAY:format-spec$, where format-spec "
        "is a list of time format directives of the unix date command. "
        "Example: $DATE:%Y%m%d$ is todays date, e.g. 20140127. A pattern "
        "of /var/tmp/backups/$DATE:%Y%m%d$.txt would search for .txt files "
        "with todays date  as name in the directory /var/tmp/backups. "
        "The YESTERDAY syntax simply subtracts one day from the reference time."
    )


def _migrate_conjunctions(conjunction: object) -> Mapping[str, object]:
    """
    Migrate the conjunctions from a tuple to a dictionary format.

    >>> _migrate_conjunctions(("CRIT", ["count", "size"]))
    {'monitoring_state': 'CRIT', 'configs': ['count', 'size']}
    >>> _migrate_conjunctions({"monitoring_state": "CRIT", "configs": ["count", "size"]})
    {'monitoring_state': 'CRIT', 'configs': ['count', 'size']}
    """
    if isinstance(conjunction, tuple):
        return {"monitoring_state": conjunction[0], "configs": conjunction[1]}
    return cast(Mapping[str, object], conjunction)


def _migrate_group_patterns(group_pattern: object) -> Mapping[str, object]:
    """
    Migrate the group patterns from a tuple to a dictionary format.

    >>> _migrate_group_patterns(("include_pattern", "exclude_pattern"))
    {'group_pattern_include': 'include_pattern', 'group_pattern_exclude': 'exclude_pattern'}
    >>> _migrate_group_patterns({"group_pattern_include": "include_pattern", "group_pattern_exclude": "exclude_pattern"})
    {'group_pattern_include': 'include_pattern', 'group_pattern_exclude': 'exclude_pattern'}
    """
    if isinstance(group_pattern, tuple):
        return {
            "group_pattern_include": group_pattern[0],
            "group_pattern_exclude": group_pattern[1],
        }
    return cast(Mapping[str, object], group_pattern)


def _valuespec_fileinfo_groups() -> Dictionary:
    return Dictionary(
        title=Title("File grouping patterns"),
        elements={
            "group_patterns": DictElement(
                required=False,
                parameter_form=List(
                    element_template=Dictionary(
                        help_text=Help("This defines one file grouping pattern."),
                        elements={
                            "group_name": DictElement(
                                required=True,
                                parameter_form=String(
                                    title=Title("Name of group"), field_size=FieldSize.MEDIUM
                                ),
                            ),
                            "pattern_configs": DictElement(
                                required=True,
                                parameter_form=Dictionary(
                                    elements={
                                        "include_pattern": DictElement(
                                            required=True,
                                            parameter_form=RegularExpression(
                                                predefined_help_text=MatchingScope.PREFIX,
                                                title=Title("Include Pattern"),
                                            ),
                                        ),
                                        "exclude_pattern": DictElement(
                                            required=True,
                                            parameter_form=RegularExpression(
                                                predefined_help_text=MatchingScope.FULL,
                                                title=Title("Exclude Pattern"),
                                            ),
                                        ),
                                    },
                                ),
                            ),
                        },
                    ),
                    title=Title("Group patterns"),
                    help_text=_get_fileinfo_groups_help(),
                    add_element_label=Label("Add pattern group"),
                ),
            )
        },
    )


rule_spec_fileinfo_groups = DiscoveryParameters(
    name="fileinfo_groups",
    topic=Topic.STORAGE,
    parameter_form=_valuespec_fileinfo_groups,
    title=Title("Size, age and count of file groups"),
)


def _item_spec_fileinfo_groups():
    return String(
        title=Title("File Group Name"),
        help_text=Help(
            "This name must match the name of the group defined "
            'in the <a href="wato.py?mode=edit_ruleset&varname=fileinfo_groups">%s</a> ruleset.'
        )
        % Help("File Grouping Patterns"),
    )


def get_fileinfo_groups_parameter_form(is_enforced: bool = False) -> Dictionary:
    """
    Returns the parameter form for fileinfo groups checking.
    """
    return Dictionary(
        elements={
            "group_patterns": DictElement(
                required=is_enforced,
                render_only=not is_enforced,
                parameter_form=List(
                    title=Title("Group patterns") if is_enforced else None,
                    help_text=_get_fileinfo_groups_help(),
                    add_element_label=Label("Add pattern group"),
                    element_template=Dictionary(
                        migrate=_migrate_group_patterns,
                        help_text=Help("This defines one file grouping pattern."),
                        elements={
                            "group_pattern_include": DictElement(
                                required=True,
                                parameter_form=RegularExpression(
                                    predefined_help_text=MatchingScope.PREFIX,
                                    title=Title("Include Pattern"),
                                ),
                            ),
                            "group_pattern_exclude": DictElement(
                                required=True,
                                parameter_form=RegularExpression(
                                    predefined_help_text=MatchingScope.FULL,
                                    title=Title("Exclude Pattern"),
                                ),
                            ),
                        },
                    ),
                ),
            ),
            "minage_oldest": DictElement(
                required=False,
                parameter_form=SimpleLevels(
                    title=Title("Minimal age of oldest file"),
                    level_direction=LevelDirection.LOWER,
                    prefill_levels_type=DefaultValue(LevelsType.FIXED),
                    prefill_fixed_levels=InputHint((0, 0)),
                    migrate=migrate_to_float_simple_levels,
                    form_spec_template=TimeSpan(
                        displayed_magnitudes=DISPLAYED_MAGNITUDES_TIME,
                    ),
                ),
            ),
            "maxage_oldest": DictElement(
                required=False,
                parameter_form=SimpleLevels(
                    title=Title("Maximal age of oldest file"),
                    level_direction=LevelDirection.UPPER,
                    prefill_levels_type=DefaultValue(LevelsType.FIXED),
                    prefill_fixed_levels=InputHint((0, 0)),
                    migrate=migrate_to_float_simple_levels,
                    form_spec_template=TimeSpan(
                        displayed_magnitudes=DISPLAYED_MAGNITUDES_TIME,
                    ),
                ),
            ),
            "minage_newest": DictElement(
                required=False,
                parameter_form=SimpleLevels(
                    title=Title("Minimal age of newest file"),
                    level_direction=LevelDirection.LOWER,
                    prefill_levels_type=DefaultValue(LevelsType.FIXED),
                    prefill_fixed_levels=InputHint((0, 0)),
                    migrate=migrate_to_float_simple_levels,
                    form_spec_template=TimeSpan(
                        displayed_magnitudes=DISPLAYED_MAGNITUDES_TIME,
                    ),
                ),
            ),
            "maxage_newest": DictElement(
                required=False,
                parameter_form=SimpleLevels(
                    title=Title("Maximal age of newest file"),
                    level_direction=LevelDirection.UPPER,
                    prefill_levels_type=DefaultValue(LevelsType.FIXED),
                    prefill_fixed_levels=InputHint((0, 0)),
                    migrate=migrate_to_float_simple_levels,
                    form_spec_template=TimeSpan(
                        displayed_magnitudes=DISPLAYED_MAGNITUDES_TIME,
                    ),
                ),
            ),
            "minsize_smallest": DictElement(
                required=False,
                parameter_form=SimpleLevels(
                    title=Title("Minimal size of smallest file"),
                    level_direction=LevelDirection.LOWER,
                    prefill_levels_type=DefaultValue(LevelsType.FIXED),
                    prefill_fixed_levels=InputHint((0, 0)),
                    migrate=migrate_to_integer_simple_levels,
                    form_spec_template=DataSize(
                        displayed_magnitudes=DISPLAYED_MAGNITUDES_DATA,
                    ),
                ),
            ),
            "maxsize_smallest": DictElement(
                required=False,
                parameter_form=SimpleLevels(
                    title=Title("Maximal size of smallest file"),
                    level_direction=LevelDirection.UPPER,
                    prefill_levels_type=DefaultValue(LevelsType.FIXED),
                    prefill_fixed_levels=InputHint((0, 0)),
                    migrate=migrate_to_integer_simple_levels,
                    form_spec_template=DataSize(
                        displayed_magnitudes=DISPLAYED_MAGNITUDES_DATA,
                    ),
                ),
            ),
            "minsize_largest": DictElement(
                required=False,
                parameter_form=SimpleLevels(
                    title=Title("Minimal size of largest file"),
                    level_direction=LevelDirection.LOWER,
                    prefill_levels_type=DefaultValue(LevelsType.FIXED),
                    prefill_fixed_levels=InputHint((0, 0)),
                    migrate=migrate_to_integer_simple_levels,
                    form_spec_template=DataSize(
                        displayed_magnitudes=DISPLAYED_MAGNITUDES_DATA,
                    ),
                ),
            ),
            "maxsize_largest": DictElement(
                required=False,
                parameter_form=SimpleLevels(
                    title=Title("Maximal size of largest file"),
                    level_direction=LevelDirection.UPPER,
                    prefill_levels_type=DefaultValue(LevelsType.FIXED),
                    prefill_fixed_levels=InputHint((0, 0)),
                    migrate=migrate_to_integer_simple_levels,
                    form_spec_template=DataSize(
                        displayed_magnitudes=DISPLAYED_MAGNITUDES_DATA,
                    ),
                ),
            ),
            "minsize": DictElement(
                required=False,
                parameter_form=SimpleLevels(
                    title=Title("Minimal size"),
                    level_direction=LevelDirection.LOWER,
                    prefill_levels_type=DefaultValue(LevelsType.FIXED),
                    prefill_fixed_levels=InputHint((0, 0)),
                    migrate=migrate_to_integer_simple_levels,
                    form_spec_template=DataSize(
                        displayed_magnitudes=DISPLAYED_MAGNITUDES_DATA,
                    ),
                ),
            ),
            "maxsize": DictElement(
                required=False,
                parameter_form=SimpleLevels(
                    title=Title("Maximal size"),
                    level_direction=LevelDirection.UPPER,
                    prefill_levels_type=DefaultValue(LevelsType.FIXED),
                    prefill_fixed_levels=InputHint((0, 0)),
                    migrate=migrate_to_integer_simple_levels,
                    form_spec_template=DataSize(
                        displayed_magnitudes=DISPLAYED_MAGNITUDES_DATA,
                    ),
                ),
            ),
            "mincount": DictElement(
                required=False,
                parameter_form=SimpleLevels(
                    title=Title("Minimal file count"),
                    level_direction=LevelDirection.LOWER,
                    prefill_levels_type=DefaultValue(LevelsType.FIXED),
                    prefill_fixed_levels=InputHint((0, 0)),
                    migrate=migrate_to_integer_simple_levels,
                    form_spec_template=Integer(),
                ),
            ),
            "maxcount": DictElement(
                required=False,
                parameter_form=SimpleLevels(
                    title=Title("Maximal file count"),
                    level_direction=LevelDirection.UPPER,
                    prefill_levels_type=DefaultValue(LevelsType.FIXED),
                    prefill_fixed_levels=InputHint((0, 0)),
                    migrate=migrate_to_integer_simple_levels,
                    form_spec_template=Integer(),
                ),
            ),
            "conjunctions": DictElement(
                required=False,
                parameter_form=List(
                    element_template=Dictionary(
                        migrate=_migrate_conjunctions,
                        elements={
                            "monitoring_state": DictElement(
                                required=True,
                                parameter_form=ServiceState(
                                    title=Title("Monitoring state"),
                                    prefill=DefaultValue(ServiceState.CRIT),
                                ),
                            ),
                            "configs": DictElement(
                                required=True,
                                parameter_form=List(
                                    element_template=CascadingSingleChoice(
                                        elements=[
                                            CascadingSingleChoiceElement(
                                                name="count",
                                                title=Title("File count at"),
                                                parameter_form=Integer(),
                                            ),
                                            CascadingSingleChoiceElement(
                                                name="count_lower",
                                                title=Title("File count below"),
                                                parameter_form=Integer(),
                                            ),
                                            CascadingSingleChoiceElement(
                                                name="size",
                                                title=Title("File size at"),
                                                parameter_form=DataSize(
                                                    displayed_magnitudes=DISPLAYED_MAGNITUDES_DATA,
                                                ),
                                            ),
                                            CascadingSingleChoiceElement(
                                                name="size_lower",
                                                title=Title("File size below"),
                                                parameter_form=DataSize(
                                                    displayed_magnitudes=DISPLAYED_MAGNITUDES_DATA,
                                                ),
                                            ),
                                            CascadingSingleChoiceElement(
                                                name="size_largest",
                                                title=Title("Largest file size at"),
                                                parameter_form=DataSize(
                                                    displayed_magnitudes=DISPLAYED_MAGNITUDES_DATA,
                                                ),
                                            ),
                                            CascadingSingleChoiceElement(
                                                name="size_largest_lower",
                                                title=Title("Largest file size below"),
                                                parameter_form=DataSize(
                                                    displayed_magnitudes=DISPLAYED_MAGNITUDES_DATA,
                                                ),
                                            ),
                                            CascadingSingleChoiceElement(
                                                name="size_smallest",
                                                title=Title("Smallest file size at"),
                                                parameter_form=DataSize(
                                                    displayed_magnitudes=DISPLAYED_MAGNITUDES_DATA,
                                                ),
                                            ),
                                            CascadingSingleChoiceElement(
                                                name="size_smallest_lower",
                                                title=Title("Smallest file size below"),
                                                parameter_form=DataSize(
                                                    displayed_magnitudes=DISPLAYED_MAGNITUDES_DATA,
                                                ),
                                            ),
                                            CascadingSingleChoiceElement(
                                                name="age_oldest",
                                                title=Title("Oldest file age at"),
                                                parameter_form=TimeSpan(
                                                    displayed_magnitudes=DISPLAYED_MAGNITUDES_TIME,
                                                    migrate=float,  # type: ignore[arg-type] # wrong type, right behaviour
                                                ),
                                            ),
                                            CascadingSingleChoiceElement(
                                                name="age_oldest_lower",
                                                title=Title("Oldest file age below"),
                                                parameter_form=TimeSpan(
                                                    displayed_magnitudes=DISPLAYED_MAGNITUDES_TIME,
                                                    migrate=float,  # type: ignore[arg-type] # wrong type, right behaviour
                                                ),
                                            ),
                                            CascadingSingleChoiceElement(
                                                name="age_newest",
                                                title=Title("Newest file age at"),
                                                parameter_form=TimeSpan(
                                                    displayed_magnitudes=DISPLAYED_MAGNITUDES_TIME,
                                                    migrate=float,  # type: ignore[arg-type] # wrong type, right behaviour
                                                ),
                                            ),
                                            CascadingSingleChoiceElement(
                                                name="age_newest_lower",
                                                title=Title("Newest file age below"),
                                                parameter_form=TimeSpan(
                                                    displayed_magnitudes=DISPLAYED_MAGNITUDES_TIME,
                                                    migrate=float,  # type: ignore[arg-type] # wrong type, right behaviour
                                                ),
                                            ),
                                        ],
                                    ),
                                ),
                            ),
                        },
                    ),
                    title=Title("Level conjunctions"),
                    help_text=Help(
                        "In order to check dependent file group statistics you can configure "
                        "conjunctions of single levels now. A conjunction consists of a monitoring state "
                        "and any number of upper or lower levels. If all of the configured levels within "
                        "a conjunction are reached then the related state is reported."
                    ),
                ),
            ),
            "negative_age_tolerance": get_fileinfo_negative_age_tolerance_element(),
        },
    )


rule_spec_fileinfo_groups_checking = CheckParameters(
    name="fileinfo_groups_checking",
    title=Title("Size, age and count of file groups"),
    topic=Topic.STORAGE,
    parameter_form=get_fileinfo_groups_parameter_form,
    condition=HostAndItemCondition(
        item_form=_item_spec_fileinfo_groups(),
        item_title=Title("File Group Name"),
    ),
    create_enforced_service=False,
)


rule_spec_fileinfo_groups_enforced = EnforcedService(
    name="fileinfo_groups_checking",
    title=Title("Size, age and count of file groups"),
    topic=Topic.STORAGE,
    parameter_form=lambda: get_fileinfo_groups_parameter_form(is_enforced=True),
    condition=HostAndItemCondition(
        item_form=_item_spec_fileinfo_groups(),
        item_title=Title("File Group Name"),
    ),
)
