#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.ccc.hostaddress import HostName
from cmk.gui.form_specs.unstable import TwoColumnDictionary
from cmk.rulesets.internal.form_specs import ListExtended
from cmk.rulesets.v1 import Help, Label, Message, Title
from cmk.rulesets.v1.form_specs import (
    CascadingSingleChoice,
    CascadingSingleChoiceElement,
    DefaultValue,
    DictElement,
    Dictionary,
    FixedValue,
    List,
    MatchingScope,
    MultipleChoice,
    MultipleChoiceElement,
    RegularExpression,
    String,
    validators,
)

from .helm import HOST_KINDS


def cluster_configuration() -> Dictionary:
    return TwoColumnDictionary(
        elements={
            "cluster_name": DictElement(
                required=True,
                parameter_form=String(
                    title=Title("Cluster name"),
                    custom_validate=(
                        validators.LengthInRange(min_value=1, max_value=63),
                        validators.MatchRegex(
                            regex=HostName.REGEX_HOST_NAME,
                            error_msg=Message(
                                "Use only letters, numbers, dots, hyphens and underscores, "
                                "starting with a letter, number or underscore."
                            ),
                        ),
                    ),
                    help_text=Help(
                        "This name becomes part of the generated Kubernetes host names. "
                        "Keep it stable to retain their monitoring history."
                    ),
                ),
            ),
            "namespace": DictElement(
                required=True,
                parameter_form=String(
                    title=Title("Deployment namespace"),
                    prefill=DefaultValue("checkmk-monitoring"),
                    custom_validate=(
                        validators.LengthInRange(min_value=1, max_value=63),
                        validators.MatchRegex(
                            regex=r"\A[a-z0-9](?:[-a-z0-9]*[a-z0-9])?\Z",
                            error_msg=Message(
                                "Use lowercase letters, numbers and hyphens, starting and ending "
                                "with a letter or number."
                            ),
                        ),
                    ),
                    help_text=Help("The namespace in which the Kubernetes agent will be deployed."),
                ),
            ),
            "host_kinds": DictElement(
                required=True,
                parameter_form=MultipleChoice(
                    title=Title("Kubernetes kinds to monitor"),
                    elements=[
                        MultipleChoiceElement(name="deployments", title=Title("Deployments")),
                        MultipleChoiceElement(name="daemonsets", title=Title("DaemonSets")),
                        MultipleChoiceElement(name="statefulsets", title=Title("StatefulSets")),
                        MultipleChoiceElement(name="namespaces", title=Title("Namespaces")),
                        MultipleChoiceElement(name="nodes", title=Title("Nodes")),
                        MultipleChoiceElement(name="pods", title=Title("Pods")),
                        MultipleChoiceElement(name="cronjobs", title=Title("CronJobs")),
                    ],
                    prefill=DefaultValue([kind for kind in HOST_KINDS if kind != "pods"]),
                    help_text=Help(
                        "Selected kinds become Checkmk hosts. Individual resources can override "
                        "this choice using the checkmk.com/promote-to-host annotation."
                    ),
                ),
            ),
            "namespaces": DictElement(
                parameter_form=CascadingSingleChoice(
                    title=Title("Namespaces to monitor"),
                    elements=[
                        CascadingSingleChoiceElement(
                            name="include",
                            title=Title("Monitor namespaces matching"),
                            parameter_form=_namespace_patterns(),
                        ),
                        CascadingSingleChoiceElement(
                            name="exclude",
                            title=Title("Exclude namespaces matching"),
                            parameter_form=_namespace_patterns(),
                        ),
                    ],
                    prefill=DefaultValue("include"),
                    help_text=Help(
                        "When disabled, all namespaces are monitored. Filters apply to namespaced "
                        "resources; cluster and node hosts and their rollups are unaffected."
                    ),
                ),
            ),
        }
    )


def _namespace_patterns() -> List[str]:
    return List(
        element_template=_pattern(),
        add_element_label=Label("Add pattern"),
        custom_validate=(validators.LengthInRange(min_value=1),),
    )


def _pattern() -> RegularExpression:
    return RegularExpression(
        title=Title("Pattern"),
        predefined_help_text=MatchingScope.INFIX,
        custom_validate=(validators.LengthInRange(min_value=1),),
        help_text=Help("Look-around assertions and backreferences are not supported by the agent."),
    )


def advanced_configuration() -> Dictionary:
    """Monitoring options rendered inside the stage's Advanced options section."""
    return TwoColumnDictionary(
        elements={
            "excluded_node_roles": DictElement(
                required=True,
                parameter_form=ListExtended(
                    title=Title("Cluster-level aggregation exclusions"),
                    element_template=_pattern(),
                    prefill=DefaultValue(["control-plane", "infra"]),
                    add_element_label=Label("Add role pattern"),
                    help_text=Help(
                        "Exclude nodes whose role, taken from a node-role.kubernetes.io/ label, "
                        "matches a pattern from cluster-level resource aggregations. Clear the list to "
                        "include all nodes."
                    ),
                ),
            ),
            "annotations": DictElement(
                parameter_form=CascadingSingleChoice(
                    title=Title("Import annotations as host labels"),
                    elements=[
                        CascadingSingleChoiceElement(
                            name="all",
                            title=Title("Import all valid annotations"),
                            parameter_form=FixedValue(value=None),
                        ),
                        CascadingSingleChoiceElement(
                            name="pattern",
                            title=Title("Import matching annotation keys"),
                            parameter_form=_pattern(),
                        ),
                    ],
                    prefill=DefaultValue("all"),
                    help_text=Help("When disabled, no annotations are imported as host labels."),
                ),
            ),
        }
    )
