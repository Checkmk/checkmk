#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterable

from cmk.inventory_ui.v1_unstable import (
    Alignment,
    BackgroundColor,
    BoolField,
    DecimalNotation,
    LabelColor,
    Node,
    NumberField,
    StrictPrecision,
    Table,
    TextField,
    Title,
    Unit,
    View,
)

UNIT_COUNT = Unit(DecimalNotation(""), StrictPrecision(0))
UNIT_PERCENTAGE = Unit(DecimalNotation("%"))


def _style_service_status(value: str) -> Iterable[Alignment | BackgroundColor | LabelColor]:
    yield Alignment.CENTER
    match value:
        case "running":
            yield LabelColor.BLACK
            yield BackgroundColor.GREEN
        case "stopped":
            yield LabelColor.WHITE
            yield BackgroundColor.DARK_RED
        case _:
            yield LabelColor.WHITE
            yield BackgroundColor.DARK_GRAY


node_software_applications_check_mk = Node(
    name="software_applications_check_mk",
    path=["software", "applications", "check_mk"],
    title=Title("Checkmk"),
    attributes={
        "num_hosts": TextField(Title("#Hosts")),
        "num_services": TextField(Title("#Services")),
    },
)

node_software_applications_check_mk_sites = Node(
    name="software_applications_check_mk_sites",
    path=["software", "applications", "check_mk", "sites"],
    title=Title("Checkmk sites"),
    table=Table(
        view=View(name="invcmksites", title=Title("Checkmk sites")),
        columns={
            "site": TextField(Title("Site")),
            "used_version": TextField(Title("Version")),
            "num_hosts": NumberField(Title("#Hosts"), render=UNIT_COUNT),
            "num_services": NumberField(Title("#Services"), render=UNIT_COUNT),
            "check_mk_helper_usage": NumberField(Title("CMK helper usage"), render=UNIT_PERCENTAGE),
            "fetcher_helper_usage": NumberField(
                Title("Fetcher helper usage"), render=UNIT_PERCENTAGE
            ),
            "checker_helper_usage": NumberField(
                Title("Checker helper usage"), render=UNIT_PERCENTAGE
            ),
            "livestatus_usage": NumberField(Title("Livestatus usage"), render=UNIT_PERCENTAGE),
            "check_helper_usage": NumberField(Title("Actual helper usage"), render=UNIT_PERCENTAGE),
            "autostart": BoolField(Title("Autostart")),
            "apache": TextField(Title("Apache status"), style=_style_service_status),
            "cmc": TextField(Title("CMC status"), style=_style_service_status),
            "crontab": TextField(Title("Crontab status"), style=_style_service_status),
            "dcd": TextField(Title("DCD status"), style=_style_service_status),
            "liveproxyd": TextField(Title("Liveproxyd status"), style=_style_service_status),
            "mkeventd": TextField(Title("MKEvent status"), style=_style_service_status),
            "mknotifyd": TextField(Title("MKNotify status"), style=_style_service_status),
            "rrdcached": TextField(Title("RRDCached status"), style=_style_service_status),
            "stunnel": TextField(Title("STunnel status"), style=_style_service_status),
            "xinetd": TextField(Title("XInetd status"), style=_style_service_status),
            "nagios": TextField(Title("Nagios status"), style=_style_service_status),
            "npcd": TextField(Title("NPCD status"), style=_style_service_status),
        },
    ),
)

node_software_applications_check_mk_versions = Node(
    name="software_applications_check_mk_versions",
    path=["software", "applications", "check_mk", "versions"],
    title=Title("Checkmk versions"),
    table=Table(
        view=View(name="invcmkversions", title=Title("Checkmk versions")),
        columns={
            "version": TextField(Title("Version")),
            "number": TextField(Title("Number")),
            "edition": TextField(Title("Edition")),
            "demo": BoolField(Title("Demo")),
            "num_sites": NumberField(Title("#Sites"), render=UNIT_COUNT),
        },
    ),
)

node_software_applications_check_mk_cluster = Node(
    name="software_applications_check_mk_cluster",
    path=["software", "applications", "check_mk", "cluster"],
    title=Title("Cluster"),
    attributes={
        "is_cluster": BoolField(Title("Cluster host")),
    },
)

node_software_applications_check_mk_cluster_nodes = Node(
    name="software_applications_check_mk_cluster_nodes",
    path=["software", "applications", "check_mk", "cluster", "nodes"],
    title=Title("Nodes"),
    table=Table(
        columns={
            "name": TextField(Title("Node name")),
        },
    ),
)
