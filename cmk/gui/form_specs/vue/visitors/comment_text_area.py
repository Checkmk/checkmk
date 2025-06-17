#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from dataclasses import asdict

from cmk.gui.form_specs.vue.visitors.multiline_text import MultilineTextVisitor
from cmk.gui.i18n import _
from cmk.gui.logged_in import user

from cmk.shared_typing import vue_formspec_components as shared_type_defs

from ._type_defs import InvalidValue


class CommentTextAreaVisitor(MultilineTextVisitor):
    def _to_vue(
        self, parsed_value: str | InvalidValue[str]
    ) -> tuple[shared_type_defs.CommentTextArea, str]:
        multiline_text, value = super()._to_vue(parsed_value)
        multiline_text_args = asdict(multiline_text)
        multiline_text_args["type"] = "comment_text_area"
        return (
            shared_type_defs.CommentTextArea(
                **multiline_text_args,
                user_name=user.id or "",
                i18n=shared_type_defs.CommentTextAreaI18n(
                    prefix_date_and_comment=_("Prefix date and your name to the comment")
                ),
            ),
            value,
        )
