#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Optional, List
from dataclasses import dataclass, asdict
from livestatus import SiteId

from cmk.gui import config
import cmk.gui.sites as sites
from cmk.gui.globals import request
from cmk.gui.i18n import _
from cmk.gui.utils.urls import makeuri
from cmk.gui.valuespec import Dictionary
from cmk.gui.pages import page_registry, AjaxPage
from cmk.gui.plugins.dashboard import dashlet_registry
from cmk.gui.figures import ABCFigureDashlet, ABCDataGenerator


@dataclass
class Part:
    title: str
    color: Optional[str]
    count: int


@dataclass
class Element:
    title: str
    link: Optional[str]
    state: Optional[str]
    total: Part
    parts: List[Part]

    def serialize(self):
        serialized = asdict(self)
        serialized["total"] = asdict(self.total)
        serialized["parts"] = [asdict(p) for p in self.parts]
        return serialized


class SiteOverviewDashletDataGenerator(ABCDataGenerator):
    @classmethod
    def vs_parameters(cls):
        return Dictionary(title=_("Properties"), render="form", optional_keys=False, elements=[])

    @classmethod
    def generate_response_data(cls, properties, context, settings):
        site_id = context.get("site", {}).get("site")
        render_mode = "hosts" if site_id else "sites"

        if render_mode == "hosts":
            assert site_id is not None
            elements = cls._collect_hosts_data(SiteId(site_id))
        elif render_mode == "sites":
            elements = cls._collect_sites_data()
        else:
            raise NotImplementedError()

        return {
            # TODO: Get the correct dashlet title. This needs to use the general dashlet title
            # calculation. We somehow have to get the title from
            # cmk.gui.dashboard._render_dashlet_title.
            "title": _("Site overview"),
            "render_mode": render_mode,
            "plot_definitions": [],
            "data": [e.serialize() for e in elements],
        }

    @classmethod
    def _collect_hosts_data(cls, site_id: SiteId) -> List[Element]:
        return []

    @classmethod
    def _collect_sites_data(cls) -> List[Element]:
        sites.update_site_states_from_dead_sites()
        elements = []
        for site_id, _sitealias in config.sorted_sites():
            site_spec = config.site(site_id)
            site_status = sites.states().get(site_id, sites.SiteStatus({}))
            state: Optional[str] = site_status.get("state")
            if state is None or state == "disabled":
                link = None
            else:
                link = makeuri(request, [
                    ("site", site_id),
                ])
            elements.append(
                Element(
                    title=site_spec["alias"],
                    link=link,
                    state=state,
                    parts=[
                        Part(
                            title="",
                            count=0,
                            color="",
                        ),
                        Part(
                            title="",
                            count=0,
                            color="",
                        ),
                    ],
                    total=Part(
                        title=_("Total"),
                        count=0,
                        color="",
                    ),
                ))

        return elements + test_elements()


def test_elements():
    test_sites = [
        (
            "Hamburg",
            "ham",
            (
                240,  # critical hosts
                111,  # hosts with unknowns
                100,  # hosts with warnings
                50,  # hosts in downtime
                12335,  # OK
            )),
        ("München", "muc", (
            0,
            1,
            5,
            0,
            100,
        )),
        ("Darmstadt", "dar", (
            305,
            10,
            4445,
            0,
            108908,
        )),
        ("Berlin", "ber", (
            0,
            4500,
            0,
            6000,
            3101101,
        )),
        ("Essen", "ess", (
            40024,
            23,
            99299,
            60,
            2498284,
        )),
        ("Gutstadt", "gut", (
            0,
            0,
            0,
            0,
            668868,
        )),
        ("Schlechtstadt", "sch", (
            548284,
            0,
            0,
            0,
            0,
        )),
    ]
    elements = []
    for site_name, site_id, states in test_sites:
        parts = []
        total = 0
        for title, color, count in zip([
                "Critical hosts",
                "Hosts with unknowns",
                "Hosts with warnings",
                "Hosts in downtime",
                "OK/UP",
        ], ["#ff0000", "#ff8800", "#ffff00", "#00aaff", "#13d38910"], states):
            parts.append(Part(title=title, color=color, count=count))
            total += count

        elements.append(
            Element(
                title=site_name,
                link=makeuri(request, [("site", site_id)]),
                state=None,
                parts=parts,
                total=Part(title="Total", color=None, count=total),
            ))
    return elements


@page_registry.register_page("ajax_site_overview_dashlet_data")
class SitesDashletData(AjaxPage):
    def page(self):
        return SiteOverviewDashletDataGenerator.generate_response_from_request()


@dashlet_registry.register
class SiteOverviewDashlet(ABCFigureDashlet):
    @classmethod
    def type_name(cls):
        return "site_overview"

    @classmethod
    def title(cls):
        return _("Site overview")

    @classmethod
    def description(cls):
        return _("Displays either sites and states or hosts and states of a site")

    @classmethod
    def data_generator(cls):
        return SiteOverviewDashletDataGenerator

    @classmethod
    def single_infos(cls):
        return []

    def show(self):
        self.js_dashlet("ajax_site_overview_dashlet_data.py")
