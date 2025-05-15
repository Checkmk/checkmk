#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from cmk.gui.openapi.framework.model.base_models import LinkModel
from cmk.gui.openapi.framework.model.constructors import generate_links
from cmk.gui.openapi.restful_objects.constructors import expand_rel


def test_generate_links_default_links() -> None:
    links = generate_links("host", "example-host")
    relations = {link.rel for link in links}
    assert relations == {
        "self",
        "urn:org.restfulobjects:rels/delete",
        "urn:org.restfulobjects:rels/update",
    }
    assert len(relations) == len(links), "Expected unique link relations"


def test_generate_links_no_editable() -> None:
    links = generate_links("host", "example-host", editable=False)
    update_links = [link for link in links if link.rel == expand_rel(".../update")]
    assert len(update_links) == 0


def test_generate_links_no_deletable() -> None:
    links = generate_links("host", "example-host", deletable=False)
    delete_links = [link for link in links if link.rel == expand_rel(".../delete")]
    assert len(delete_links) == 0


def test_generate_links_extra_links() -> None:
    extra = LinkModel(
        rel=expand_rel(".../extra"),
        href="/extra",
        domainType="link",
        method="GET",
        type="application/json",
    )
    links = generate_links("host", "example-host", extra_links=[extra])
    extra_links = [link for link in links if link.rel == expand_rel(".../extra")]
    assert len(extra_links) == 1
    assert extra_links[0] == extra


def test_generate_links_extra_links_multiple() -> None:
    extra_1 = LinkModel(
        rel=expand_rel(".../extra"),
        href="/extra_1",
        domainType="link",
        method="GET",
        type="application/json",
    )
    extra_2 = LinkModel(
        rel=expand_rel(".../extra"),
        href="/extra_2",
        domainType="link",
        method="GET",
        type="application/json",
    )
    links = generate_links("host", "example-host", extra_links=[extra_1, extra_2])
    extra_links = [link for link in links if link.rel == expand_rel(".../extra")]
    assert len(extra_links) == 2
    extra_hrefs = {link.href for link in extra_links}
    assert len(extra_hrefs) == 2, "Expected unique hrefs for extra links"
    assert extra_hrefs == {extra_1.href, extra_2.href}


def test_generate_links_custom_self() -> None:
    self = LinkModel(rel="self", href=".", domainType="link", method="GET", type="application/json")
    links = generate_links(
        "host",
        "example-host",
        self_link=self,
    )
    self_links = [link for link in links if link.rel == "self"]
    assert len(self_links) == 1
    assert self_links[0] == self
