#!/usr/bin/env python2
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import time

import cmk.gui.config as config
from cmk.gui.htmllib import HTML
from cmk.gui.i18n import _
from cmk.gui.globals import html
from cmk.gui.valuespec import (
    TextAreaUnicode,
    TextAscii,
)


class RuleComment(TextAreaUnicode):
    def __init__(self, **kwargs):
        kwargs.setdefault("title", _("Comment"))
        kwargs.setdefault(
            "help",
            _("An optional comment that may be used to explain the purpose of this object. "
              "The comment is only visible in this dialog and may help other users "
              "understanding the intentions of the configured attributes."))
        kwargs.setdefault("rows", 4)
        kwargs.setdefault("cols", 80)
        super(RuleComment, self).__init__(**kwargs)

    def render_input(self, varprefix, value):
        html.open_div(style="white-space: nowrap;")

        super(RuleComment, self).render_input(varprefix, value)

        date_and_user = "%s %s: " % (time.strftime("%F", time.localtime()), config.user.id)

        html.nbsp()
        html.icon_button(None,
                         title=_("Prefix date and your name to the comment"),
                         icon="insertdate",
                         onclick="cmk.valuespecs.rule_comment_prefix_date_and_user(this, '%s');" %
                         date_and_user)
        html.close_div()


def DocumentationURL():
    return TextAscii(
        title=_("Documentation URL"),
        help=HTML(
            _("An optional URL pointing to documentation or any other page. This will be displayed "
              "as an icon %s and open a new page when clicked. "
              "You can use either global URLs (beginning with <tt>http://</tt>), absolute local urls "
              "(beginning with <tt>/</tt>) or relative URLs (that are relative to <tt>check_mk/</tt>)."
             ) % html.render_icon("url")),
        size=80,
    )
