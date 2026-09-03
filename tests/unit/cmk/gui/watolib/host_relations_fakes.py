#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""A host as the relation resolution and the export see it, without a folder tree behind it."""

from collections.abc import Mapping
from typing import cast

from cmk.ccc.hostaddress import HostName
from cmk.ccc.site import SiteId
from cmk.gui.watolib.host_attributes import HostAttributes
from cmk.gui.watolib.host_relations import RelatedHost


class FakeHost:
    """A host as ``resolve_all_relations`` sees it - it asks for nothing else.

    Satisfies :class:`RelatedHost`, so it needs no cast where the resolver is called.
    """

    def __init__(self, name: str, relations: object = None, site: str = "central") -> None:
        self._name = HostName(name)
        self._site = SiteId(site)
        self.attributes = cast(
            "HostAttributes", {} if relations is None else {"relations": relations}
        )

    def name(self) -> HostName:
        return self._name

    def site_id(self) -> SiteId:
        return self._site


def fake_hosts(**relations: object) -> Mapping[HostName, RelatedHost]:
    """The hosts named by the keyword arguments, each holding the relations given as its value."""
    return {HostName(name): FakeHost(name, value) for name, value in relations.items()}
