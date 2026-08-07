#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from dataclasses import dataclass
from typing import NewType, Self

HostName = NewType("HostName", str)
ServiceName = NewType("ServiceName", str)
SiteID = NewType("SiteID", str)


class MetricName(str):
    # A metric name normalised to PNP4Nagios format: a str subclass whose construction is a projection
    # (non-injective). The raw name is pnp-cleaned, so a name carrying spaces / ":" / "/" / "\" / NUL is
    # mapped to its canonical RRD identifier.
    def __new__(cls, text: str) -> Self:
        # An embedded null byte is mapped to "_" like the other path-hostile chars: it would otherwise
        # make open() raise "ValueError: embedded null byte" when the RRD is created.
        return super().__new__(
            cls,
            text.replace(" ", "_")
            .replace(":", "_")
            .replace("/", "_")
            .replace("\\", "_")
            .replace("\x00", "_"),
        )


@dataclass(frozen=True, kw_only=True)
class Service:
    # The monitoring site the service lives on, when known. Carried through matching so the metrics
    # built for the service can be tagged with it; None means "site not (yet) known".
    site_id: SiteID | None = None
    host_name: HostName
    service_name: ServiceName
