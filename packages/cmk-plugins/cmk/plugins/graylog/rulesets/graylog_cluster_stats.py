#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.rulesets.v1 import Title
from cmk.rulesets.v1.form_specs import (
    DataSize,
    DefaultValue,
    DictElement,
    Dictionary,
    IECMagnitude,
    InputHint,
    Integer,
    LevelDirection,
    migrate_to_integer_simple_levels,
    ServiceState,
    SimpleLevels,
)
from cmk.rulesets.v1.rule_specs import CheckParameters, HostCondition, Topic

_DISPLAYED_MAGNITUDES = [
    IECMagnitude.BYTE,
    IECMagnitude.KIBI,
    IECMagnitude.MEBI,
    IECMagnitude.GIBI,
    IECMagnitude.TEBI,
]


def _parameter_valuespec_graylog_cluster_stats() -> Dictionary:
    return Dictionary(
        elements={
            "input_count_lower": DictElement(
                parameter_form=SimpleLevels[int](
                    title=Title("Total number of inputs lower level"),
                    level_direction=LevelDirection.LOWER,
                    form_spec_template=Integer(unit_symbol="inputs"),
                    prefill_fixed_levels=InputHint((0, 0)),
                    migrate=migrate_to_integer_simple_levels,
                ),
            ),
            "input_count_upper": DictElement(
                parameter_form=SimpleLevels[int](
                    title=Title("Total number of inputs upper level"),
                    level_direction=LevelDirection.UPPER,
                    form_spec_template=Integer(unit_symbol="inputs"),
                    prefill_fixed_levels=InputHint((0, 0)),
                    migrate=migrate_to_integer_simple_levels,
                ),
            ),
            "output_count_lower": DictElement(
                parameter_form=SimpleLevels[int](
                    title=Title("Total number of outputs lower level"),
                    level_direction=LevelDirection.LOWER,
                    form_spec_template=Integer(unit_symbol="outputs"),
                    prefill_fixed_levels=InputHint((0, 0)),
                    migrate=migrate_to_integer_simple_levels,
                ),
            ),
            "output_count_upper": DictElement(
                parameter_form=SimpleLevels[int](
                    title=Title("Total number of outputs upper level"),
                    level_direction=LevelDirection.UPPER,
                    form_spec_template=Integer(unit_symbol="outputs"),
                    prefill_fixed_levels=InputHint((0, 0)),
                    migrate=migrate_to_integer_simple_levels,
                ),
            ),
            "stream_count_lower": DictElement(
                parameter_form=SimpleLevels[int](
                    title=Title("Total number of streams lower level"),
                    level_direction=LevelDirection.LOWER,
                    form_spec_template=Integer(unit_symbol="streams"),
                    prefill_fixed_levels=InputHint((0, 0)),
                    migrate=migrate_to_integer_simple_levels,
                ),
            ),
            "stream_count_upper": DictElement(
                parameter_form=SimpleLevels[int](
                    title=Title("Total number of streams upper level"),
                    level_direction=LevelDirection.UPPER,
                    form_spec_template=Integer(unit_symbol="streams"),
                    prefill_fixed_levels=InputHint((0, 0)),
                    migrate=migrate_to_integer_simple_levels,
                ),
            ),
            "stream_rule_count_lower": DictElement(
                parameter_form=SimpleLevels[int](
                    title=Title("Total number of stream rules lower level"),
                    level_direction=LevelDirection.LOWER,
                    form_spec_template=Integer(unit_symbol="streams"),
                    prefill_fixed_levels=InputHint((0, 0)),
                    migrate=migrate_to_integer_simple_levels,
                ),
            ),
            "stream_rule_count_upper": DictElement(
                parameter_form=SimpleLevels[int](
                    title=Title("Total number of stream rules upper level"),
                    level_direction=LevelDirection.UPPER,
                    form_spec_template=Integer(unit_symbol="streams"),
                    prefill_fixed_levels=InputHint((0, 0)),
                    migrate=migrate_to_integer_simple_levels,
                ),
            ),
            "extractor_count_lower": DictElement(
                parameter_form=SimpleLevels[int](
                    title=Title("Total number of extractor lower level"),
                    level_direction=LevelDirection.LOWER,
                    form_spec_template=Integer(unit_symbol="extractor"),
                    prefill_fixed_levels=InputHint((0, 0)),
                    migrate=migrate_to_integer_simple_levels,
                ),
            ),
            "extractor_count_upper": DictElement(
                parameter_form=SimpleLevels[int](
                    title=Title("Total number of extractor upper level"),
                    level_direction=LevelDirection.UPPER,
                    form_spec_template=Integer(unit_symbol="extractor"),
                    prefill_fixed_levels=InputHint((0, 0)),
                    migrate=migrate_to_integer_simple_levels,
                ),
            ),
            "user_count_lower": DictElement(
                parameter_form=SimpleLevels[int](
                    title=Title("Total number of user lower level"),
                    level_direction=LevelDirection.LOWER,
                    form_spec_template=Integer(unit_symbol="user"),
                    prefill_fixed_levels=InputHint((0, 0)),
                    migrate=migrate_to_integer_simple_levels,
                ),
            ),
            "user_count_upper": DictElement(
                parameter_form=SimpleLevels[int](
                    title=Title("Total number of user upper level"),
                    level_direction=LevelDirection.UPPER,
                    form_spec_template=Integer(unit_symbol="user"),
                    prefill_fixed_levels=InputHint((0, 0)),
                    migrate=migrate_to_integer_simple_levels,
                ),
            ),
        },
    )


rule_spec_graylog_cluster_stats = CheckParameters(
    name="graylog_cluster_stats",
    title=Title("Graylog cluster statistics"),
    topic=Topic.APPLICATIONS,
    parameter_form=_parameter_valuespec_graylog_cluster_stats,
    condition=HostCondition(),
)


def _parameter_valuespec_graylog_cluster_stats_elastic() -> Dictionary:
    return Dictionary(
        elements={
            "green": DictElement(
                parameter_form=ServiceState(
                    title=Title("Status: green"),
                    prefill=DefaultValue(ServiceState.OK),
                ),
            ),
            "yellow": DictElement(
                parameter_form=ServiceState(
                    title=Title("Status: yellow"),
                    prefill=DefaultValue(ServiceState.WARN),
                ),
            ),
            "red": DictElement(
                parameter_form=ServiceState(
                    title=Title("Status: red"),
                    prefill=DefaultValue(ServiceState.CRIT),
                ),
            ),
            "number_of_nodes_lower": DictElement(
                parameter_form=SimpleLevels[int](
                    title=Title("Total number of nodes lower level"),
                    level_direction=LevelDirection.LOWER,
                    form_spec_template=Integer(unit_symbol="nodes"),
                    prefill_fixed_levels=InputHint((0, 0)),
                    migrate=migrate_to_integer_simple_levels,
                ),
            ),
            "number_of_nodes_upper": DictElement(
                parameter_form=SimpleLevels[int](
                    title=Title("Total number of nodes upper level"),
                    level_direction=LevelDirection.UPPER,
                    form_spec_template=Integer(unit_symbol="nodes"),
                    prefill_fixed_levels=InputHint((0, 0)),
                    migrate=migrate_to_integer_simple_levels,
                ),
            ),
            "number_of_data_nodes_lower": DictElement(
                parameter_form=SimpleLevels[int](
                    title=Title("Total number of data nodes lower level"),
                    level_direction=LevelDirection.LOWER,
                    form_spec_template=Integer(unit_symbol="data nodes"),
                    prefill_fixed_levels=InputHint((0, 0)),
                    migrate=migrate_to_integer_simple_levels,
                ),
            ),
            "number_of_data_nodes_upper": DictElement(
                parameter_form=SimpleLevels[int](
                    title=Title("Total number of data nodes upper level"),
                    level_direction=LevelDirection.UPPER,
                    form_spec_template=Integer(unit_symbol="data nodes"),
                    prefill_fixed_levels=InputHint((0, 0)),
                    migrate=migrate_to_integer_simple_levels,
                ),
            ),
            "active_shards_lower": DictElement(
                parameter_form=SimpleLevels[int](
                    title=Title("Total number of active shards lower level"),
                    level_direction=LevelDirection.LOWER,
                    form_spec_template=Integer(unit_symbol="shards"),
                    prefill_fixed_levels=InputHint((0, 0)),
                    migrate=migrate_to_integer_simple_levels,
                ),
            ),
            "active_shards_upper": DictElement(
                parameter_form=SimpleLevels[int](
                    title=Title("Total number of active shards upper level"),
                    level_direction=LevelDirection.UPPER,
                    form_spec_template=Integer(unit_symbol="shards"),
                    prefill_fixed_levels=InputHint((0, 0)),
                    migrate=migrate_to_integer_simple_levels,
                ),
            ),
            "active_primary_shards_lower": DictElement(
                parameter_form=SimpleLevels[int](
                    title=Title("Total number of active primary shards lower level"),
                    level_direction=LevelDirection.LOWER,
                    form_spec_template=Integer(unit_symbol="shards"),
                    prefill_fixed_levels=InputHint((0, 0)),
                    migrate=migrate_to_integer_simple_levels,
                ),
            ),
            "active_primary_shards_upper": DictElement(
                parameter_form=SimpleLevels[int](
                    title=Title("Total number of active primary shards upper level"),
                    level_direction=LevelDirection.UPPER,
                    form_spec_template=Integer(unit_symbol="shards"),
                    prefill_fixed_levels=InputHint((0, 0)),
                    migrate=migrate_to_integer_simple_levels,
                ),
            ),
            "unassigned_shards_upper": DictElement(
                parameter_form=SimpleLevels[int](
                    title=Title("Total number of unassigned shards"),
                    level_direction=LevelDirection.UPPER,
                    form_spec_template=Integer(unit_symbol="shards"),
                    prefill_fixed_levels=InputHint((0, 0)),
                    migrate=migrate_to_integer_simple_levels,
                ),
            ),
            "initializing_shards_upper": DictElement(
                parameter_form=SimpleLevels[int](
                    title=Title("Number of initializing shards"),
                    level_direction=LevelDirection.UPPER,
                    form_spec_template=Integer(unit_symbol="shards"),
                    prefill_fixed_levels=InputHint((0, 0)),
                    migrate=migrate_to_integer_simple_levels,
                ),
            ),
            "relocating_shards_upper": DictElement(
                parameter_form=SimpleLevels[int](
                    title=Title("Number of relocating shards"),
                    level_direction=LevelDirection.UPPER,
                    form_spec_template=Integer(unit_symbol="shards"),
                    prefill_fixed_levels=InputHint((0, 0)),
                    migrate=migrate_to_integer_simple_levels,
                ),
            ),
            "number_of_pending_tasks_upper": DictElement(
                parameter_form=SimpleLevels[int](
                    title=Title("Number of pending tasks"),
                    level_direction=LevelDirection.UPPER,
                    form_spec_template=Integer(unit_symbol="tasks"),
                    prefill_fixed_levels=InputHint((0, 0)),
                    migrate=migrate_to_integer_simple_levels,
                ),
            ),
            "index_count_lower": DictElement(
                parameter_form=SimpleLevels[int](
                    title=Title("Total number of indices lower level"),
                    level_direction=LevelDirection.LOWER,
                    form_spec_template=Integer(unit_symbol="indices"),
                    prefill_fixed_levels=InputHint((0, 0)),
                    migrate=migrate_to_integer_simple_levels,
                ),
            ),
            "index_count_upper": DictElement(
                parameter_form=SimpleLevels[int](
                    title=Title("Total number of indices upper level"),
                    level_direction=LevelDirection.UPPER,
                    form_spec_template=Integer(unit_symbol="indices"),
                    prefill_fixed_levels=InputHint((0, 0)),
                    migrate=migrate_to_integer_simple_levels,
                ),
            ),
        },
    )


rule_spec_graylog_cluster_stats_elastic = CheckParameters(
    name="graylog_cluster_stats_elastic",
    title=Title("Graylog cluster elasticsearch statistics"),
    topic=Topic.APPLICATIONS,
    parameter_form=_parameter_valuespec_graylog_cluster_stats_elastic,
    condition=HostCondition(),
)


def _parameter_valuespec_graylog_cluster_stats_mongodb() -> Dictionary:
    return Dictionary(
        elements={
            "indexes_lower": DictElement(
                parameter_form=SimpleLevels[int](
                    title=Title("Total number of indexes lower level"),
                    level_direction=LevelDirection.LOWER,
                    form_spec_template=Integer(unit_symbol="indexes"),
                    prefill_fixed_levels=InputHint((0, 0)),
                    migrate=migrate_to_integer_simple_levels,
                ),
            ),
            "indexes_upper": DictElement(
                parameter_form=SimpleLevels[int](
                    title=Title("Total number of indexes upper level"),
                    level_direction=LevelDirection.UPPER,
                    form_spec_template=Integer(unit_symbol="indexes"),
                    prefill_fixed_levels=InputHint((0, 0)),
                    migrate=migrate_to_integer_simple_levels,
                ),
            ),
            "storage_size_upper": DictElement(
                parameter_form=SimpleLevels[int](
                    title=Title("Upper levels for allocated storage size"),
                    level_direction=LevelDirection.UPPER,
                    form_spec_template=DataSize(displayed_magnitudes=_DISPLAYED_MAGNITUDES),
                    prefill_fixed_levels=InputHint((0, 0)),
                    migrate=migrate_to_integer_simple_levels,
                ),
            ),
            "index_size_upper": DictElement(
                parameter_form=SimpleLevels[int](
                    title=Title("Upper levels for total index size"),
                    level_direction=LevelDirection.UPPER,
                    form_spec_template=DataSize(displayed_magnitudes=_DISPLAYED_MAGNITUDES),
                    prefill_fixed_levels=InputHint((0, 0)),
                    migrate=migrate_to_integer_simple_levels,
                ),
            ),
            "data_size_upper": DictElement(
                parameter_form=SimpleLevels[int](
                    title=Title("Upper levels for total uncompressed data size"),
                    level_direction=LevelDirection.UPPER,
                    form_spec_template=DataSize(displayed_magnitudes=_DISPLAYED_MAGNITUDES),
                    prefill_fixed_levels=InputHint((0, 0)),
                    migrate=migrate_to_integer_simple_levels,
                ),
            ),
            "file_size_upper": DictElement(
                parameter_form=SimpleLevels[int](
                    title=Title("Upper levels for datafile size"),
                    level_direction=LevelDirection.UPPER,
                    form_spec_template=DataSize(displayed_magnitudes=_DISPLAYED_MAGNITUDES),
                    prefill_fixed_levels=InputHint((0, 0)),
                    migrate=migrate_to_integer_simple_levels,
                ),
            ),
            "ns_size_mb_upper": DictElement(
                parameter_form=SimpleLevels[int](
                    title=Title("Upper levels for total namespace size"),
                    level_direction=LevelDirection.UPPER,
                    form_spec_template=DataSize(displayed_magnitudes=_DISPLAYED_MAGNITUDES),
                    prefill_fixed_levels=InputHint((0, 0)),
                    migrate=migrate_to_integer_simple_levels,
                ),
            ),
            "avg_obj_size_upper": DictElement(
                parameter_form=SimpleLevels[int](
                    title=Title("Upper levels for average document size"),
                    level_direction=LevelDirection.UPPER,
                    form_spec_template=DataSize(displayed_magnitudes=_DISPLAYED_MAGNITUDES),
                    prefill_fixed_levels=InputHint((0, 0)),
                    migrate=migrate_to_integer_simple_levels,
                ),
            ),
            "num_extents_lower": DictElement(
                parameter_form=SimpleLevels[int](
                    title=Title("Total number of extents lower level"),
                    level_direction=LevelDirection.LOWER,
                    form_spec_template=Integer(unit_symbol="extents"),
                    prefill_fixed_levels=InputHint((0, 0)),
                    migrate=migrate_to_integer_simple_levels,
                ),
            ),
            "num_extents_upper": DictElement(
                parameter_form=SimpleLevels[int](
                    title=Title("Total number of extents upper level"),
                    level_direction=LevelDirection.UPPER,
                    form_spec_template=Integer(unit_symbol="extents"),
                    prefill_fixed_levels=InputHint((0, 0)),
                    migrate=migrate_to_integer_simple_levels,
                ),
            ),
            "collections_lower": DictElement(
                parameter_form=SimpleLevels[int](
                    title=Title("Total number of collections lower level"),
                    level_direction=LevelDirection.LOWER,
                    form_spec_template=Integer(unit_symbol="collections"),
                    prefill_fixed_levels=InputHint((0, 0)),
                    migrate=migrate_to_integer_simple_levels,
                ),
            ),
            "collections_upper": DictElement(
                parameter_form=SimpleLevels[int](
                    title=Title("Total number of collections upper level"),
                    level_direction=LevelDirection.UPPER,
                    form_spec_template=Integer(unit_symbol="collections"),
                    prefill_fixed_levels=InputHint((0, 0)),
                    migrate=migrate_to_integer_simple_levels,
                ),
            ),
            "ojects_lower": DictElement(
                parameter_form=SimpleLevels[int](
                    title=Title("Total number of objects lower level"),
                    level_direction=LevelDirection.LOWER,
                    form_spec_template=Integer(unit_symbol="objects"),
                    prefill_fixed_levels=InputHint((0, 0)),
                    migrate=migrate_to_integer_simple_levels,
                ),
            ),
            "objects_upper": DictElement(
                parameter_form=SimpleLevels[int](
                    title=Title("Total number of objects upper level"),
                    level_direction=LevelDirection.UPPER,
                    form_spec_template=Integer(unit_symbol="objects"),
                    prefill_fixed_levels=InputHint((0, 0)),
                    migrate=migrate_to_integer_simple_levels,
                ),
            ),
        },
    )


rule_spec_graylog_cluster_stats_mongodb = CheckParameters(
    name="graylog_cluster_stats_mongodb",
    title=Title("Graylog cluster MongoDB statistics"),
    topic=Topic.APPLICATIONS,
    parameter_form=_parameter_valuespec_graylog_cluster_stats_mongodb,
    condition=HostCondition(),
)
