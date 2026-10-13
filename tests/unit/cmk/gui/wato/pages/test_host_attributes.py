#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""How the host edit dialog offers the relations field."""

import re
from collections.abc import Sequence

import pytest

from cmk.ccc.hostaddress import HostName
from cmk.ccc.site import SiteId
from cmk.gui.config import active_config
from cmk.gui.utils.host_relations import RelationLink
from cmk.gui.utils.output_funnel import output_funnel
from cmk.gui.wato.pages._host_attributes import configure_attributes, DialogIdent
from cmk.gui.watolib.host_attributes import (
    all_host_attributes,
    HostAttributes,
    store_relations,
)
from cmk.gui.watolib.hosts_and_folders import FolderTree, Host, HostsAndFoldersConfig


def _render(relations: Sequence[RelationLink], *, for_what: DialogIdent) -> str:
    tree = FolderTree(config=HostsAndFoldersConfig.from_config(active_config))
    root = tree.root_folder()
    attributes = HostAttributes(site=SiteId("NO_SITE"))
    store_relations(attributes, relations)
    os1 = Host(
        folder=root,
        host_name=HostName("os1"),
        attributes=attributes,
        cluster_nodes=None,
    )

    with output_funnel.plugged():
        configure_attributes(
            all_host_attributes(
                active_config.wato_host_attrs, active_config.tags.get_tag_groups_by_topic()
            ),
            new=False,
            hosts={"os1": os1},
            for_what=for_what,
            parent=root,
            aux_tags_by_tag=active_config.tags.get_aux_tags_by_tag(),
            config=active_config,
        )
        return output_funnel.drain()


@pytest.mark.usefixtures("request_context", "with_admin_login", "patch_theme")
def test_the_relations_field_is_offered_without_a_checkbox() -> None:
    rendered = _render(
        [{"kind": "management", "direction": "child", "host": HostName("mgmt-01")}], for_what="host"
    )

    assert '<div id="attr_entry_relations">' in rendered
    assert "mgmt-01" in rendered
    checkbox = re.search(r'<input[^>]*name="host_change_relations"[^>]*>', rendered)
    assert checkbox is not None
    assert 'type="hidden"' in checkbox.group(0)


@pytest.mark.usefixtures("request_context", "with_admin_login", "patch_theme")
def test_a_host_without_relations_still_gets_an_empty_field() -> None:
    rendered = _render([], for_what="host")

    assert '<div id="attr_entry_relations">' in rendered


@pytest.mark.usefixtures("request_context", "with_admin_login", "patch_theme")
def test_the_relations_field_is_not_offered_in_a_bulk_edit() -> None:
    rendered = _render(
        [{"kind": "management", "direction": "child", "host": HostName("mgmt-01")}], for_what="bulk"
    )

    assert "mgmt-01" not in rendered
    assert 'name="bulk_change_relations"' not in rendered
