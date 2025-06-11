#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.breadcrumb import Breadcrumb, BreadcrumbItem, make_main_menu_breadcrumb
from cmk.gui.http import request
from cmk.gui.main_menu import main_menu_registry
from cmk.gui.utils.urls import makeuri
from cmk.gui.visuals.type import visual_type_registry


def visual_page_breadcrumb(what: str, title: str, page_name: str) -> Breadcrumb:
    breadcrumb = make_main_menu_breadcrumb(main_menu_registry.menu_customize())

    list_title = visual_type_registry[what]().plural_title
    breadcrumb.append(BreadcrumbItem(title=list_title.title(), url="edit_%s.py" % what))

    if page_name == "list":  # The list is the parent of all others
        return breadcrumb

    breadcrumb.append(BreadcrumbItem(title=title, url=makeuri(request, [])))
    return breadcrumb
