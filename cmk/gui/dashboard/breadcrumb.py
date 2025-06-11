#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.breadcrumb import Breadcrumb, BreadcrumbItem, make_topic_breadcrumb
from cmk.gui.http import request
from cmk.gui.main_menu import main_menu_registry
from cmk.gui.pagetypes import PagetypeTopics
from cmk.gui.type_defs import HTTPVariables, VisualContext
from cmk.gui.utils.urls import makeuri, makeuri_contextless

from .type_defs import DashboardConfig

__all__ = ["dashboard_breadcrumb"]


def dashboard_breadcrumb(
    name: str, board: DashboardConfig, title: str, context: VisualContext
) -> Breadcrumb:
    breadcrumb = make_topic_breadcrumb(
        main_menu_registry.menu_monitoring(),
        PagetypeTopics.get_topic(board["topic"]).title(),
    )

    if "kubernetes" in name:
        return kubernetes_dashboard_breadcrumb(name, board, title, breadcrumb, context)

    breadcrumb.append(BreadcrumbItem(title, makeuri(request, [("name", name)])))
    return breadcrumb


def kubernetes_dashboard_breadcrumb(
    name: str,
    board: DashboardConfig,
    title: str,
    breadcrumb: Breadcrumb,
    context: VisualContext,
) -> Breadcrumb:
    """Realize the Kubernetes hierarchy breadcrumb

    Kubernetes (overview board)
     |
     + Kubernetes Cluster
       |
       + Kubernetes Namespace
         |
         + Kubernetes [DaemonSet|StatefulSet|Deployment]
    """
    k8s_ids: dict[str, str] = {
        ident: "kubernetes_%s" % ident
        for ident in [
            "overview",
            "cluster",
            "cluster-host",  # for the host label only; not a dashboard name
            "namespace",
            "daemonset",
            "statefulset",
            "deployment",
        ]
    }
    # Overview
    breadcrumb.append(
        BreadcrumbItem("Kubernetes", makeuri_contextless(request, [("name", k8s_ids["overview"])]))
    )
    if name == k8s_ids["overview"]:
        return breadcrumb

    # Cluster
    cluster_name: str | None = context.get(k8s_ids["cluster"], {}).get(k8s_ids["cluster"])
    cluster_host: str | None = (
        # take current host from context, if on the cluster dashboard
        context.get("host", {}).get("host")
        if name == k8s_ids["cluster"]
        # else take the cluster-host from request (url)
        else request.get_str_input(k8s_ids["cluster-host"])
    )
    if not (cluster_name and cluster_host):
        breadcrumb.append(BreadcrumbItem(title, makeuri(request, [("name", name)])))
        return breadcrumb
    add_vars: HTTPVariables = [
        ("site", context.get("site", {}).get("site")),
        (k8s_ids["cluster"], cluster_name),
        (k8s_ids["cluster-host"], cluster_host),
    ]
    breadcrumb.append(
        BreadcrumbItem(
            f"Cluster {cluster_name}",
            makeuri_contextless(
                request,
                [
                    ("name", k8s_ids["cluster"]),
                    ("host", cluster_host),
                    *add_vars,
                ],
            ),
        )
    )
    if name == k8s_ids["cluster"]:
        return breadcrumb

    # Namespace
    namespace_name: str | None = context.get(k8s_ids["namespace"], {}).get(k8s_ids["namespace"])
    if not namespace_name:
        breadcrumb.append(BreadcrumbItem(title, makeuri(request, [("name", name)])))
        return breadcrumb
    add_vars.append((k8s_ids["namespace"], namespace_name))
    breadcrumb.append(
        BreadcrumbItem(
            f"Namespace {namespace_name}",
            makeuri_contextless(
                request,
                [
                    ("name", k8s_ids["namespace"]),
                    ("host", f"namespace_{cluster_name}_{namespace_name}"),
                    *add_vars,
                ],
            ),
        )
    )
    if name == k8s_ids["namespace"]:
        return breadcrumb

    # [DaemonSet|StatefulSet|Deployment]
    for obj_type, obj_type_camelcase in [
        ("daemonset", "DaemonSet"),
        ("statefulset", "StatefulSet"),
        ("deployment", "Deployment"),
    ]:
        if obj_name := context.get(k8s_ids[obj_type], {}).get(k8s_ids[obj_type]):
            title = f"{obj_type_camelcase} {obj_name}"
            add_vars.append((k8s_ids[obj_type], obj_name))
            host_name = "_".join([obj_type, cluster_name, namespace_name, obj_name])
            breadcrumb.append(
                BreadcrumbItem(
                    title,
                    makeuri_contextless(
                        request,
                        [("name", k8s_ids[obj_type]), ("host", host_name), *add_vars],
                    ),
                )
            )
            break
    if not obj_name:
        breadcrumb.append(BreadcrumbItem(title, makeuri(request, [("name", name)])))

    return breadcrumb
