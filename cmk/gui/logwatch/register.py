#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.pages import PageRegistry
from cmk.gui.search import MatchItemGeneratorRegistry
from cmk.gui.watolib.mode import ModeRegistry
from cmk.gui.watolib.rulespecs import RulespecRegistry

from ._page import register as _register_page
from ._rulespecs import register as _register_rulespecs


def register(
    page_registry: PageRegistry,
    rulespec_registry: RulespecRegistry,
    mode_registry: ModeRegistry,
    match_item_generator_registry: MatchItemGeneratorRegistry,
) -> None:
    _register_page(page_registry)
    _register_rulespecs(rulespec_registry, mode_registry, match_item_generator_registry)
