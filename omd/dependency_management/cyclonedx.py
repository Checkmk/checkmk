# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""CycloneDX data"""

import base64
import uuid
from collections.abc import Iterable, Iterator
from dataclasses import dataclass, field
from datetime import datetime, UTC
from pathlib import Path
from typing import Annotated, Literal, NewType, Self
from urllib.parse import parse_qsl, quote, unquote, urlencode, urlparse, urlunparse

from pydantic import BaseModel, ConfigDict, Field, PlainSerializer, PlainValidator, RootModel

JSONDict = dict[str, object]

SPDXId = NewType("SPDXId", str)

VulnId = str
VulnerabilityState = Literal[
    "resolved",
    "resolved_with_pedigree",
    "exploitable",
    "in_triage",
    "false_positive",
    "not_affected",
]


@dataclass(frozen=True)
class PUrl:
    """A package URL
    A package url has the following scheme:
        scheme:type/namespace/name@version?qualifiers#subpath
    """

    type_: str
    name: str
    version: str
    namespace: str | None = None
    qualifiers: frozenset[tuple[str, str]] = field(default_factory=frozenset)
    subpath: str | None = None

    @classmethod
    def from_str(cls, some_str: str) -> Self:
        """parse from str

        Currently version is mandatory"""

        parsed_url = urlparse(some_str)
        path_wo_version, version = parsed_url.path.split("@", maxsplit=1)
        type_, *namespace, name = path_wo_version.split("/")

        return cls(
            type_,
            unquote(name),
            unquote(version),
            None if not namespace else "/".join(map(unquote, namespace)),
            (
                frozenset(parse_qsl(parsed_url.query, keep_blank_values=True))
                if parsed_url.query
                else frozenset()
            ),
            unquote(parsed_url.fragment) if parsed_url.fragment else None,
        )

    def purl_str(self) -> str:
        path = quote(self.type_)
        path += f"/{quote(self.namespace)}" if self.namespace else ""
        path += f"/{quote(self.name)}@{quote(self.version)}"

        return urlunparse(
            (
                "pkg",
                "",
                path,
                "",
                urlencode(dict(self.qualifiers)),
                quote(self.subpath or ""),
            )
        )


class LicenseDB(RootModel[dict[PUrl, SPDXId]]):
    root: dict[
        Annotated[
            PUrl, PlainValidator(PUrl.from_str), PlainSerializer(PUrl.purl_str, return_type=str)
        ],
        SPDXId,
    ]

    def get(self, purl: PUrl) -> SPDXId | None:
        return self.root.get(purl)

    def set(self, purl: PUrl, license_id: SPDXId) -> None:
        self.root[purl] = license_id


@dataclass(frozen=True)
class LicenseInfo:
    id_: SPDXId
    text: str | None

    def merge(self, other: Self) -> "LicenseInfo":
        if self.id_ != other.id_:
            raise ValueError(f"Conflicting license ids: {self.id_!r} != {other.id_!r}")
        return LicenseInfo(
            self.id_, _merge_agreeing(f"license text for {self.id_!r}", self.text, other.text)
        )

    def to_json(self) -> JSONDict:
        # heuristic to determine between expression and id
        if " " in str(self.id_):
            return {"expression": self.id_}

        if self.text is None:
            return {
                "license": {
                    "id": self.id_,
                }
            }
        return {
            "license": {
                "id": self.id_,
                "text": {
                    "contentType": "text/plain",
                    "encoding": "base64",
                    "content": base64.b64encode(self.text.encode("utf-8")).decode("utf-8"),
                },
            }
        }


def _merge_agreeing[T](what: str, a: T | None, b: T | None) -> T | None:
    """Return the value that is set, ignoring Nones; raise if both are set and differ."""
    if a is not None and b is not None and a != b:
        raise ValueError(f"Conflicting {what}: {a!r} != {b!r}")
    return a if a is not None else b


def _merge_optional_license(a: LicenseInfo | None, b: LicenseInfo | None) -> LicenseInfo | None:
    if a is None or b is None:
        return a or b
    return a.merge(b)


class Hash(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    alg: Literal["SHA-256", "SHA-512"]
    content: str


class Component(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    type_: Literal["library", "application"]
    purl: PUrl
    hashes: frozenset[Hash] = Field(default_factory=frozenset)
    files: frozenset[Path] = Field(default_factory=frozenset)
    labels: frozenset[str] = Field(default_factory=frozenset)
    license_info: LicenseInfo | None = None
    cpe: str | None = None

    @property
    def ref(self) -> str:
        return self.purl.purl_str()

    @property
    def properties(self) -> list[dict[str, str]]:
        return [
            {
                "name": "path",
                "value": str(f),
            }
            for f in self.files
        ] + [
            {
                "name": "bazel-label",
                "value": l,
            }
            for l in self.labels
        ]

    def merge(self, other: Self) -> Self:
        if self.purl != other.purl:
            raise ValueError(f"Cannot merge different purls: {self.ref} != {other.ref}")
        if self.type_ != other.type_:
            raise ValueError(f"Conflicting type for {self.ref}: {self.type_} != {other.type_}")
        return self.model_copy(
            update={
                "hashes": self.hashes | other.hashes,
                "files": self.files | other.files,
                "labels": self.labels | other.labels,
                "license_info": _merge_optional_license(self.license_info, other.license_info),
                "cpe": _merge_agreeing(f"cpe for {self.ref}", self.cpe, other.cpe),
            }
        )

    def to_bom_json(self) -> JSONDict:
        result: JSONDict = {
            "bom-ref": self.ref,
            "type": self.type_,
            "name": self.purl.name,
            "version": self.purl.version,
            "hashes": [{"alg": h.alg, "content": h.content} for h in self.hashes],
            "properties": self.properties,
            "purl": self.purl.purl_str(),
        }
        if self.license_info:
            result["licenses"] = [self.license_info.to_json()]
        if self.cpe is not None:
            result["cpe"] = self.cpe
        return result


@dataclass(frozen=True)
class Vulnerability:
    """info regarding a vulnerability"""

    vulnerability_id: VulnId
    affects: frozenset[PUrl]
    state: VulnerabilityState
    reason: str

    @staticmethod
    def vuln_id_to_source(vuln_id: VulnId) -> dict[str, str]:
        """convert the vuln id to a cyclondx source

        here we concentrate to be compliant with dtrack..."""
        if vuln_id.startswith("CVE-"):
            return {"name": "NVD"}
        if vuln_id.startswith("GHSA-"):
            return {"name": "GITHUB"}
        # OSV has no own identifier, IMHO RUSTSEC do not belong to OSV...
        if vuln_id.startswith("RUSTSEC-"):
            return {"name": "OSV"}
        if vuln_id.startswith("PYSEC-"):
            return {"name": "OSV"}
        raise NotImplementedError(f"VulnID: {vuln_id!r} not supported")

    def to_json(self) -> JSONDict:
        return {
            "id": self.vulnerability_id,
            "source": self.vuln_id_to_source(self.vulnerability_id),
            "analysis": {
                "state": self.state,
                "detail": self.reason,
            },
            "affects": [{"ref": p.purl_str()} for p in self.affects],
        }


class ComponentList(RootModel[list[Component]]):
    root: list[Component]

    def __iter__(self) -> Iterator[Component]:  # type: ignore[override]
        return iter(self.root)

    def __getitem__(self, item: int) -> Component:
        return self.root[item]


def unify_components(components: Iterable[Component]) -> list[Component]:
    """Merge components sharing a purl into a single component.

    Merging combines files/labels/hashes and fills in optional fields (license,
    cpe); it raises on genuinely conflicting values (see Component.merge).
    """
    unified: dict[PUrl, Component] = {}
    for c in components:
        unified[c.purl] = unified[c.purl].merge(c) if c.purl in unified else c
    return list(unified.values())


def components_without_license(
    components: ComponentList,
    automatically_researched: LicenseDB,
    manually_researched: LicenseDB,
) -> list[Component]:
    """Return components that have no license in any of the license DBs."""
    return [
        c
        for c in components
        if c.license_info is None
        and automatically_researched.get(c.purl) is None
        and manually_researched.get(c.purl) is None
    ]


class Bom:
    """The main Bom object"""

    def __init__(self) -> None:
        self.serial = str(uuid.uuid4())
        self.creation_date = datetime.now(UTC)
        self.components: list[Component] = []
        self.vulnerabilities: list[Vulnerability] = []

    def to_json(self) -> JSONDict:
        return {
            "bomFormat": "CycloneDX",
            "specVersion": "1.6",
            "serialNumber": f"urn:uuid:{self.serial}",
            "metadata": {
                "timestamp": self.creation_date.isoformat(),
                "component": {
                    "type": "application",
                    "name": "Checkmk",
                    "bom-ref": "root-checkmk",
                },
            },
            "components": [c.to_bom_json() for c in self.components],
            "dependencies": [
                {
                    "ref": "root-checkmk",
                    "dependsOn": [str(c.ref) for c in self.components],
                }
            ],
            "vulnerabilities": [v.to_json() for v in self.vulnerabilities],
        }
