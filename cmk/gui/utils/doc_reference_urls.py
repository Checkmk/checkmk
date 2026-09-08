#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""URLs into the Checkmk documentation.

These need to know the running edition, so they stay out of the reference
definitions in cmk.web.utils.doc_references.
"""

import cmk.utils.paths
from cmk.ccc.version import __version__, Edition, edition, Version
from cmk.web.utils.doc_references import DocReference, DocReferenceUtm
from cmk.web.utils.urls import urlencode_vars


def get_docs_base_url(language: str) -> str:
    version = (
        "saas"
        if edition(cmk.utils.paths.omd_root) == Edition.CLOUD
        else Version.from_str(__version__).version_base or "master"
    )
    lang = "de" if language == "de" else "en"
    return f"https://docs.checkmk.com/{version}/{lang}"


def doc_reference_url(
    language: str,
    utm: DocReferenceUtm,
    doc_ref: DocReference | None = None,
) -> str:
    base = get_docs_base_url(language)
    version = Version.from_str(__version__).version_without_rc or "master"
    cmk_edition = edition(cmk.utils.paths.omd_root)
    query = urlencode_vars(
        [
            ("utm_source", "checkmk"),
            ("utm_medium", "app"),
            ("utm_campaign", utm.campaign),
            ("utm_content", utm.content),
            ("utm_term", f"{version}_{cmk_edition.short}"),
        ]
    )

    if doc_ref is None:
        return f"{base}?{query}"
    if "#" not in doc_ref.value:
        return f"{base}/{doc_ref.value}.html?{query}"
    page, anchor = doc_ref.value.split("#", 1)
    return f"{base}/{page}.html?{query}#{anchor}"
