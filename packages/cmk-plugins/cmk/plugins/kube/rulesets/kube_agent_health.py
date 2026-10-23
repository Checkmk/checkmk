#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.rulesets.v1 import form_specs, Help, Label, rule_specs, Title


def _upper_time_levels(
    title: Title, defaults: tuple[float, float], help_text: Help, *, enabled: bool = True
) -> form_specs.SimpleLevels[float]:
    return form_specs.SimpleLevels(
        title=title,
        help_text=help_text + Help(" Choose 'No levels' to disable these thresholds."),
        form_spec_template=form_specs.TimeSpan(
            displayed_magnitudes=[
                form_specs.TimeMagnitude.MILLISECOND,
                form_specs.TimeMagnitude.SECOND,
                form_specs.TimeMagnitude.MINUTE,
            ],
            custom_validate=(form_specs.validators.NumberInRange(min_value=0),),
        ),
        level_direction=form_specs.LevelDirection.UPPER,
        prefill_fixed_levels=form_specs.DefaultValue(defaults),
        prefill_levels_type=form_specs.DefaultValue(
            form_specs.LevelsType.FIXED if enabled else form_specs.LevelsType.NONE
        ),
    )


def _parameter_form_node_scrapers() -> form_specs.Dictionary:
    return form_specs.Dictionary(
        title=Title("Node scrapers"),
        help_text=Help(
            "Allows for alerting on how often a node checks in with the cluster aggregator "
            "from the node's scraper. Once a payload expires from the aggregator's cache, it "
            "is considered missing and reports the specified missing payload state. It is "
            "recommended to match levels here with your collection interval and cache retention "
            "set for the in-cluster agent."
        ),
        elements={
            "age": form_specs.DictElement(
                parameter_form=_upper_time_levels(
                    Title("Time since last data received"),
                    (90.0, 120.0),
                    Help(
                        "Check how long the cluster aggregator has waited for each data type. "
                        "Adjust these levels to your collection interval and cache retention. "
                        "Missing data is evaluated separately, even when age thresholds are disabled."
                    ),
                ),
            ),
            "missing_state": form_specs.DictElement(
                parameter_form=form_specs.ServiceState(
                    title=Title("State when expected data is missing from the cache"),
                    help_text=Help(
                        "Choose the state when a data type has never arrived or has "
                        "expired from the cache, including during startup. This state "
                        "applies regardless of the configured age thresholds."
                    ),
                    prefill=form_specs.DefaultValue(form_specs.ServiceState.CRIT),
                ),
            ),
            "version_state": form_specs.DictElement(
                parameter_form=form_specs.ServiceState(
                    title=Title("State when node-scraper and cluster-aggregator versions differ"),
                    help_text=Help(
                        "Choose the state when a node reports a node-scraper version different "
                        "from the cluster-aggregator version. Versions that are not reported and "
                        "differing Git revisions do not cause alerts."
                    ),
                    prefill=form_specs.DefaultValue(form_specs.ServiceState.OK),
                ),
            ),
        },
    )


def _parameter_form_reflectors() -> form_specs.Dictionary:
    return form_specs.Dictionary(
        title=Title("Kubernetes API reflectors"),
        help_text=Help(
            "Reflectors maintain the cache of Kubernetes objects using lists and watches. "
            "The age of a completed list is not a freshness signal: a healthy watch can "
            "continue indefinitely without relisting."
        ),
        elements={
            "uninitialized_state": form_specs.DictElement(
                parameter_form=form_specs.ServiceState(
                    title=Title("State before the first list has completed"),
                    help_text=Help(
                        "Choose the state while the agent has not yet collected a complete list "
                        "of this Kubernetes resource kind. This also applies during initial startup."
                    ),
                    prefill=form_specs.DefaultValue(form_specs.ServiceState.WARN),
                ),
            ),
            "relist_age": form_specs.DictElement(
                parameter_form=_upper_time_levels(
                    Title("Duration of an ongoing list or relist"),
                    (120.0, 300.0),
                    Help(
                        "Alert if the agent takes too long to obtain a complete list of "
                        "Kubernetes objects. Only an unfinished list is timed; the age and "
                        "duration of a completed list do not affect the service state."
                    ),
                ),
            ),
            "recent_error_window": form_specs.DictElement(
                parameter_form=form_specs.CascadingSingleChoice(
                    title=Title("Recent watch errors"),
                    help_text=Help(
                        "After an error while receiving Kubernetes object updates, keep an "
                        "alert active for the selected period. Each new error restarts this "
                        "period. The alert ends when the period expires; this does not confirm "
                        "that the connection has recovered. Inspect the cluster-aggregator logs "
                        "to investigate the underlying Kubernetes API error."
                    ),
                    prefill=form_specs.DefaultValue("disabled"),
                    elements=[
                        form_specs.CascadingSingleChoiceElement(
                            name="enabled",
                            title=Title("Alert for a limited time"),
                            parameter_form=form_specs.TimeSpan(
                                help_text=Help(
                                    "How long to alert after the most recent watch error."
                                ),
                                displayed_magnitudes=[
                                    form_specs.TimeMagnitude.SECOND,
                                    form_specs.TimeMagnitude.MINUTE,
                                ],
                                prefill=form_specs.DefaultValue(300.0),
                                custom_validate=(form_specs.validators.NumberInRange(min_value=1),),
                            ),
                        ),
                        form_specs.CascadingSingleChoiceElement(
                            name="disabled",
                            title=Title("Do not alert"),
                            parameter_form=form_specs.FixedValue(value=None),
                        ),
                    ],
                ),
            ),
            "recent_error_state": form_specs.DictElement(
                parameter_form=form_specs.ServiceState(
                    title=Title("State for a recent watch error"),
                    help_text=Help(
                        "Choose the state used while a recent watch-error alert is active. "
                        "This setting has no effect when 'Recent watch errors' is set to "
                        "'Do not alert'. Error details remain available in reflector services."
                    ),
                    prefill=form_specs.DefaultValue(form_specs.ServiceState.WARN),
                ),
            ),
            "last_event_age": form_specs.DictElement(
                parameter_form=_upper_time_levels(
                    Title("Time since the last resource event"),
                    (3600.0, 86400.0),
                    Help(
                        "Show when this reflector last received a resource event. Enable "
                        "thresholds only for resource kinds where a long quiet period is "
                        "unexpected."
                    ),
                    enabled=False,
                ),
            ),
        },
    )


def _parameter_form_health() -> form_specs.Dictionary:
    return form_specs.Dictionary(
        help_text=Help(
            "These settings apply to the cluster overview. Node and reflector "
            "services have their own rules and do not change the overview's evaluation."
        ),
        elements={
            "scrapers": form_specs.DictElement(parameter_form=_parameter_form_node_scrapers()),
            "reflectors": form_specs.DictElement(parameter_form=_parameter_form_reflectors()),
            "empty_scrapers_state": form_specs.DictElement(
                parameter_form=form_specs.ServiceState(
                    title=Title("State when no node-scraper nodes are reported"),
                    help_text=Help(
                        "Choose the state when the agent reports no nodes with node scrapers. "
                        "Check whether the node-scraper DaemonSet is deployed, identified "
                        "correctly and has scheduled pods."
                    ),
                    prefill=form_specs.DefaultValue(form_specs.ServiceState.WARN),
                ),
            ),
            "empty_reflectors_state": form_specs.DictElement(
                parameter_form=form_specs.ServiceState(
                    title=Title("State when no reflectors are reported"),
                    help_text=Help(
                        "Choose the state when the agent reports no Kubernetes API reflectors. "
                        "Check the cluster-aggregator deployment and its logs."
                    ),
                    prefill=form_specs.DefaultValue(form_specs.ServiceState.CRIT),
                ),
            ),
        },
    )


def _parameter_form_discovery() -> form_specs.Dictionary:
    return form_specs.Dictionary(
        help_text=Help(
            "Enable component services for separate diagnostics, thresholds, notifications "
            "and graphs. The cluster overview continues to alert independently, so a fault "
            "can affect both services. All services live on the cluster host. Rediscover "
            "services after changing this rule."
        ),
        elements={
            "nodes": form_specs.DictElement(
                required=True,
                parameter_form=form_specs.BooleanChoice(
                    title=Title("Node-scraper nodes"),
                    label=Label("Discover a service per node"),
                    help_text=Help(
                        "Add a service on the cluster host for each node running a node "
                        "scraper. Use these services for node-specific thresholds, graphs and "
                        "notifications. Rediscover services after changing this choice."
                    ),
                    prefill=form_specs.DefaultValue(False),
                ),
            ),
            "reflectors": form_specs.DictElement(
                required=True,
                parameter_form=form_specs.BooleanChoice(
                    title=Title("Kubernetes API reflectors"),
                    label=Label("Discover a service per resource kind"),
                    help_text=Help(
                        "Add a service on the cluster host for each watched Kubernetes resource "
                        "kind, such as Pod or DaemonSet. Use these services for separate "
                        "thresholds, graphs and notifications. Rediscover services after "
                        "changing this choice."
                    ),
                    prefill=form_specs.DefaultValue(True),
                ),
            ),
        },
    )


rule_spec_kube_agent_health = rule_specs.CheckParameters(
    name="kube_agent_health",
    title=Title("Kubernetes agent health"),
    topic=rule_specs.Topic.APPLICATIONS,
    parameter_form=_parameter_form_health,
    condition=rule_specs.HostCondition(),
)

rule_spec_kube_agent_health_node = rule_specs.CheckParameters(
    name="kube_agent_health_node",
    title=Title("Kubernetes agent node health"),
    topic=rule_specs.Topic.APPLICATIONS,
    parameter_form=_parameter_form_node_scrapers,
    condition=rule_specs.HostAndItemCondition(item_title=Title("Node name")),
)

rule_spec_kube_agent_health_reflector = rule_specs.CheckParameters(
    name="kube_agent_health_reflector",
    title=Title("Kubernetes agent reflector health"),
    topic=rule_specs.Topic.APPLICATIONS,
    parameter_form=_parameter_form_reflectors,
    condition=rule_specs.HostAndItemCondition(item_title=Title("Kubernetes resource kind")),
)

rule_spec_discovery_kube_agent_health = rule_specs.DiscoveryParameters(
    name="discovery_kube_agent_health",
    title=Title("Kubernetes agent health service discovery"),
    topic=rule_specs.Topic.APPLICATIONS,
    parameter_form=_parameter_form_discovery,
)
