#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable, Mapping

from cmk.rulesets.v1 import Title
from cmk.rulesets.v1.form_specs import (
    DefaultValue,
    DictElement,
    Dictionary,
    Float,
    LevelDirection,
    LevelsType,
    migrate_to_float_simple_levels,
    Percentage,
    SimpleLevels,
    SimpleLevelsConfigModel,
)
from cmk.rulesets.v1.rule_specs import CheckParameters, HostCondition, Topic


def _rate_levels(title: Title) -> DictElement[SimpleLevelsConfigModel[float]]:
    return DictElement(
        required=False,
        parameter_form=SimpleLevels(
            title=title,
            migrate=migrate_to_float_simple_levels,
            level_direction=LevelDirection.UPPER,
            prefill_levels_type=DefaultValue(LevelsType.FIXED),
            prefill_fixed_levels=DefaultValue((1.0, 2.0)),
            form_spec_template=Float(unit_symbol="/s"),
        ),
    )


def _rate_rule_spec(
    name: str,
    title: Title,
    elements: Mapping[str, Title],
    migrate: Callable[[object], Mapping[str, object]] | None = None,
) -> CheckParameters:
    return CheckParameters(
        name=name,
        title=title,
        topic=Topic.APPLICATIONS,
        parameter_form=lambda: Dictionary(
            elements={key: _rate_levels(element_title) for key, element_title in elements.items()},
            migrate=migrate,
        ),
        condition=HostCondition(),
    )


def _ratio_rule_spec(name: str, title: Title) -> CheckParameters:
    return CheckParameters(
        name=name,
        title=title,
        topic=Topic.APPLICATIONS,
        parameter_form=lambda: Dictionary(
            elements={
                "levels_lower": DictElement(
                    required=False,
                    parameter_form=SimpleLevels(
                        title=Title("Lower levels"),
                        migrate=migrate_to_float_simple_levels,
                        level_direction=LevelDirection.LOWER,
                        prefill_levels_type=DefaultValue(LevelsType.FIXED),
                        prefill_fixed_levels=DefaultValue((70.0, 60.0)),
                        form_spec_template=Percentage(),
                    ),
                ),
            }
        ),
        condition=HostCondition(),
    )


rule_spec_varnish_backend = _rate_rule_spec(
    "varnish_backend",
    Title("Varnish backend"),
    {
        "busy": Title('Upper levels for "backend connections busy/too many" per second'),
        "fail": Title('Upper levels for "backend connections failures" per second'),
        "unhealthy": Title(
            'Upper levels for "backend connections unhealthy/not attempted" per second'
        ),
    },
)

rule_spec_varnish_cache = _rate_rule_spec(
    "varnish_cache",
    Title("Varnish Cache"),
    {"miss": Title('Upper levels for "cache misses" per second')},
)

rule_spec_varnish_client = _rate_rule_spec(
    "varnish_client",
    Title("Varnish Client"),
    {
        "drop": Title('Upper levels for "clients dropped" per second'),
        "req": Title('Upper levels for "client requests" per second'),
    },
)

rule_spec_varnish_esi = _rate_rule_spec(
    "varnish_esi",
    Title("Varnish ESI"),
    {
        "errors": Title('Upper levels for "ESI errors" per second'),
        "warnings": Title('Upper levels for "ESI warnings" per second'),
    },
)


def _migrate_fetch_keys(params: object) -> Mapping[str, object]:
    # keys must be identifiers, '1xx', '204' and '304' are not
    if not isinstance(params, Mapping):
        raise TypeError(params)
    return {f"fetch_{k}" if str(k)[0].isdigit() else str(k): v for k, v in params.items()}


rule_spec_varnish_fetch = _rate_rule_spec(
    "varnish_fetch",
    Title("Varnish Fetch"),
    {
        "fetch_1xx": Title('Upper levels for "fetch no body (1xx)" per second'),
        "fetch_204": Title('Upper levels for "fetch no body (204)" per second'),
        "fetch_304": Title('Upper levels for "fetch no body (304)" per second'),
        "bad": Title('Upper levels for "fetch had bad headers" per second'),
        "eof": Title('Upper levels for "fetch EOF" per second'),
        "failed": Title('Upper levels for "fetch failed" per second'),
        "zero": Title('Upper levels for "fetch zero length" per second'),
    },
    migrate=_migrate_fetch_keys,
)

rule_spec_varnish_objects = _rate_rule_spec(
    "varnish_objects",
    Title("Varnish Objects"),
    {
        "expired": Title('Upper levels for "expired objects" per second'),
        "lru_nuked": Title('Upper levels for "LRU nuked objects" per second'),
    },
)

rule_spec_varnish_worker = _rate_rule_spec(
    "varnish_worker",
    Title("Varnish Worker"),
    {
        "wrk_drop": Title('Upper levels for "dropped work requests" per second'),
        "wrk_failed": Title('Upper levels for "worker threads not created" per second'),
        "wrk_queued": Title('Upper levels for "queued work requests" per second'),
    },
)

rule_spec_varnish_backend_success_ratio = _ratio_rule_spec(
    "varnish_backend_success_ratio", Title("Varnish backend success ratio")
)

rule_spec_varnish_cache_hit_ratio = _ratio_rule_spec(
    "varnish_cache_hit_ratio", Title("Varnish Cache Hit Ratio")
)

rule_spec_varnish_worker_thread_ratio = _ratio_rule_spec(
    "varnish_worker_thread_ratio", Title("Varnish Worker Thread Ratio")
)
