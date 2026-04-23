#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# Re-export from cmk.web for backward compatibility. All existing cmk.gui callers
# continue to work unchanged.

from cmk.web.utils.escaping import (
    EscapableEntity,
    escape_attribute,
    escape_text,
    escape_to_html_permissive,
    replace_anchor_tags_with_urls,
    replace_br_with_newlines,
    strip_scripts,
    strip_tags,
    strip_tags_for_tooltip,
)

__all__ = [
    "EscapableEntity",
    "escape_attribute",
    "escape_text",
    "escape_to_html_permissive",
    "replace_anchor_tags_with_urls",
    "replace_br_with_newlines",
    "strip_scripts",
    "strip_tags",
    "strip_tags_for_tooltip",
]
