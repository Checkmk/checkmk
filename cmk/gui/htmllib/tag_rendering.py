#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# Re-export from cmk.web for backward compatibility.
from cmk.web.htmllib.tag_rendering import HTMLContent as HTMLContent
from cmk.web.htmllib.tag_rendering import HTMLTagAttributes as HTMLTagAttributes
from cmk.web.htmllib.tag_rendering import HTMLTagAttributeValue as HTMLTagAttributeValue
from cmk.web.htmllib.tag_rendering import HTMLTagName as HTMLTagName
from cmk.web.htmllib.tag_rendering import HTMLTagValue as HTMLTagValue
from cmk.web.htmllib.tag_rendering import normalize_css_spec as normalize_css_spec
from cmk.web.htmllib.tag_rendering import render_element as render_element
from cmk.web.htmllib.tag_rendering import render_end_tag as render_end_tag
from cmk.web.htmllib.tag_rendering import render_start_tag as render_start_tag
