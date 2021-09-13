#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    import cmk.gui.htmllib as htmllib
    from cmk.gui.http import Request

# .
#   .--Display Opts.-------------------------------------------------------.
#   |       ____  _           _                ___        _                |
#   |      |  _ \(_)___ _ __ | | __ _ _   _   / _ \ _ __ | |_ ___          |
#   |      | | | | / __| '_ \| |/ _` | | | | | | | | '_ \| __/ __|         |
#   |      | |_| | \__ \ |_) | | (_| | |_| | | |_| | |_) | |_\__ \_        |
#   |      |____/|_|___/ .__/|_|\__,_|\__, |  \___/| .__/ \__|___(_)       |
#   |                  |_|            |___/        |_|                     |
#   +----------------------------------------------------------------------+
#   | Display options are flags that control which elements of a view      |
#   | should be displayed (buttons, sorting, etc.). They can be  specified |
#   | via the URL variable display_options.                                |
#   | An upper-case char means enabled, lower-case means disabled.         |
#   '----------------------------------------------------------------------'


class DisplayOptions:
    H = "H"  # The HTML header and body-tag (containing the tags <HTML> and <BODY>)
    T = "T"  # The title line showing the header and the logged in user
    B = "B"  # The blue context buttons that link to other views
    F = "F"  # The button for using filters
    C = "C"  # The button for using commands and all icons for commands (e.g. the reschedule icon)
    O = "O"  # The view options number of columns and refresh
    D = "D"  # The Display button, which contains column specific formatting settings
    E = "E"  # The button for editing the view
    Z = "Z"  # The footer line, where refresh: 30s is being displayed
    R = "R"  # The auto-refreshing in general (browser reload)
    S = "S"  # The playing of alarm sounds (on critical and warning services)
    U = "U"  # Load persisted user row selections
    I = "I"  # All hyperlinks pointing to other views
    X = "X"  # All other hyperlinks (pointing to external applications like PNP, WATO or others)
    M = "M"  # If this option is not set, then all hyperlinks are targeted to the HTML frame
    # with the name main. This is useful when using views as elements in the dashboard.
    L = "L"  # The column title links in multisite views
    W = "W"  # The limit and livestatus error message in views
    N = "N"  # Switching to inline display mode when disabled
    # (e.g. no padding round page)

    @classmethod
    def all_on(cls) -> str:
        opts = ""
        for k in sorted(cls.__dict__.keys()):
            if len(k) == 1:
                opts += k
        return opts

    @classmethod
    def all_off(cls) -> str:
        return cls.all_on().lower()

    def __init__(self) -> None:
        self.options: str = self.all_off()
        self.title_options: Optional[str] = None

    def load_from_html(self, request: Request, html: htmllib.html) -> None:
        # Parse display options and
        if html.output_format == "html":
            options = request.get_ascii_input_mandatory("display_options", "")
        else:
            options = self.all_off()

        # Remember the display options in the object for later linking etc.
        self.options = self._merge_with_defaults(options)

        # This is needed for letting only the data table reload. The problem is that
        # the data table is re-fetched via javascript call using special display_options
        # but these special display_options must not be used in links etc. So we use
        # a special var _display_options for defining the display_options for rendering
        # the data table to be reloaded. The contents of "display_options" are used for
        # linking to other views.
        if request.has_var("_display_options"):
            self.options = self._merge_with_defaults(
                request.get_ascii_input_mandatory("_display_options", "")
            )

        # But there is one special case: Links to other views (sorter header links, painter column
        # links). These links need to know about the provided display_option parameter. The links
        # could use "display_options.options" but this contains the implicit options which should
        # not be added to the URLs. So the real parameters need to be preserved for this case.
        self.title_options = request.get_ascii_input("display_options")

        # If display option 'M' is set, then all links are targetet to the 'main'
        # frame. Also the display options are removed since the view in the main
        # frame should be displayed in standard mode.
        if self.disabled(self.M):
            html.set_link_target("main")
            request.del_var("display_options")

    # If all display_options are upper case assume all not given values default
    # to lower-case. Vice versa when all display_options are lower case.
    # When the display_options are mixed case assume all unset options to be enabled
    def _merge_with_defaults(self, opts: str) -> str:
        do_defaults = self.all_off() if opts.isupper() else self.all_on()
        for c in do_defaults:
            if c.lower() not in opts.lower():
                opts += c
        return opts

    def enabled(self, opt: str) -> bool:
        return opt in self.options

    def disabled(self, opt: str) -> bool:
        return opt not in self.options
