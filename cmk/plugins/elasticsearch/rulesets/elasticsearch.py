#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from typing import Any

from cmk.rulesets.v1 import Help, Label, Message, Title
from cmk.rulesets.v1.form_specs import (
    BooleanChoice,
    DefaultValue,
    DictElement,
    Dictionary,
    Integer,
    List,
    migrate_to_password,
    Password,
    SingleChoice,
    SingleChoiceElement,
    String,
)
from cmk.rulesets.v1.form_specs.validators import LengthInRange, NetworkPort, ValidationError
from cmk.rulesets.v1.rule_specs import SpecialAgent, Topic


def _migrate(value: object) -> Mapping[str, object]:
    if not isinstance(value, dict):
        raise ValueError(f"Invalid value {value} for Elasticsearch")
    if "no-cert-check" in value:
        value["no_cert_check"] = value.pop("no-cert-check")

    if "infos" in value:
        value["cluster_health"] = "cluster_health" in value["infos"]
        value["nodes"] = "nodes" in value["infos"]
        value["stats"] = ["*-*"] if "stats" in value["infos"] else []
        del value["infos"]

    return value


def _validate_index_patterns(value: Any) -> None:
    # Based on index name criteria:
    # https://www.elastic.co/guide/en/elasticsearch/reference/current/indices-create-index.html

    invalid_chars = r"\\/?\"<>|, #"
    if invalid := set(value) & set(invalid_chars):
        raise ValidationError(
            Message("Pattern contains invalid characters: %s")
            % ",".join(f"'{el}'" for el in invalid)
        )


def _parameter_form() -> Dictionary:
    return Dictionary(
        title=Title("Elasticsearch"),
        help_text=Help("Requests data about Elasticsearch clusters, nodes and indices."),
        elements={
            "hosts": DictElement(
                parameter_form=List(
                    title=Title("Host names to query"),
                    help_text=Help(
                        "Use this option to set which host should be checked by the special agent. If the "
                        "connection to the first server fails, the next server will be queried (fallback). "
                        "The check will only output data from the first host that sends a response."
                    ),
                    element_template=String(macro_support=True),
                    custom_validate=(LengthInRange(min_value=1),),
                ),
                required=True,
            ),
            "user": DictElement(
                parameter_form=String(title=Title("Username")),
                required=False,
            ),
            "password": DictElement(
                parameter_form=Password(
                    title=Title("Password"),
                    custom_validate=(LengthInRange(min_value=1),),
                    migrate=migrate_to_password,
                ),
                required=False,
            ),
            "protocol": DictElement(
                parameter_form=SingleChoice(
                    title=Title("Protocol"),
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
                required=True,
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
                required=True,
            ),
            "no_cert_check": DictElement(
                parameter_form=BooleanChoice(
                    title=Title("Skip SSL certificate verification"),
                    prefill=DefaultValue(False),
                    label=Label("Skip verification (insecure)"),
                ),
                required=False,
            ),
            "cluster_health": DictElement(
                parameter_form=BooleanChoice(
                    label=Label("Cluster health"),
                    prefill=DefaultValue(False),
                ),
                required=True,
            ),
            "nodes": DictElement(
                parameter_form=BooleanChoice(
                    label=Label("Node statistics"),
                    prefill=DefaultValue(False),
                ),
                required=True,
            ),
            "stats": DictElement(
                parameter_form=List(
                    element_template=String(
                        label=Label("Pattern"),
                        prefill=DefaultValue("*"),
                        custom_validate=(LengthInRange(min_value=1), _validate_index_patterns),
                    ),
                    title=Title("Cluster, indices and shard statistics"),
                    help_text=Help(
                        "You can specify data streams, indices, and aliases "
                        "used to limit the request. "
                        "Supports wildcards (*). "
                        "To target all data streams and indices use `*` or `_all`. "
                        "The patterns will be combined to form the final url endpoint, e.g.: "
                        "`pattern_1,pattern_2/_stats/store,docs?ignore_unavailable=true`"
                    ),
                    add_element_label=Label("Add new pattern"),
                    editable_order=False,
                    custom_validate=(LengthInRange(min_value=1),),
                ),
                required=False,
            ),
        },
        migrate=_migrate,
    )


rule_spec_special_agent_elasticsearch = SpecialAgent(
    name="elasticsearch",
    title=Title("Elasticsearch"),
    topic=Topic.APPLICATIONS,
    parameter_form=_parameter_form,
)
