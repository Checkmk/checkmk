# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Check that every shipped dependency has a researched license."""

from pathlib import Path

from cyclonedx import (
    ComponentList,
    components_without_license,
    LicenseDB,
    unify_components,
)

_HERE = Path(__file__).parent


def test_all_shipped_dependencies_have_a_researched_license() -> None:
    components = ComponentList.model_validate_json(
        (_HERE / "list_of_dependencies.json").read_text()
    )
    automatically_researched = LicenseDB.model_validate_json(
        (_HERE / "automatically_researched_licenses.json").read_bytes()
    )
    manually_researched = LicenseDB.model_validate_json(
        (_HERE / "manually_researched_licenses.json").read_bytes()
    )

    # create_bom determines licenses on unified components, so a license
    # contributed by one instance of a purl (e.g. from the SBOM) covers the
    # others (e.g. from a lock file). Unify first to mirror that behaviour.
    unified = ComponentList(unify_components(components))
    missing = components_without_license(unified, automatically_researched, manually_researched)

    assert not missing, (
        f"{len(missing)} shipped dependencies have no researched license:\n"
        + "\n".join(f"  - {c.purl.purl_str()}" for c in sorted(missing, key=lambda c: c.ref))
        + "\n\nRun `bazel run //omd/dependency_management:research_licenses` to research them "
        "automatically and commit the updated automatically_researched_licenses.json. "
        "If automatic research fails, add the license to manually_researched_licenses.json."
    )
