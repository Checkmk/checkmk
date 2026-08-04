#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="explicit-override"

"""Plain GUI pages that want an entry in a main menu.

Views, dashboards and pagetypes reach a main menu through their own stores. A
plain `Page` has no store, so the shipped ones hardcode themselves in the
sidebar snap-in that builds the menu - which is edition-independent and must
therefore not import a non-free feature plugin.

A feature plugin registers here instead. Edition gating comes for free: a
plugin only loads in the editions that ship it.
"""

from collections.abc import Callable
from dataclasses import dataclass, field

import cmk.ccc.plugin_registry
from cmk.gui.type_defs import Visual


@dataclass(frozen=True)
class MainMenuPage:
    """A page's menu entry.

    `visual_spec` is a callable rather than a value so its title is translated
    per request, in the visitor's language.
    """

    ident: str
    visual_spec: Callable[[], Visual]
    is_permitted: Callable[[], bool] = field(default=lambda: True)


class MainMenuPageRegistry(cmk.ccc.plugin_registry.Registry[MainMenuPage]):
    def plugin_name(self, instance: MainMenuPage) -> str:
        return instance.ident


main_menu_page_registry = MainMenuPageRegistry()
