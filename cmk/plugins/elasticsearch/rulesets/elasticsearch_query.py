#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.rulesets.v1 import Help, Title
from cmk.rulesets.v1.form_specs import (
    DefaultValue,
    DictElement,
    Dictionary,
    Integer,
    LevelDirection,
    List,
    migrate_to_integer_simple_levels,
    migrate_to_password,
    Password,
    SimpleLevels,
    SingleChoice,
    SingleChoiceElement,
    String,
    TimeMagnitude,
    TimeSpan,
)
from cmk.rulesets.v1.form_specs.validators import LengthInRange, NetworkPort
from cmk.rulesets.v1.rule_specs import ActiveCheck, Topic


def _migrate_to_float(value: object) -> float:
    if isinstance(value, int | float):
        return float(value)

    raise TypeError(value)


def _parameter_form() -> Dictionary:
    return Dictionary(
        elements={
            "svc_item": DictElement(
                parameter_form=String(
                    title=Title("Item suffix"),
                    help_text=Help(
                        "Here you can define what service name (item) is "
                        "used for the created service. The resulting item "
                        "is always prefixed with 'Elasticsearch Query'."
                    ),
                ),
                required=True,
            ),
            "hostname": DictElement(
                parameter_form=String(
                    title=Title("DNS host name or IP address"),
                    help_text=Help(
                        "You can specify a host name or IP address different from the IP address "
                        "of the host this check will be assigned to."
                    ),
                    macro_support=True,
                ),
                required=False,
            ),
            "user": DictElement(
                parameter_form=String(title=Title("Username")),
                required=False,
            ),
            "password": DictElement(
                parameter_form=Password(
                    title=Title("Password of the user"),
                    custom_validate=(LengthInRange(min_value=1),),
                    migrate=migrate_to_password,
                ),
                required=False,
            ),
            "protocol": DictElement(
                parameter_form=SingleChoice(
                    title=Title("Protocol"),
                    help_text=Help("Here you can define which protocol to use, default is https."),
                    elements=[
                        SingleChoiceElement(
                            name="http",
                            title=Title("HTTP"),
                        ),
                        SingleChoiceElement(
                            name="https",
                            title=Title("HTTPS"),
                        ),
                    ],
                    prefill=DefaultValue("https"),
                ),
                required=False,
            ),
            "port": DictElement(
                parameter_form=Integer(
                    title=Title("Port"),
                    help_text=Help(
                        "Use this option to query a port which is different from standard port 9200."
                    ),
                    custom_validate=(NetworkPort(),),
                    prefill=DefaultValue(9200),
                ),
                required=False,
            ),
            "pattern": DictElement(
                parameter_form=String(
                    title=Title("Search pattern"),
                    help_text=Help(
                        "Here you can define what search pattern should be used. "
                        "You can use Kibana query language as described "
                        '<a href="https://www.elastic.co/guide/en/kibana/current/kuery-query.html"'
                        'target="_blank">here</a>. To optimize search speed, use defined indices and fields '
                        "otherwise all indices and fields will be searched."
                    ),
                ),
                required=True,
            ),
            "index": DictElement(
                parameter_form=List(
                    title=Title("Indices to query"),
                    help_text=Help(
                        "Here you can define what index should be queried "
                        "for the defined search. You can query one or "
                        "multiple indices. Without this option all indices "
                        "are queried. If you want to speed up your search, "
                        "use definded indices."
                    ),
                    element_template=String(),
                ),
                required=False,
            ),
            "fieldname": DictElement(
                parameter_form=List(
                    title=Title("Fieldnames to query"),
                    help_text=Help(
                        "Here you can define fieldnames that should be used "
                        "in the search. Regexp query is allowed as described "
                        '<a href="https://www.elastic.co/guide/en/elasticsearch/reference/current/query-dsl-regexp-query.html"'
                        'target="_blank">here</a>. If you want to speed up your search, '
                        "use defined indices."
                    ),
                    element_template=String(),
                ),
                required=False,
            ),
            "timerange": DictElement(
                parameter_form=TimeSpan(
                    title=Title("Time range"),
                    displayed_magnitudes=(
                        TimeMagnitude.DAY,
                        TimeMagnitude.HOUR,
                        TimeMagnitude.MINUTE,
                    ),
                    prefill=DefaultValue(60.0),
                    migrate=_migrate_to_float,
                ),
                required=True,
            ),
            "count": DictElement(
                parameter_form=SimpleLevels(
                    title=Title("Thresholds on message count"),
                    form_spec_template=Integer(),
                    level_direction=LevelDirection.UPPER,
                    prefill_fixed_levels=DefaultValue((0, 0)),
                    migrate=migrate_to_integer_simple_levels,
                ),
                required=False,
            ),
        },
    )


rule_spec_active_check_elasticsearch = ActiveCheck(
    name="elasticsearch_query",
    title=Title("Query elasticsearch logs"),
    topic=Topic.APPLICATIONS,
    parameter_form=_parameter_form,
)
