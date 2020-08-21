#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.valuespec import (
    Dictionary,
    Filesize,
    Percentage,
    Tuple,
)
from cmk.gui.plugins.wato import (
    RulespecGroupCheckParametersApplications,
    CheckParameterRulespecWithoutItem,
    rulespec_registry,
)


def _parameter_valuespec_k8s_pods_cpu():
    return Dictionary(elements=[
        ("system",
         Tuple(
             title=_("System CPU usage"),
             elements=[Percentage(title=_("Warning at")),
                       Percentage(title=_("Critical at"))],
         )),
        ("user",
         Tuple(
             title=_("User CPU usage"),
             elements=[Percentage(title=_("Warning at")),
                       Percentage(title=_("Critical at"))],
         )),
    ],)


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="k8s_pods_cpu",
        group=RulespecGroupCheckParametersApplications,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_k8s_pods_cpu,
        title=lambda: _("Kubernetes Namespaced pods cpu usage"),
    ))


def _parameter_valuespec_k8s_pods_memory():
    return Dictionary(elements=[
        ("rss",
         Tuple(
             title=_("Resident memory usage"),
             elements=[
                 Filesize(title=_("Warning at")),
                 Filesize(title=_("Critical at")),
             ],
         )),
        ("swap",
         Tuple(
             title=_("Swap memory usage"),
             elements=[
                 Filesize(title=_("Warning at")),
                 Filesize(title=_("Critical at")),
             ],
         )),
        ("usage_bytes",
         Tuple(
             title=_("Total memory usage"),
             elements=[
                 Filesize(title=_("Warning at")),
                 Filesize(title=_("Critical at")),
             ],
         )),
    ],)


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="k8s_pods_memory",
        group=RulespecGroupCheckParametersApplications,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_k8s_pods_memory,
        title=lambda: _("Kubernetes Namespaced pods memory usage"),
    ))


def _parameter_valuespec_k8s_pods_fs():
    return Dictionary(elements=[
        ("usage_bytes",
         Tuple(
             title=_("Filesystem usage"),
             elements=[
                 Filesize(title=_("Warning at")),
                 Filesize(title=_("Critical at")),
             ],
         )),
    ],)


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="k8s_pods_fs",
        group=RulespecGroupCheckParametersApplications,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_k8s_pods_fs,
        title=lambda: _("Kubernetes Namespaced pods Filesystem usage"),
    ))
