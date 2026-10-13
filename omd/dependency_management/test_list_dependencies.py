# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Check how purls from Bazel package metadata are turned into components."""

from cyclonedx import PUrl
from list_dependencies import PackageMetadata


def test_wheel_artifact_qualifiers_are_dropped_from_pypi_purls() -> None:
    metadata = PackageMetadata.model_validate(
        {
            "attributes": {},
            "label": "@@rules_python++pip+cmk_requirements_314_aiohttp//:package_metadata",
            "purl": (
                "pkg:pypi/aiohttp@3.14.3"
                "?repository_url=https://pypi.org/simple/aiohttp/"
                "&file_name=aiohttp-3.14.3-cp314-cp314-manylinux2014_x86_64.whl"
            ),
        }
    )

    assert metadata.component().purl == PUrl(type_="pypi", name="aiohttp", version="3.14.3")


def test_qualifiers_of_other_package_types_are_kept() -> None:
    metadata = PackageMetadata.model_validate(
        {
            "attributes": {},
            "label": "@@perl-modules+//:Perl-OSType-1.008.-package_metadata",
            "purl": "pkg:cpan/Perl-OSType@1.008?repository_url=https://cpan.metacpan.org/",
        }
    )

    assert metadata.component().purl == PUrl(
        type_="cpan",
        name="Perl-OSType",
        version="1.008",
        qualifiers=frozenset({("repository_url", "https://cpan.metacpan.org/")}),
    )
