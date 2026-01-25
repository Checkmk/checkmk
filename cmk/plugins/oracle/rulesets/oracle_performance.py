#!/usr/bin/env python3
# Copyright (C) 2014 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="type-arg"

from cmk.plugins.oracle.constants import (
    ORACLE_IO_FILES,
    ORACLE_IO_SIZES,
    ORACLE_IO_TYPES,
    ORACLE_PGA_FIELDS,
    ORACLE_SGA_FIELDS,
    ORACLE_WAITCLASSES,
)
from cmk.rulesets.v1 import Help, Label, Title
from cmk.rulesets.v1.form_specs import (
    CascadingSingleChoice,
    CascadingSingleChoiceElement,
    DataSize,
    DictElement,
    Dictionary,
    FixedValue,
    Float,
    IECMagnitude,
    InputHint,
    Integer,
    LevelDirection,
    List,
    migrate_to_float_simple_levels,
    migrate_to_integer_simple_levels,
    SimpleLevels,
)
from cmk.rulesets.v1.rule_specs import (
    CheckParameters,
    DiscoveryParameters,
    HostAndItemCondition,
    Topic,
)


def _formspec_discovery_oracle_performance() -> Dictionary:
    return Dictionary(
        title=Title("Service discovery"),
        elements={
            "dbtime": DictElement(
                required=False,
                parameter_form=FixedValue(
                    value=True,
                    title=Title("Create separate service for DB time"),
                    label=Label("Extracts DB time performance data into a separate service"),
                ),
            ),
            "memory": DictElement(
                required=False,
                parameter_form=FixedValue(
                    value=True,
                    title=Title("Create separate service for memory information"),
                    label=Label(
                        "Extracts SGA performance data into a separate service and additionally displays PGA performance data"
                    ),
                ),
            ),
            "iostat_bytes": DictElement(
                required=False,
                parameter_form=FixedValue(
                    value=True,
                    title=Title("Create additional service for IO stats bytes"),
                    label=Label(
                        "Creates a new service that displays information about disk I/O of database files. "
                        "This service displays the number of bytes read and written to database files."
                    ),
                ),
            ),
            "iostat_ios": DictElement(
                required=False,
                parameter_form=FixedValue(
                    value=True,
                    title=Title("Create additional service for IO stats requests"),
                    label=Label(
                        "Creates a new service that displays information about disk I/O of database files. "
                        "This service displays the number of single block read and write requests that are being made to database files."
                    ),
                ),
            ),
            "waitclasses": DictElement(
                required=False,
                parameter_form=FixedValue(
                    value=True,
                    title=Title("Create additional service for system wait"),
                    label=Label(
                        "Display the time an oracle instance spents inside of the different wait classes."
                    ),
                ),
            ),
        },
    )


rule_spec_oracle_performance_discovery = DiscoveryParameters(
    title=Title("Oracle performance discovery"),
    topic=Topic.DATABASES,
    parameter_form=_formspec_discovery_oracle_performance,
    name="oracle_performance_discovery",
)


_PERSEC_LEVELS = SimpleLevels(
    form_spec_template=Float(unit_symbol="1/s"),
    level_direction=LevelDirection.UPPER,
    prefill_fixed_levels=InputHint((0.0, 0.0)),
    migrate=migrate_to_float_simple_levels,
)


# FIXME: This is currently written in a way that prevents us from adding
# any localization.
def _parameter_valuespec_oracle_performance() -> Dictionary:
    # memory
    memory_choices = [
        CascadingSingleChoiceElement(
            name=ga.metric,
            title=Title(ga.name),  # astrein: disable=localization-checker
            parameter_form=SimpleLevels(
                form_spec_template=DataSize(
                    displayed_magnitudes=(
                        IECMagnitude.BYTE,
                        IECMagnitude.KIBI,
                        IECMagnitude.MEBI,
                        IECMagnitude.GIBI,
                    ),
                ),
                level_direction=LevelDirection.UPPER,
                prefill_fixed_levels=InputHint((0, 0)),
                migrate=migrate_to_integer_simple_levels,
            ),
        )
        for ga in ORACLE_SGA_FIELDS + ORACLE_PGA_FIELDS
    ]

    # iostat_bytes + iostat_ios
    iostat_bytes_choices: list[CascadingSingleChoiceElement] = []
    iostat_ios_choices: list[CascadingSingleChoiceElement] = []
    for iofile in ORACLE_IO_FILES:
        for size_code, size_text in ORACLE_IO_SIZES:
            for io_code, io_text, io_unit in ORACLE_IO_TYPES:
                target_array = iostat_bytes_choices if io_unit == "bytes/s" else iostat_ios_choices
                target_array.append(
                    CascadingSingleChoiceElement(
                        name=f"oracle_ios_f_{iofile.id}_{size_code}_{io_code}",
                        title=Title(  # astrein: disable=localization-checker
                            f" {iofile.name} {size_text} {io_text}"
                        ),
                        parameter_form=SimpleLevels(
                            form_spec_template=Integer(unit_symbol=io_unit),
                            level_direction=LevelDirection.UPPER,
                            prefill_fixed_levels=InputHint((0, 0)),
                            migrate=migrate_to_integer_simple_levels,
                        ),
                    )
                )

    # waitclasses
    waitclasses_choices = [
        ("oracle_wait_class_total", "Total waited"),
        ("oracle_wait_class_total_fg", "Total waited (FG)"),
    ]
    for waitclass in ORACLE_WAITCLASSES:
        waitclasses_choices.append((waitclass.metric, "%s wait class" % waitclass.name))
        waitclasses_choices.append((waitclass.metric_fg, "%s wait class (FG)" % waitclass.name))

    return Dictionary(
        help_text=Help("Here you can set levels for the Oracle performance metrics."),
        elements={
            "dbtime": DictElement(
                required=False,
                parameter_form=List(
                    element_template=CascadingSingleChoice(
                        title=Title("Field"),
                        elements=[
                            CascadingSingleChoiceElement(
                                name="oracle_db_cpu",
                                title=Title("DB CPU"),
                                parameter_form=_PERSEC_LEVELS,
                            ),
                            CascadingSingleChoiceElement(
                                name="oracle_db_time",
                                title=Title("DB time"),
                                parameter_form=_PERSEC_LEVELS,
                            ),
                            CascadingSingleChoiceElement(
                                name="oracle_db_wait_time",
                                title=Title("DB non-idle wait"),
                                parameter_form=_PERSEC_LEVELS,
                            ),
                        ],
                    ),
                    title=Title("Levels for DB time"),
                ),
            ),
            "memory": DictElement(
                required=False,
                parameter_form=List(
                    element_template=CascadingSingleChoice(
                        title=Title("Field"),
                        elements=memory_choices,
                    ),
                    title=Title("Levels for memory"),
                ),
            ),
            "iostat_bytes": DictElement(
                required=False,
                parameter_form=List(
                    element_template=CascadingSingleChoice(
                        title=Title("Field"),
                        elements=iostat_bytes_choices,
                    ),
                    title=Title("Levels for IO stats bytes"),
                ),
            ),
            "iostat_ios": DictElement(
                required=False,
                parameter_form=List(
                    element_template=CascadingSingleChoice(
                        title=Title("Field"),
                        elements=iostat_ios_choices,
                    ),
                    title=Title("Levels for IO stats requests"),
                ),
            ),
            "waitclasses": DictElement(
                required=False,
                parameter_form=List(
                    element_template=CascadingSingleChoice(
                        title=Title("Field"),
                        elements=[
                            CascadingSingleChoiceElement(
                                name=name,
                                title=Title(title),  # astrein: disable=localization-checker
                                parameter_form=_PERSEC_LEVELS,
                            )
                            for name, title in waitclasses_choices
                        ],
                    ),
                    title=Title("Levels for system wait"),
                ),
            ),
        },
    )


rule_spec_oracle_performance = CheckParameters(
    name="oracle_performance",
    title=Title("Oracle performance"),
    topic=Topic.DATABASES,
    parameter_form=_parameter_valuespec_oracle_performance,
    condition=HostAndItemCondition(item_title=Title("Database SID")),
)
