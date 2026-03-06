# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import argparse
import json
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated

import yaml
from cyclonedx import (
    Bom,
    Component,
    ComponentList,
    LicenseDB,
    LicenseInfo,
    PUrl,
    Vulnerability,
    VulnerabilityState,
    VulnId,
)
from pydantic import BaseModel, ConfigDict, PlainValidator, RootModel


@dataclass(frozen=True)
class _Args:
    dep_list: Path
    vulnerability_info: Path | None
    out: Path


class VulnInfo(BaseModel):
    model_config = ConfigDict(extra="forbid")

    aliases: frozenset[VulnId] | None = None
    reason: str
    state: VulnerabilityState


class ResearchedVulnInfo(RootModel[dict[PUrl, dict[VulnId, VulnInfo]]]):
    root: dict[Annotated[PUrl, PlainValidator(PUrl.from_str)], dict[VulnId, VulnInfo]]

    def __iter__(self) -> Iterator[PUrl]:  # type: ignore[override]
        return iter(self.root)

    def __getitem__(self, item: PUrl) -> dict[VulnId, VulnInfo]:
        return self.root[item]


def _parse_args() -> _Args:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dependencies", type=Path, required=True)
    parser.add_argument("--vulnerability_info", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    return _Args(
        dep_list=args.dependencies,
        out=args.out,
        vulnerability_info=args.vulnerability_info,
    )


def determine_license(
    automatically_researched_licenses: LicenseDB,
    manually_researched_licenses: LicenseDB,
    component: Component,
) -> Component:
    """we want to be able to overwrite a license"""
    if (
        component.license_info is None
        and (auto_license := automatically_researched_licenses.get(component.purl)) is not None
    ):
        component = component.model_copy(update={"license_info": LicenseInfo(auto_license, None)})

    if (manual_license := manually_researched_licenses.get(component.purl)) is not None:
        # We may overwrite
        component = component.model_copy(update={"license_info": LicenseInfo(manual_license, None)})

    assert component.license_info is not None, (
        f"License for {component.ref} could not be determined. Please research it and add it to the manually researched licenses."
    )
    return component


def create_bom_vulnerabilites(
    vulnerability_info: ResearchedVulnInfo, components: set[Component]
) -> list[Vulnerability]:
    """create the vuln objects

    we are duplicating the info for the aliases.
    Theoretically we could add these to the references attribute, but last time dtrack did not
    pick that up. I think this is a workaround we can live with.
    """

    assert not (non_existent_vulns := set(vulnerability_info) - set(c.purl for c in components)), (
        f"Vulnerabilities for non-existent components: {non_existent_vulns}"
    )

    researched_vulns: list[Vulnerability] = []
    for component in components:
        if component.purl not in vulnerability_info:
            continue
        for vuln_id, vuln_info in vulnerability_info[component.purl].items():
            for id_ in [vuln_id] + list(vuln_info.aliases or []):
                researched_vulns.append(
                    Vulnerability(
                        vulnerability_id=id_,
                        affects=frozenset({component.purl}),
                        state=vuln_info.state,
                        reason=vuln_info.reason,
                    )
                )
    return researched_vulns


def _main() -> None:
    args = _parse_args()

    components = ComponentList.model_validate_json(args.dep_list.read_text())
    automatically_researched_licenses = LicenseDB.model_validate_json(
        (Path(__file__).parent / "automatically_researched_licenses.json").read_bytes()
    )
    manually_researched_licenses = LicenseDB.model_validate_json(
        (Path(__file__).parent / "manually_researched_licenses.json").read_bytes()
    )

    bom = Bom()
    bom.components = [
        determine_license(automatically_researched_licenses, manually_researched_licenses, c)
        for c in components
    ]

    if args.vulnerability_info:
        vuln_info = ResearchedVulnInfo.model_validate(
            yaml.safe_load(args.vulnerability_info.read_text())
        )
        bom.vulnerabilities = create_bom_vulnerabilites(vuln_info, set(bom.components))

    with open(args.out, "w") as f:
        json.dump(bom.to_json(), f, indent=2)


if __name__ == "__main__":
    _main()
