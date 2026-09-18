# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Check how package URLs are normalized and serialized."""

import pytest
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


# fmt: off
@pytest.mark.parametrize("spelling", [
    pytest.param("pkg:pypi/Charset-Normalizer@3.3.2", id="upper case"),
    pytest.param("pkg:pypi/charset_normalizer@3.3.2", id="underscore"),
    pytest.param("pkg:pypi/charset.normalizer@3.3.2", id="dot"),
    pytest.param("pkg:pypi/charset._-normalizer@3.3.2", id="run of separators"),
    pytest.param("pkg:PyPI/Charset_Normalizer@3.3.2", id="upper case type"),
])
# fmt: on
def test_pypi_purls_are_equal_however_the_name_is_spelled(spelling: str) -> None:
    assert PUrl.from_str(spelling) == PUrl(
        type_="pypi", name="charset-normalizer", version="3.3.2"
    )


def test_pypi_purls_are_serialized_with_the_canonical_name() -> None:
    assert PUrl.from_str("pkg:pypi/PyInstaller@3.6").purl_str() == "pkg:pypi/pyinstaller@3.6"


def test_names_of_other_package_types_keep_their_spelling() -> None:
    assert PUrl.from_str("pkg:cpan/Perl-OSType@1.008") == PUrl(
        type_="cpan", name="Perl-OSType", version="1.008"
    )
