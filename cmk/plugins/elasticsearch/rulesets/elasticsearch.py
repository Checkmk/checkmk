#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

from cmk.rulesets.v1 import Help, Label, Title
from cmk.rulesets.v1.form_specs import (
    BooleanChoice,
    DefaultValue,
    DictElement,
    Dictionary,
    Integer,
    List,
    migrate_to_password,
    MultipleChoice,
    MultipleChoiceElement,
    Password,
    SingleChoice,
    SingleChoiceElement,
    String,
)
from cmk.rulesets.v1.form_specs.validators import LengthInRange, NetworkPort
from cmk.rulesets.v1.rule_specs import SpecialAgent, Topic


def _migrate_element_names(value: object) -> Mapping[str, object]:
    if not isinstance(value, dict):
        raise ValueError(f"Invalid value {value} for Elasticsearch")
    if "no-cert-check" in value:
        value["no_cert_check"] = value.pop("no-cert-check")
    return value


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
            "infos": DictElement(
                parameter_form=MultipleChoice(
                    title=Title("Informations to query"),
                    help_text=Help(
                        "Defines what information to query. "
                        "Checks for cluster, indices and shard statistics follow soon."
                    ),
                    elements=[
                        MultipleChoiceElement(
                            name="cluster_health",
                            title=Title("Cluster health"),
                        ),
                        MultipleChoiceElement(
                            name="nodes",
                            title=Title("Node statistics"),
                        ),
                        MultipleChoiceElement(
                            name="stats",
                            title=Title("Cluster, indices and shard statistics"),
                        ),
                    ],
                    custom_validate=(LengthInRange(min_value=1),),
                    prefill=DefaultValue(["cluster_health", "nodes", "stats"]),
                ),
                required=True,
            ),
        },
        migrate=_migrate_element_names,
    )


rule_spec_special_agent_elasticsearch = SpecialAgent(
    name="elasticsearch",
    title=Title("Elasticsearch"),
    topic=Topic.APPLICATIONS,
    parameter_form=_parameter_form,
)
