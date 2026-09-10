#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import re
from dataclasses import dataclass, field
from typing import Literal

from cmk.ccc.site import SiteId
from cmk.gui.quick_setup.v0_unstable.definitions import UniqueFormSpecIDStr
from cmk.gui.quick_setup.v0_unstable.type_defs import ParsedFormData
from cmk.gui.quick_setup.v0_unstable.widgets import FormSpecId
from cmk.gui.watolib.configuration_bundle_store import BundleId

from .helm import MonitoringSettings

CLUSTER = FormSpecId("cluster_configuration")
ADVANCED = FormSpecId("advanced_configuration")
HOST = FormSpecId("host_data")
CONNECTION = FormSpecId("connection")
PULL_URL = FormSpecId("pull_url")


@dataclass(frozen=True, kw_only=True)
class CommonSettings:
    bundle_id: BundleId
    release_name: str
    namespace: str
    monitoring: MonitoringSettings
    host_path: str
    site_id: SiteId


@dataclass(frozen=True, kw_only=True)
class PushSettings:
    common: CommonSettings
    receiver_host: str = ""
    receiver_host_override: str | None = None


@dataclass(frozen=True, kw_only=True)
class PullSettings:
    common: CommonSettings
    shared_secret: str = field(repr=False)
    node_port: int = 30050
    tls_secret_name: str = ""
    base_url: str = ""


type Settings = PushSettings | PullSettings


def read_common_settings(data: ParsedFormData, *, default_site: SiteId) -> CommonSettings:
    """Read cluster and host settings, even before a connection mode has been chosen."""
    cluster = data[CLUSTER]
    advanced = data[ADVANCED]
    host = data[HOST]
    match host["host_name_source"]:
        case ("cluster_name", _):
            host_name = cluster["cluster_name"]
        case ("explicit", str() as name):
            host_name = name
        case _:
            raise ValueError("Invalid host name selection")

    bundle_id = BundleId(data[FormSpecId(UniqueFormSpecIDStr)]["bundle_id"])
    release_name = bundle_id.lower().replace("_", "-")
    if len(release_name) > 53 or not re.fullmatch(r"[a-z0-9](?:[-a-z0-9]*[a-z0-9])?", release_name):
        raise ValueError(
            "Use a configuration name that becomes a valid Helm release name of at most 53 characters"
        )

    namespace_mode, patterns = cluster.get("namespaces", ("include", []))
    match advanced.get("annotations"):
        case ("all", _):
            annotations: Literal["none", "all"] | tuple[Literal["pattern"], str] = "all"
        case ("pattern", str() as pattern):
            annotations = ("pattern", pattern)
        case None:
            annotations = "none"
        case _:
            raise ValueError("Invalid annotation import selection")

    return CommonSettings(
        bundle_id=bundle_id,
        release_name=release_name,
        namespace=cluster["namespace"],
        host_path=host["host_path"],
        site_id=SiteId(data.get(FormSpecId("site"), {}).get("site_selection", default_site)),
        monitoring=MonitoringSettings(
            cluster_name=cluster["cluster_name"],
            host_name=host_name,
            host_kinds=frozenset(cluster["host_kinds"]),
            namespaces=(namespace_mode, tuple(patterns)),
            annotations=annotations,
            excluded_node_roles=tuple(advanced["excluded_node_roles"]),
        ),
    )


def read_settings(data: ParsedFormData, *, default_site: SiteId) -> Settings:
    """Read settings for the selected mode; the final pull URL may still be absent."""
    if CONNECTION not in data:
        raise ValueError("Choose a connection mode before preparing or saving the deployment")
    common = read_common_settings(data, default_site=default_site)
    mode, connection = data[CONNECTION]
    match mode:
        case "push":
            return PushSettings(
                common=common,
                receiver_host=connection.get("receiver_host", ""),
                receiver_host_override=connection.get("receiver_host_override"),
            )
        case "pull":
            return PullSettings(
                common=common,
                shared_secret=connection.get("shared_secret", ""),
                node_port=connection.get("service_exposure", ("node_port", 30050))[1],
                tls_secret_name=connection.get("tls_secret_name", ""),
                base_url=data.get(PULL_URL, {}).get("base_url", ""),
            )
        case _:
            raise ValueError("Invalid connection mode")
