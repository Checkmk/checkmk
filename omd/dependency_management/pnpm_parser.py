# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Scanning a pnpm lockfiles

"Spec": https://github.com/pnpm/spec/blob/834f2815cc61917fa133e10869a2d4e9391c36bf/lockfile/
"""

import base64
from dataclasses import dataclass, field
from pathlib import Path
from typing import Annotated, Literal, Self

import yaml
from cyclonedx import Component, Hash, PUrl
from pydantic import BaseModel, Field, PlainValidator

PackageName = str
Version = str


def integrity_hash_to_hexdigest(hash_: str) -> Hash:
    """convert the base64 encoded hash to hexdigest
    >>> integrity_hash_to_hexdigest("md5-1B2M2Y8AsgTpgAmY7PhCfg==")
    'd41d8cd98f00b204e9800998ecf8427e'
    """
    type_, b64_hash = hash_.split("-", maxsplit=1)
    assert type_ == "sha512"
    return Hash(alg="SHA-512", content=base64.b64decode(b64_hash).hex())


class _PackageResolution(BaseModel):
    integrity: str  # Todo


class _LocalResolution(BaseModel):
    directory: str
    type_: str = Field(validation_alias="type")


class _V6PackageDetails(BaseModel):
    resolution: _PackageResolution
    dev: bool = False


class _V9PackageDetails(BaseModel):
    resolution: _PackageResolution | _LocalResolution

    @property
    def hashes(self) -> set[Hash]:
        if isinstance(self.resolution, _LocalResolution):
            return set()
        return {integrity_hash_to_hexdigest(self.resolution.integrity)}


@dataclass(frozen=True)
class _ImportVersion:
    version: Version
    # The path is currently unused, it is only used with peer dependencies (https://pnpm.io/how-peers-are-resolved).
    # During debugging it was helpful so grepping was a bit easier.
    path: str = field(compare=False)

    @classmethod
    def parse(cls, version: str) -> Self:
        """parse from string

        >>> _ImportVersion.parse("7.28.6")
        _ImportVersion(version='7.28.6', path='')
        >>> _ImportVersion.parse("7.28.6(@babel/core@7.28.6)")
        _ImportVersion(version='7.28.6', path='(@babel/core@7.28.6)')
        """
        if "(" not in version:
            return cls(version, "")
        version, path = version.split("(", 1)
        return cls(version, "(" + path)


@dataclass(frozen=True)
class MyDependencyIdentifier:
    """This is a mess."""

    name: PackageName
    import_version: _ImportVersion

    @classmethod
    def parse(cls, dep_path: str) -> Self:
        """parse from string

        >>> MyDependencyIdentifier.parse("@babel/helper-module-transforms@7.28.6(@babel/core@7.28.6)")
        MyDependencyIdentifier(name='@babel/helper-module-transforms', import_version=_ImportVersion(version='7.28.6', path='(@babel/core@7.28.6)'))

        >>> MyDependencyIdentifier.parse("@checkmk/saas@file:../common_node_modules/@checkmk/saas")
        MyDependencyIdentifier(name='@checkmk/saas', import_version=_ImportVersion(version='file:../common_node_modules/@checkmk/saas', path=''))
        """
        if dep_path.startswith("@"):
            name_wo_at, version = dep_path[1:].split("@", 1)
            return cls(f"@{name_wo_at}", _ImportVersion.parse(version))

        name, version = dep_path.split("@", 1)
        return cls(name, _ImportVersion.parse(version))

    @property
    def purl(self) -> PUrl:
        if self.name.startswith("@") and "/" in self.name:
            namespace, _, name = self.name.partition("/")
        else:
            namespace, name = None, self.name
        return PUrl(
            type_="npm", namespace=namespace, name=name, version=self.import_version.version
        )


class _V9ImportInfo(BaseModel):
    specifier: str
    version: Annotated[_ImportVersion, PlainValidator(_ImportVersion.parse)]


_AnnotatedMyDependencyIdentifier = Annotated[
    MyDependencyIdentifier, PlainValidator(MyDependencyIdentifier.parse)
]


class LockfileV6(BaseModel):
    version: str = Field(validation_alias="lockfileVersion", pattern=r"^6(\..+)?$")
    packages: dict[_AnnotatedMyDependencyIdentifier, _V6PackageDetails]
    importers: dict[
        str,
        dict[
            Literal["dependencies", "devDependencies", "optionalDependencies"],
            dict[PackageName, _V9ImportInfo],
        ],
    ]

    def bom_components(self, path: Path) -> list[Component]:
        return [
            Component(
                type_="library",
                purl=id_.purl,
                hashes=frozenset({integrity_hash_to_hexdigest(details.resolution.integrity)}),
                files=frozenset({path}),
            )
            for id_, details in self.packages.items()
            if not details.dev
        ]


class _Snapshot(BaseModel):
    dependencies: dict[PackageName, str] | None = None
    optional: bool = False

    def get_dependencies(self) -> set[MyDependencyIdentifier]:
        """another helper I wish I didn't need to write

        This is a snippet from my testfile:

            '@isaacs/cliui@8.0.2':
              dependencies:
                string-width: 5.1.2
                string-width-cjs: string-width@4.2.3
                strip-ansi: 7.1.2
                strip-ansi-cjs: strip-ansi@6.0.1
                wrap-ansi: 8.1.0
                wrap-ansi-cjs: wrap-ansi@7.0.0

        So apparently a requirement can be satisfied with another package?
        """
        if self.dependencies is None:
            return set()
        return {
            (
                MyDependencyIdentifier(name, _ImportVersion.parse(version))
                if version[0].isdigit()
                else MyDependencyIdentifier.parse(version)
            )
            for name, version in self.dependencies.items()
        }


@dataclass(frozen=True)
class V9Component:
    """helper to collect the needed data plus some more lock file specific data used during later processing"""

    id_: MyDependencyIdentifier
    hashes: set[Hash]
    deps: set[MyDependencyIdentifier]
    optional: bool

    @property
    def name(self) -> PackageName:
        return self.id_.name

    @property
    def version(self) -> Version:
        return self.id_.import_version.version

    def to_bom_component(self, path: Path) -> Component:
        return Component(
            type_="library",
            purl=self.id_.purl,
            hashes=frozenset(self.hashes),
            files=frozenset({path}),
        )


class LockfileV9(BaseModel):
    version: str = Field(validation_alias="lockfileVersion", pattern=r"^9(\..+)?$")
    packages: dict[_AnnotatedMyDependencyIdentifier, _V9PackageDetails]
    snapshots: dict[_AnnotatedMyDependencyIdentifier, _Snapshot]
    importers: dict[
        str,
        dict[
            Literal["dependencies", "devDependencies", "optionalDependencies"],
            dict[PackageName, _V9ImportInfo],
        ],
    ]

    def _packages_as_components(self) -> dict[MyDependencyIdentifier, V9Component]:
        return {
            package_id: V9Component(
                id_=package_id,
                hashes=details.hashes,
                deps=self.snapshots[package_id].get_dependencies(),
                optional=self.snapshots[package_id].optional,
            )
            for package_id, details in self.packages.items()
        }

    @staticmethod
    def _used_dep_ids(
        used_dep_set: set[MyDependencyIdentifier],
        components: dict[MyDependencyIdentifier, V9Component],
        component: V9Component,
    ) -> None:

        used_dep_set.add(component.id_)
        for sub_component in component.deps:
            if sub_component in used_dep_set:
                continue
            LockfileV9._used_dep_ids(used_dep_set, components, components[sub_component])

    def bom_components(self, path: Path) -> list[Component]:
        """Return a list of components for the BOM

        Cyclic dependencies are a thing here, so be warned.

        Thanks to the cyclic dependencies we cannot traverse the dependency graph once.
        To keep it manageable we first read all the package infos and then we check how the packages are related.
        The info if a package is a dev dependency comes from the graph though, so we need to traverse.

        To see if we did a decent job we traverse the prod dependency tree and the dev dependency tree and then check if we have seen all packages.
        Of course there are optional dependencies in a lock file whatever that means so we ignore if we missed those.
        """

        # Apparently some dependencies are distro/architecture specific and only required/available
        # on some platforms. We ignore them for now.

        package_components = self._packages_as_components()

        prod_dependencies: set[MyDependencyIdentifier] = set()
        dev_dependencies: set[MyDependencyIdentifier] = set()

        for import_info in self.importers.values():
            for name, info in import_info.get("dependencies", {}).items():
                self._used_dep_ids(
                    prod_dependencies,
                    package_components,
                    package_components[MyDependencyIdentifier(name, info.version)],
                )

            for name, info in import_info.get("devDependencies", {}).items():
                self._used_dep_ids(
                    dev_dependencies,
                    package_components,
                    package_components[MyDependencyIdentifier(name, info.version)],
                )

        non_optional_deps = {
            id_ for id_, component in package_components.items() if not component.optional
        }
        if unused_components := non_optional_deps - (prod_dependencies | dev_dependencies):
            raise ValueError(f"Unused components: {unused_components}")

        return [
            c.to_bom_component(path)
            for c in package_components.values()
            if c.id_ in prod_dependencies
        ]


def read_pnpm_lock(path: Path) -> list[Component]:
    with path.open() as fh:
        packages = yaml.safe_load(fh)

    version = str(packages.get("lockfileVersion", ""))
    match version:
        case _v if _v.startswith("6."):
            return LockfileV6.model_validate(packages).bom_components(path)
        case _v if _v.startswith("9."):
            return LockfileV9.model_validate(packages).bom_components(path)
        case _:
            raise NotImplementedError(f"pnpm lockfile version {version} not supported")
