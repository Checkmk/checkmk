# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Check how package URLs are serialized."""

from cyclonedx import PUrl


def test_purl_str_sorts_the_qualifiers_by_key() -> None:
    purl = PUrl(
        type_="deb",
        namespace="ubuntu",
        name="libc6",
        version="2.39-0ubuntu8",
        qualifiers=frozenset(
            {
                ("repository_url", "http://archive.ubuntu.com/"),
                ("arch", "amd64"),
                ("distro", "noble"),
            }
        ),
    )

    assert purl.purl_str() == (
        "pkg:deb/ubuntu/libc6@2.39-0ubuntu8"
        "?arch=amd64&distro=noble&repository_url=http%3A%2F%2Farchive.ubuntu.com%2F"
    )
