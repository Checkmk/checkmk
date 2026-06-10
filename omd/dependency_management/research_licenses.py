# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote

import pyspdx
import requests
from cyclonedx import Component, ComponentList, components_without_license, LicenseDB, SPDXId

TIMEOUT = 60

# crates.io rejects requests with a generic/library User-Agent (returns 403).
# Its crawler policy requires a descriptive UA identifying the caller with a
# contact address. See https://crates.io/data-access
_CRATES_IO_USER_AGENT = "checkmk-license-research (https://checkmk.com; feedback@checkmk.com)"


class NoLicenseFound(Exception):
    pass


@dataclass(frozen=True)
class _Args:
    dep_list: Path
    out: Path


def _parse_args() -> _Args:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dependencies", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)

    args = parser.parse_args()
    return _Args(
        dep_list=args.dependencies,
        out=args.out,
    )


def _is_valid_spdx_id(license_id: str) -> bool:
    try:
        pyspdx.validate(license_id)
        return True
    except ValueError:
        return False


def research_cargo_license(component: Component) -> SPDXId:
    """retrieve license from crates.io (aka cargo)"""

    assert component.purl.type_ == "cargo"

    url = f"https://crates.io/api/v1/crates/{component.purl.name}/{component.purl.version}"
    response = requests.get(url, timeout=TIMEOUT, headers={"User-Agent": _CRATES_IO_USER_AGENT})
    response.raise_for_status()

    license_ = response.json()["version"].get("license")

    if license_ is None:
        raise NoLicenseFound(f"Crate {component.purl.purl_str()} has no license in {url!r}")

    if _is_valid_spdx_id(license_):
        return SPDXId(license_)

    # Crates often has the notation of MIT/Apache-2.0
    # See:
    #   - https://github.com/rust-lang/cargo/issues/2039
    #   - https://github.com/nexB/scancode-toolkit/issues/2516
    # I'd say AND is stricter than OR therefore I assume all LicenseA/LicenseB
    # projects to be LicenseA AND LicenseB licensed. Hopefully crate.io improves in
    # that regard soon.

    if "/" in license_ and _is_valid_spdx_id(license_.replace("/", " AND ")):
        return SPDXId(license_.replace("/", " AND "))

    raise NoLicenseFound(f"Crate {component.purl.purl_str()} has no valid SPDX license: {license_}")


def research_npm_license(component: Component) -> SPDXId:
    """retrieve license from npm"""

    assert component.purl.type_ == "npm"

    url = f"https://registry.npmjs.org/{component.purl.namespace + '/' if component.purl.namespace else ''}{component.purl.name}/{component.purl.version}"
    response = requests.get(url, timeout=TIMEOUT)
    response.raise_for_status()

    license_ = response.json().get("license")

    if license_ is None:
        raise NoLicenseFound(f"Package {component.purl.purl_str()} has no license in {url!r}")

    if _is_valid_spdx_id(license_):
        return SPDXId(license_)

    raise NoLicenseFound(
        f"Package {component.purl.purl_str()} has no valid SPDX license: {license_}"
    )


_CPAN_LICENSES = {
    "apache_2_0": "Apache-2.0",
    "artistic_2": "Artistic-2.0",
    "mit": "MIT",
    "perl_5": "Artistic-1.0-Perl OR GPL-1.0-or-later",  # https://metacpan.org/pod/Software::License::Perl_5
    "gpl_2": "GPL-2.0-only",
}


def research_cpan_license(component: Component) -> SPDXId:
    """retrieve license from metacpan"""

    assert component.purl.type_ == "cpan"

    url = "https://fastapi.metacpan.org/v1/release/_search"
    response = requests.get(
        url,
        params={
            "q": f"distribution:{component.purl.name.replace('::', '-')} AND version:{component.purl.version}"
        },
        timeout=TIMEOUT,
    )
    response.raise_for_status()

    hits = response.json()["hits"]["hits"]
    if len(hits) != 1:
        raise NoLicenseFound(
            f"Package {component.purl.purl_str()} not found (got {len(hits)} hits) in {url!r}"
        )

    licenses = hits[0]["_source"]["license"]
    if len(licenses) != 1:
        raise NoLicenseFound(
            f"Package {component.purl.purl_str()} has unexpected license list: {licenses}"
        )

    cpan_license_id = licenses[0]

    if cpan_license_id == "unknown":
        raise NoLicenseFound(f"Package {component.purl.purl_str()} has unknown license in metacpan")

    if cpan_license_id not in _CPAN_LICENSES:
        raise NoLicenseFound(
            f"Package {component.purl.purl_str()} has unmapped CPAN license: {cpan_license_id!r}"
        )

    return SPDXId(_CPAN_LICENSES[cpan_license_id])


def research_pypi_license(component: Component) -> SPDXId:
    """retrieve license from pypi"""

    assert component.purl.type_ == "pypi"

    url = f"https://pypi.org/pypi/{component.purl.name}/{component.purl.version}/json"
    response = requests.get(url, timeout=TIMEOUT)
    response.raise_for_status()

    info = response.json().get("info", {})

    for field in ("license_expression", "license"):
        if license_ := info.get(field):
            if _is_valid_spdx_id(license_):
                return SPDXId(license_)
            if license_ == "Apache 2.0":
                return SPDXId("Apache-2.0")
            if license_ == "MIT License":
                return SPDXId("MIT")

    raise NoLicenseFound(
        f"Package {component.purl.purl_str()} has no valid SPDX license in {url!r}"
    )


def research_golang_license(component: Component) -> SPDXId:
    """retrieve license from deps.dev"""

    assert component.purl.type_ == "golang"

    # Go module names contain slashes (e.g. github.com/foo/bar) which must be escaped.
    name = (
        f"{component.purl.namespace}/{component.purl.name}"
        if component.purl.namespace
        else component.purl.name
    )
    url = (
        f"https://api.deps.dev/v3/systems/GO/packages/{quote(name, safe='')}"
        f"/versions/{quote(component.purl.version, safe='')}"
    )
    response = requests.get(url, timeout=TIMEOUT)
    response.raise_for_status()

    licenses = response.json().get("licenses") or []
    if not licenses:
        raise NoLicenseFound(f"Package {component.purl.purl_str()} has no license in {url!r}")

    # deps.dev may return multiple licenses; join with AND to stay conservative.
    license_ = " AND ".join(licenses) if len(licenses) > 1 else licenses[0]

    if _is_valid_spdx_id(license_):
        return SPDXId(license_)

    raise NoLicenseFound(
        f"Package {component.purl.purl_str()} has no valid SPDX license: {license_}"
    )


def research_licenses(
    components: ComponentList,
    manually_researched_licenses: LicenseDB,
    automatically_researched_licenses: LicenseDB,
) -> tuple[LicenseDB, list[tuple[Component, Exception]]]:
    # I thought about only returning the used purls and their licenses, but in the case of errors we
    # would lose the cache. Therefore let's not cleanup automatically but do it manually if needed.
    new_db = automatically_researched_licenses.model_copy(deep=True)
    errors: list[tuple[Component, Exception]] = []
    for component in components_without_license(
        components, automatically_researched_licenses, manually_researched_licenses
    ):
        try:
            match component.purl.type_:
                case "cargo":
                    new_db.set(component.purl, research_cargo_license(component))
                case "npm":
                    new_db.set(component.purl, research_npm_license(component))
                case "cpan":
                    new_db.set(component.purl, research_cpan_license(component))
                case "pypi":
                    new_db.set(component.purl, research_pypi_license(component))
                case "golang":
                    new_db.set(component.purl, research_golang_license(component))
                case _:
                    raise NotImplementedError(
                        f"Don't know how to research license for component with purl type {component.purl.type_} maybe you need to manually research it?"
                    )
        except Exception as exc:
            errors.append((component, exc))
    return new_db, errors


def _main() -> None:
    args = _parse_args()

    components = ComponentList.model_validate_json(args.dep_list.read_text())
    automatically_researched_licenses = LicenseDB.model_validate_json(
        (Path(__file__).parent / "automatically_researched_licenses.json").read_bytes()
    )
    manually_researched_licenses = LicenseDB.model_validate_json(
        (Path(__file__).parent / "manually_researched_licenses.json").read_bytes()
    )

    new_automatically_researched_licenses, errors = research_licenses(
        components, manually_researched_licenses, automatically_researched_licenses
    )
    with open(args.out, "w") as f:
        # pydantic cannot sort keys
        json.dump(
            new_automatically_researched_licenses.model_dump(mode="json"),
            f,
            indent=2,
            sort_keys=True,
        )
        f.write("\n")

    if errors:
        print(f"\n{len(errors)} license lookup(s) failed:", file=sys.stderr)  # noqa: T201
        for component, exc in errors:
            print(f"  - {component.purl.purl_str()}: {exc}", file=sys.stderr)  # noqa: T201
        sys.exit(1)


if __name__ == "__main__":
    _main()
