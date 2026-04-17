#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence
from typing import Any

from cmk.rulesets.v1 import Help, Message, Title
from cmk.rulesets.v1.form_specs import (
    BooleanChoice,
    CascadingSingleChoice,
    CascadingSingleChoiceElement,
    DefaultValue,
    DictElement,
    Dictionary,
    FieldSize,
    FixedValue,
    List,
    MatchingScope,
    RegularExpression,
    SingleChoice,
    SingleChoiceElement,
    String,
    TimeMagnitude,
    TimeSpan,
    validators,
)
from cmk.rulesets.v1.rule_specs import AgentConfig, Topic


def _migrate_grouping_item(item: object) -> Mapping[str, object]:
    if isinstance(item, dict):
        return item
    seq = item if isinstance(item, (list, tuple)) else list(item)  # type: ignore[call-overload]
    group_name, condition = seq[0], seq[1]
    return {"group_name": group_name, "condition": condition}


def _migrate_section(section: object) -> Mapping[str, object]:
    if not isinstance(section, dict):
        raise ValueError(f"Unexpected section value: {section!r}")
    if "grouping" not in section:
        return section
    grouping = section["grouping"]
    if not isinstance(grouping, (list, tuple)):
        raise ValueError(f"Unexpected grouping value: {grouping!r}")
    return {**section, "grouping": [_migrate_grouping_item(g) for g in grouping]}


def migrate(value: object) -> Mapping[str, object]:
    if isinstance(value, dict) and "deployment" in value:
        dep = value["deployment"]
        if isinstance(dep, (tuple, list)) and dep[0] in ("sync", "cached", "do_not_deploy"):
            if "DEFAULT" in value:
                result: dict[str, object] = {
                    k if k != "DEFAULT" else "default": v for k, v in value.items()
                }
                result["default"] = _migrate_section(result["default"])
                return result
            return value
        if dep is None:
            return {"deployment": ("do_not_deploy", None)}
        result = {k if k != "DEFAULT" else "default": v for k, v in value.items()}
        result["deployment"] = ("sync", None)
        if dep == "plugin_only":
            result["deploy_config"] = False
        if "sections" in result:
            raw_sections = result["sections"]
            sections: Sequence[object] = (
                raw_sections if isinstance(raw_sections, (list, tuple)) else []
            )
            result["sections"] = [_migrate_section(s) for s in sections]
        if "default" in result:
            result["default"] = _migrate_section(result["default"])
        return result
    if value is None:
        return {"deployment": ("do_not_deploy", None)}
    raise ValueError(f"Unexpected value: {value!r}")


def _grouping_elements() -> Mapping[str, DictElement[Any]]:
    return {
        "group_name": DictElement(
            required=True,
            parameter_form=String(
                title=Title("Group name"),
                help_text=Help(
                    "The section and the group name will be included in the item name."
                    " To use the single file aggregation, add <tt>%s</tt> to the group name."
                ),
                field_size=FieldSize.LARGE,
                custom_validate=(validators.LengthInRange(min_value=1),),
            ),
        ),
        "condition": DictElement(
            required=True,
            parameter_form=CascadingSingleChoice(
                title=Title("Grouping condition"),
                elements=(
                    CascadingSingleChoiceElement(
                        name="regex",
                        title=Title("Regular expression"),
                        parameter_form=RegularExpression(
                            predefined_help_text=MatchingScope.PREFIX,
                            help_text=Help("Group files based on a regular expression pattern."),
                        ),
                    ),
                ),
                prefill=DefaultValue("regex"),
            ),
        ),
    }


def _section_filter_elements() -> Mapping[str, DictElement[Any]]:
    return {
        "input_patterns": DictElement(
            required=True,
            parameter_form=String(
                title=Title("Globbing pattern for input files"),
                help_text=Help(
                    "The plug-in will process anything that is matched by this"
                    " globbing pattern. If it's a directory, recursively"
                    " process all of its content."
                ),
                field_size=FieldSize.LARGE,
                custom_validate=(validators.LengthInRange(min_value=1),),
            ),
        ),
        "filter_regex": DictElement(
            parameter_form=String(
                title=Title("Filter files by matching regular expression"),
                help_text=Help(
                    "This will result in all files whose full file path does not match"
                    " the regular expression being dismissed."
                ),
                field_size=FieldSize.LARGE,
                custom_validate=(validators.LengthInRange(min_value=1),),
            ),
        ),
        "filter_regex_inverse": DictElement(
            parameter_form=String(
                title=Title("Filter files by not matching regular expression"),
                help_text=Help(
                    "This will result in all files whose full file path does match"
                    " the regular expression being dismissed."
                ),
                field_size=FieldSize.LARGE,
                custom_validate=(validators.LengthInRange(min_value=1),),
            ),
        ),
        "filter_size": DictElement(
            parameter_form=String(
                title=Title("Filter files by size"),
                help_text=Help(
                    "This will result in all files with sizes not matching the"
                    " specification being dismissed. Specifications are in the"
                    " format [OPERATOR][SIZE_IN_BYTES], e.g. '>=1024'."
                ),
                custom_validate=(
                    validators.MatchRegex(
                        "^[<=>]+[0-9]+$",
                        Message("Size filter specification must be of the format [OPERATOR][INT]."),
                    ),
                ),
            ),
        ),
        "filter_age": DictElement(
            parameter_form=String(
                title=Title("Filter files by age"),
                help_text=Help(
                    "This will result in all files with ages not matching the"
                    " specification being dismissed. Specifications are in the"
                    " format [OPERATOR][AGE_IN_SECONDS], e.g. '>=3600'."
                ),
                custom_validate=(
                    validators.MatchRegex(
                        "^[<=>]+[0-9]+$",
                        Message("Age filter specification must be of the format [OPERATOR][INT]."),
                    ),
                ),
            ),
        ),
        "output": DictElement(
            parameter_form=SingleChoice(
                title=Title("Output aggregation"),
                help_text=Help(
                    "Choose what kind of output data is sent to the Checkmk server: "
                    "Only count the files, only report count and extremes files (i.e. "
                    "the oldest, newest, largest and smallest), report the "
                    "full stats on all files, or send information about a single file only."
                ),
                elements=(
                    SingleChoiceElement(name="count_only", title=Title("Count only")),
                    SingleChoiceElement(name="extremes_only", title=Title("Extremes only")),
                    SingleChoiceElement(name="file_stats", title=Title("Full stats")),
                    SingleChoiceElement(name="single_file", title=Title("Single file")),
                ),
            ),
        ),
        "grouping": DictElement(
            parameter_form=List(
                title=Title("File grouping"),
                help_text=Help(
                    "Group files within a file group further into subgroups."
                    " Specify a name for the subgroup, and a condition by which"
                    " files are grouped. Files associated with a subgroup are"
                    " excluded from the main file group. One service is created for"
                    " each subgroup."
                ),
                element_template=Dictionary(elements=_grouping_elements()),
            ),
        ),
    }


def _valuespec_agent_config_mk_filestats() -> Dictionary:
    return Dictionary(
        help_text=Help(
            "The agent plug-in <tt>mk_filestats</tt> monitors a configured set"
            " of files for their number, size and age. Files are grouped according"
            " to the configured section. Also a single file can be monitored."
            " If no sections are specified, the plug-in does not produce output."
        ),
        elements={
            "deployment": DictElement(
                required=True,
                parameter_form=CascadingSingleChoice(
                    title=Title("Deployment type"),
                    elements=(
                        CascadingSingleChoiceElement(
                            name="sync",
                            title=Title("Deploy the plug-in and run it synchronously"),
                            parameter_form=FixedValue(value=None),
                        ),
                        CascadingSingleChoiceElement(
                            name="cached",
                            title=Title("Deploy the plug-in and run it asynchronously"),
                            parameter_form=TimeSpan(
                                displayed_magnitudes=(
                                    TimeMagnitude.HOUR,
                                    TimeMagnitude.MINUTE,
                                ),
                            ),
                        ),
                        CascadingSingleChoiceElement(
                            name="do_not_deploy",
                            title=Title("Do not deploy the plug-in"),
                            parameter_form=FixedValue(value=None),
                        ),
                    ),
                    prefill=DefaultValue("sync"),
                ),
            ),
            "deploy_config": DictElement(
                parameter_form=BooleanChoice(
                    title=Title("Deploy configuration file"),
                    help_text=Help(
                        "When disabled, the plug-in is deployed without its configuration file."
                        " The file <tt>/etc/check_mk/filestats.cfg</tt> must then be created"
                        " and maintained manually."
                    ),
                    prefill=DefaultValue(True),
                ),
            ),
            "sections": DictElement(
                parameter_form=List(
                    title=Title("Sections"),
                    element_template=Dictionary(
                        title=Title("Section of files to monitor"),
                        elements={
                            "name": DictElement(
                                required=True,
                                parameter_form=String(
                                    title=Title("Section name"),
                                    help_text=Help(
                                        "The section name will be included in the item name."
                                        " To use the single file aggregation, add"
                                        " <tt>%s</tt> to the section name."
                                    ),
                                ),
                            ),
                            **_section_filter_elements(),
                        },
                    ),
                ),
            ),
            "default": DictElement(
                parameter_form=Dictionary(
                    title=Title("Set default values for all sections"),
                    elements=_section_filter_elements(),
                ),
            ),
            "subgroups_delimiter": DictElement(
                parameter_form=String(
                    title=Title("Delimiter for file grouping"),
                    help_text=Help(
                        "This option is only relevant if you have file grouping enabled and you wish"
                        ' to use the character "@" in any of your subgroup names.'
                        " If this is the case, please choose any ASCII character that is NOT used in any"
                        " of your subgroup names. You can also specify a combination of characters."
                        " For information: the subgroup delimiter is used to separate the subgroup name"
                        " from the main section name in the configuration file."
                        " For example: [My Subgroup@My Main Section]."
                    ),
                    prefill=DefaultValue("@"),
                ),
            ),
        },
        migrate=migrate,
    )


rule_spec_mk_filestats = AgentConfig(
    title=Title("Count, size and age of files - mk_filestats (Linux/Solaris)"),
    name="mk_filestats",
    topic=Topic.STORAGE,
    parameter_form=_valuespec_agent_config_mk_filestats,
)
