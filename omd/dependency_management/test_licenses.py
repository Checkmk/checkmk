# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Check that every shipped dependency has a researched license."""

from pathlib import Path

import pyspdx
import pytest
from cyclonedx import (
    ComponentList,
    components_without_license,
    LicenseDB,
    unify_components,
)

_HERE = Path(__file__).parent


@pytest.fixture(name="automatically_researched_licenses", scope="session")
def _automatically_researched_licenses() -> LicenseDB:
    return LicenseDB.model_validate_json(
        (_HERE / "automatically_researched_licenses.json").read_bytes()
    )


@pytest.fixture(name="manually_researched_licenses", scope="session")
def _manually_researched_licenses() -> LicenseDB:
    return LicenseDB.model_validate_json((_HERE / "manually_researched_licenses.json").read_bytes())


def test_all_shipped_dependencies_have_a_researched_license(
    automatically_researched_licenses: LicenseDB,
    manually_researched_licenses: LicenseDB,
) -> None:
    components = ComponentList.model_validate_json(
        (_HERE / "list_of_dependencies.json").read_text()
    )

    # create_bom determines licenses on unified components, so a license
    # contributed by one instance of a purl (e.g. from the SBOM) covers the
    # others (e.g. from a lock file). Unify first to mirror that behaviour.
    unified = ComponentList(unify_components(components))
    missing = components_without_license(
        unified, automatically_researched_licenses, manually_researched_licenses
    )

    assert not missing, (
        f"{len(missing)} shipped dependencies have no researched license:\n"
        + "\n".join(f"  - {c.purl.purl_str()}" for c in sorted(missing, key=lambda c: c.ref))
        + "\n\nRun `bazel run //omd/dependency_management:research_licenses` to research them "
        "automatically and commit the updated automatically_researched_licenses.json. "
        "If automatic research fails, add the license to manually_researched_licenses.json."
    )


def test_licenses_are_spdx_compliant(
    automatically_researched_licenses: LicenseDB,
    manually_researched_licenses: LicenseDB,
) -> None:
    offenders = {}

    for purl, license_ in automatically_researched_licenses.root.items():
        try:
            pyspdx.validate(license_)
        except ValueError:
            offenders[purl] = license_

    for purl, license_ in manually_researched_licenses.root.items():
        try:
            pyspdx.validate(license_)
        except ValueError:
            offenders[purl] = license_

    assert not offenders, "Some researched licenses are not SPDX compliant:\n" + "\n".join(
        f"  - {purl.purl_str}: {license_}" for purl, license_ in offenders.items()
    )
