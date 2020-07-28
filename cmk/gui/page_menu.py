#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Page menu processing

Cares about the page navigation of our GUI. This is the menu bar that can be found on top of each
page. It is meant to be used for page wide actions and navigation to other related pages.

The hierarchy here is:

    PageMenu > PageMenuDropdown > PageMenuTopic > PageMenuEntry > ABCPageMenuItem
"""

import abc
import json
from dataclasses import dataclass, field
from typing import List, Iterator, Optional


@dataclass
class Link:
    """Group of attributes used for linking"""
    url: Optional[str] = None
    target: Optional[str] = None
    onclick: Optional[str] = None


class ABCPageMenuItem(metaclass=abc.ABCMeta):
    """Base class for all page menu items of the page menu
    There can be different item types, like regular links, search fields, ...
    """


@dataclass
class PageMenuLink(ABCPageMenuItem):
    """A generic hyper link to other pages"""
    link: Link


def make_simple_link(url: str) -> PageMenuLink:
    return PageMenuLink(Link(url=url))


def make_external_link(url: str) -> PageMenuLink:
    return PageMenuLink(Link(url=url, target="_blank"))


def make_javascript_link(javascript: str) -> PageMenuLink:
    return PageMenuLink(Link(onclick=javascript))


def make_form_submit_link(form_name: str, button_name: str) -> PageMenuLink:
    return make_javascript_link("cmk.page_menu.form_submit(%s, %s)" %
                                (json.dumps(form_name), json.dumps(button_name)))


@dataclass
class PageMenuEntry:
    """Representing an entry in the menu, holding the ABCPageMenuItem to be displayed"""
    name: str
    title: str
    description: str
    icon_name: str
    item: ABCPageMenuItem
    is_enabled: bool = True
    is_advanced: bool = False
    is_list_entry: bool = True
    is_shortcut: bool = False
    is_suggested: bool = False


@dataclass
class PageMenuTopic:
    """A dropdown is populated with multiple topics which hold the actual entries"""
    title: str
    entries: List[PageMenuEntry] = field(default_factory=list)


@dataclass
class PageMenuDropdown:
    """Each dropdown in the page menu is represented by this structure"""
    name: str
    title: str
    topics: List[PageMenuTopic] = field(default_factory=list)

    @property
    def any_advanced_entries(self) -> bool:
        return any(entry.is_advanced for topic in self.topics for entry in topic.entries)


@dataclass
class PageMenu:
    """Representing the whole menu of the page"""
    dropdowns: List[PageMenuDropdown] = field(default_factory=list)

    @property
    def shortcuts(self) -> Iterator[PageMenuEntry]:
        for dropdown in self.dropdowns:
            for topic in dropdown.topics:
                for entry in topic.entries:
                    if entry.is_shortcut:
                        yield entry

    @property
    def suggestions(self) -> Iterator[PageMenuEntry]:
        for entry in self.shortcuts:
            if entry.is_suggested:
                yield entry

    @property
    def has_suggestions(self) -> bool:
        return any(True for _s in self.suggestions)
