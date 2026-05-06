# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import IO

import toml
from cyclonedx import Component, LicenseInfo, PUrl, SPDXId
from pnpm_parser import read_pnpm_lock
from pydantic import BaseModel, ConfigDict, Field


@dataclass(frozen=True)
class _Args:
    bazel_info: Path | None
    out: Path
    manifests: list[Path]


class LicenseKind(BaseModel):
    model_config = ConfigDict(extra="forbid")

    identifier: SPDXId
    name: str


class LicenseData(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: LicenseKind
    label: str
    text: Path | None = None

    def read(self) -> str | None:
        if self.text is None:
            return None
        return self.text.read_text()


class CpeData(BaseModel):
    model_config = ConfigDict(extra="forbid")

    cpe: str


class PackageMetadataAttributes(BaseModel):
    model_config = ConfigDict(extra="forbid")

    license_data_path: Path | None = Field(
        validation_alias="build.bazel.attribute.license", default=None
    )
    cpe_data_path: Path | None = Field(
        validation_alias="com.checkmk.dependency_management.cpe", default=None
    )

    def license_data(self) -> LicenseData | None:
        if self.license_data_path is None:
            return None
        return LicenseData.model_validate_json(self.license_data_path.read_text())

    def cpe(self) -> str | None:
        if self.cpe_data_path is None:
            return None
        return CpeData.model_validate_json(self.cpe_data_path.read_text()).cpe


class PackageMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid")

    attributes: PackageMetadataAttributes
    label: str
    purl: str

    def component(self) -> Component:
        return Component(
            type_="library",
            purl=PUrl.from_str(self.purl),
            labels=frozenset({self.label}),
            license_info=LicenseInfo(
                id_=SPDXId(license_data.kind.identifier), text=license_data.read()
            )
            if (license_data := self.attributes.license_data())
            else None,
            cpe=self.attributes.cpe(),
        )


class Dependency(BaseModel):
    model_config = ConfigDict(extra="forbid")

    metadata: Path

    def read(self) -> PackageMetadata:
        return PackageMetadata.model_validate_json(self.metadata.read_text())


class Config(BaseModel):
    model_config = ConfigDict(extra="forbid")

    deps: list[Dependency]

    def components(self) -> set[Component]:
        return {bazel_dep.read().component() for bazel_dep in self.deps}


class RequirementsTxtParser:
    @dataclass
    class Info:
        name: str
        version: str
        hashes: list[str]

    def __init__(self, path: Path) -> None:
        self.continuing = False
        self.info: dict[str, RequirementsTxtParser.Info] = {}
        self._path = path

    def parse(self) -> None:
        with self._path.open() as rfile:
            self._parse_file(rfile)

    def _parse_file(self, requirements_file: IO[str]) -> None:
        while line := requirements_file.readline():
            if not line.strip() or line.lstrip().startswith("#"):
                continue
            if line.strip().startswith("--"):
                assert line.strip().startswith("--index-url")
                continue

            # e.g. pyjwt[crypto], bandit[sarif, toml]
            line = re.sub(r"\[.+\]", "", line)
            name_version = line.replace(" @ git+", "==git+").split(maxsplit=1)[0]
            try:
                name, version = name_version.split("==", 1)
            except ValueError as e:
                e.add_note(f"failed to parse line: {line=} {name_version=}")
                raise

            info = self.Info(
                name=re.sub(r"\[\w+\]", "", name),
                version=version,
                hashes=[],
            )

            while line.rstrip().endswith("\\"):
                line = requirements_file.readline()
                info.hashes.append(self._parse_continuing_line(line))
            self.info[info.name] = info

    @staticmethod
    def _parse_continuing_line(line: str) -> str:
        assert line.strip().startswith("--hash=sha256:")
        return line.strip().removeprefix("--hash=sha256:").removesuffix("\\").strip()

    def components(self) -> list[Component]:
        return [
            Component(
                type_="library",
                purl=PUrl(
                    type_="pypi",
                    name=info.name,
                    version=info.version,
                ),
                sha256s=frozenset(info.hashes),
                files=frozenset({self._path}),
            )
            for info in self.info.values()
        ]


def read_cargo_lock(path: Path) -> list[Component]:
    """Read a Cargo.lock file and return a list of components"""
    with path.open() as cargofile_fh:
        cargofile = toml.load(cargofile_fh)  # type: ignore[no-untyped-call]

    return [
        Component(
            type_="library",
            purl=PUrl(
                type_="cargo",
                name=details["name"],
                version=details["version"],
            ),
            sha256s=frozenset({details["checksum"]}),
            files=frozenset({path}),
        )
        for details in cargofile.get("package", [])
        if "source" in details
    ]


def read_manifests(paths: list[Path]) -> list[Component]:
    components = []
    for path in paths:
        match path:
            case Path(name="runtime-requirements.txt"):
                parser = RequirementsTxtParser(path)
                parser.parse()
                components.extend(parser.components())
            case Path(name="pnpm-lock.yaml"):
                components.extend(read_pnpm_lock(path))
            case Path(name="Cargo.lock"):
                components.extend(read_cargo_lock(path))
            case _:
                raise NotImplementedError(f"Cannot handle manifest {path}")
    return components


def _parse_args() -> _Args:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bazel_info", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--manifest", action="append", default=[], type=Path)
    args = parser.parse_args()
    return _Args(
        bazel_info=args.bazel_info,
        out=args.out,
        manifests=args.manifest,
    )


def _main() -> None:
    args = _parse_args()

    components = list[Component]()
    components.extend(read_manifests(args.manifests))

    if args.bazel_info:
        bom_config = Config.model_validate_json(args.bazel_info.read_text())
        components.extend(bom_config.components())

    with open(args.out, "w") as f:
        json.dump([c.model_dump(mode="json") for c in set(components)], f, indent=2)


if __name__ == "__main__":
    _main()
