#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# A pylint checker for Checkmk layering conventions. The basic idea is very simple: We partition
# qualified names into "virtual packages" (see PackageFor protocol below) and check if imports
# between these virtual packages are explicitly allowed (see IsPackageRelationshipOK protocol
# below). If not, we report a violation. Two exceptions to: Importing from the standard library and
# the own package are always allowed, obviously. This is effectively what we would get if we had
# real separate packages with their own setup.py files etc.

# Test with:
#     PYTHONPATH=. pylint --load-plugins=tests.testlib.pylint_checker_layering_violation --disable=all --enable=layering-violation cmk/{bi,ec,checkers,fields,notification_plugins,snmplib,utils} livestatus.py

from __future__ import annotations

from collections.abc import Collection, Container, Hashable, Iterable, Mapping, Sequence, Set
from pathlib import Path
from typing import NewType, Protocol, TypeVar

import jsonschema
import yaml
from astroid import nodes  # type: ignore[import-untyped]
from pylint.checkers import BaseChecker
from pylint.lint import PyLinter

####################################################################################################
# our main "business logic", the heart of our import checking logic
####################################################################################################

PackageName = NewType("PackageName", str)  # something like "requests-oauthlib"
ModuleName = NewType("ModuleName", str)  # something like "cmk.ccc.debug"
ImportedName = NewType("ImportedName", str)


class PackageFor(Protocol):
    def __call__(self, name: ModuleName | ImportedName) -> PackageName: ...


class IsPackageRelationshipOK(Protocol):
    def __call__(
        self, *, importing_package: PackageName, imported_package: PackageName
    ) -> bool: ...


class IsImportOK:
    def __init__(
        self, package_for: PackageFor, is_package_relationship_ok: IsPackageRelationshipOK
    ) -> None:
        self._package_for = package_for
        self._is_package_relationship_ok = is_package_relationship_ok

    def __call__(self, *, importing_module: ModuleName, imported_name: ImportedName) -> bool:
        return self._is_package_relationship_ok(
            importing_package=self._package_for(importing_module),
            imported_package=self._package_for(imported_name),
        )


####################################################################################################
# the hook into pylint's AST traversal
####################################################################################################


def register(linter: PyLinter) -> None:
    linter.register_checker(LayerViolationChecker(linter))


# NOTE: The first paragraph of the class documentation string is shown in pylint's --help output as
# a heading for the defined options.
class LayerViolationChecker(BaseChecker):
    """Checkmk layering conventions"""

    name = "layering_violation"  # name of the section in the config
    msgs = {
        "C8411": (  # message id; Why did we choose this number?
            "import of %r not allowed in module %r",  # template of displayed message
            "layering-violation",  # message symbol
            "Used when an import is found which violates the Checkmk layering conventions.",  # message description
        ),
    }
    options = (
        (
            "layering-definition",
            {
                "default": "",
                "type": "path",
                "metavar": "<path to YAML file>",
                "help": "A path to a YAML file describing the layering conventions in Checkmk,"
                " consisting of a description of the virtual packages, the allowed package"
                " relationships and some expected package import cycles.",
            },
        ),
    )

    def __init__(self, linter: PyLinter) -> None:
        super().__init__(linter)
        # The config file and commandline arguments have not been processed yet, so linter.config is
        # not yet complete. We need to delay any configuration processing to open().
        self._is_import_ok: IsImportOK | None = None
        self._linter = linter

    def open(self) -> None:
        # TODO: Check how often this is called! Cache, if necessary!
        if filename := self._linter.config.layering_definition:
            self._is_import_ok = load_layering_configuration(Path(filename))

    def visit_import(self, node: nodes.Import) -> None:
        importing_module = extract_importing_module(node)
        imported_names = extract_imported_names(node)
        self._check_imports(node, importing_module, imported_names)

    def visit_importfrom(self, node: nodes.ImportFrom) -> None:
        importing_module = extract_importing_module(node)
        imported_module = extract_imported_module(node)
        imported_names = [
            ImportedName(imported_module + "." + name) for name in extract_imported_names(node)
        ]
        self._check_imports(node, importing_module, imported_names)

    def _check_imports(
        self,
        node: nodes.NodeNG,
        importing_module: ModuleName,
        imported_names: Sequence[ImportedName],
    ) -> None:
        if self._is_import_ok is None:
            return
        for imported_name in imported_names:
            if not self._is_import_ok(
                importing_module=importing_module, imported_name=imported_name
            ):
                self.add_message(
                    "layering-violation",
                    node=node,
                    args=(imported_name, importing_module),
                )


####################################################################################################
# YAML helpers
####################################################################################################


def load_layering_configuration(path: Path) -> IsImportOK:
    # NOTE: yaml.safe_load is guaranteed to return mappings in insertion order, and we depend on
    # this! This is a tiny bit of a hack, we could use a list of pairs instead, but that would make
    # the YAML quite a bit uglier.
    with path.open() as stream:
        layering_definition = yaml.load(stream, UniqueKeyLoader)
    # We validate the layering definition here syntactically, a more thorough semantic validation
    # will be done later in the constructors of PackageMapper and RelationChecker.
    jsonschema.validate(
        instance=layering_definition, schema=yaml.safe_load(LAYERING_DEFINITION_SCHEMA)
    )
    package_mapper = PackageMapper(layering_definition["package-definitions"].items())
    relation_checker = RelationChecker(
        layering_definition["allowed-package-relationships"],
        package_mapper.defined_package_names(),
        layering_definition["known-package-cycles"],
    )
    return IsImportOK(package_mapper.package_for, relation_checker.is_package_relationship_ok)


# PyYAML doesn't check for duplicate mapping keys, although it really should, see
# https://github.com/yaml/pyyaml/issues/165 for a discussion and the workaround below.
class UniqueKeyLoader(yaml.SafeLoader):  # pylint: disable=too-many-ancestors
    def construct_mapping(self, node: yaml.MappingNode, deep: bool = False) -> dict:
        mapping = set()
        for key_node, _value_node in node.value:
            key = self.construct_object(key_node, deep=deep)
            if key in mapping:
                raise yaml.MarkedYAMLError(
                    "while constructing a mapping",
                    node.start_mark,
                    "found duplicate key",
                    key_node.start_mark,
                )
            mapping.add(key)
        return super().construct_mapping(node, deep)


# We could move this schema into a separate file to be usable for IDEs, see e.g.
# https://json-schema-everywhere.github.io/yaml
LAYERING_DEFINITION_SCHEMA = """
$schema: https://json-schema.org/draft/2020-12/schema
$id: https://checkmk.com/schemas/layering-definition.json
type: object
properties:
  package-definitions:
    type: object
    additionalProperties:
      type: array
      items:
        type: string
      uniqueItems: true
  allowed-package-relationships:
    type: object
    additionalProperties:
      type: array
      items:
        type: string
      uniqueItems: true
  known-package-cycles:
    type: array
    items:
      type: array
      items:
        type: string
      uniqueItems: true
    uniqueItems: true
required:
- package-definitions
- allowed-package-relationships
- known-package-cycles
additionalProperties: false
"""

####################################################################################################
# AST helpers
####################################################################################################


def extract_importing_module(node: nodes.Import) -> ModuleName:
    return ModuleName(node.root().name)


def extract_imported_module(node: nodes.ImportFrom) -> ModuleName:
    level: int | None = node.level  # numer of dots in relative import, 0 (None?) for absolute
    modname: str = node.modname  # the module that is being imported from
    if level:
        root: nodes.Module = node.root()
        index = (None if level == 1 else -(level - 1)) if root.package else -level
        return ModuleName(".".join(root.name.split(".")[:index] + ([modname] if modname else [])))
    return ModuleName(modname)


def extract_imported_names(node: nodes.Import) -> Sequence[ImportedName]:
    return [ImportedName(name) for name, _alias in node.names]  # we don't care about any aliases


####################################################################################################
# mapping of qualified name prefixes to "virtual packages" via lists of prefixes
####################################################################################################


class PackageMapper:
    def __init__(
        self, package_definitions: Iterable[tuple[PackageName, Iterable[ModuleName]]]
    ) -> None:
        super().__init__()
        self._package_definitions = list(package_definitions)
        self._validate_no_prefix_shadowing()

    def _validate_no_prefix_shadowing(self) -> None:
        prefixes_seen: set[ModuleName] = set()
        for package_name, prefixes in self._package_definitions:
            for prefix in prefixes:
                for prefix_seen in prefixes_seen:
                    if self._is_prefix_of(prefix_seen, prefix):
                        raise ValueError(
                            f"module prefix {prefix!r} in package definition for {package_name!r} shadowed by {prefix_seen!r}"
                        )
            prefixes_seen |= set(prefixes)

    def defined_package_names(self) -> Set[PackageName]:
        return {package_name for package_name, _prefixes in self._package_definitions}

    def package_for(self, name: ModuleName | ImportedName) -> PackageName:
        for package_name, prefixes in self._package_definitions:
            if any(self._is_prefix_of(p, name) for p in prefixes):
                return package_name
        raise ValueError(f"undefined package name for {name!r}")

    @staticmethod
    def _is_prefix_of(module_prefix: ModuleName, name: ModuleName | ImportedName) -> bool:
        return (name + ".").startswith(module_prefix + ".")


####################################################################################################
# check allowed imports between "virtual packages", using the given whitelist
####################################################################################################


class RelationChecker:
    def __init__(
        self,
        allowed_package_relationships: Mapping[PackageName, Iterable[PackageName]],
        defined_package_names: Set[PackageName],
        known_package_cycles: Collection[Sequence[PackageName]],
    ) -> None:
        super().__init__()
        self._allowed_package_relationships = allowed_package_relationships
        self._validate_only_defined_package_names_used(defined_package_names, known_package_cycles)
        self._validate_no_cycles(known_package_cycles)

    def _validate_only_defined_package_names_used(
        self,
        defined_package_names: Set[PackageName],
        known_package_cycles: Collection[Sequence[PackageName]],
    ) -> None:
        def validate_defined(package_name: PackageName, where: str) -> None:
            if package_name not in defined_package_names:
                raise ValueError(f"unknown package {package_name!r} in {where}")

        for importing_package, allowed_imports in self._allowed_package_relationships.items():
            validate_defined(importing_package, "allowed package relationships")
            for allowed_import in allowed_imports:
                validate_defined(allowed_import, f"allowed imports for {importing_package!r}")
        for cycle in known_package_cycles:
            for package_name in cycle:
                validate_defined(package_name, f"known package cycle {cycle!r}")

    def _validate_no_cycles(self, known_package_cycles: Container[Sequence[PackageName]]) -> None:
        if cycles := [
            scc
            for scc in tarjan(self._allowed_package_relationships)
            if len(scc) > 1 and scc not in known_package_cycles
        ]:
            plural = "s" if len(cycles) > 1 else ""
            pretty_cycles = " and ".join(
                " => ".join(list(cycle[::-1]) + [cycle[-1]]) for cycle in cycles
            )
            raise ValueError(f"cycle{plural} in allowed package relationships: {pretty_cycles}")

    def is_package_relationship_ok(
        self, importing_package: PackageName, imported_package: PackageName
    ) -> bool:
        return (
            imported_package in (PackageName("stdlib"), importing_package)
            or imported_package in self._allowed_package_relationships[importing_package]
        )


####################################################################################################
# Tarjan's algorithm for SCCs, everybody should write their own version of it at least once! ;-)
####################################################################################################

T = TypeVar("T", bound=Hashable)


def tarjan(graph: Mapping[T, Iterable[T]]) -> Sequence[Sequence[T]]:
    """Returns the strongly connected components of the graph g in topological order,
    see e.g. https://en.wikipedia.org/wiki/Tarjan%27s_strongly_connected_components_algorithm.
    Simple recursive version, should be OK for our purposes."""
    node_stack: list[T] = []
    on_stack: set[T] = set()
    index: dict[T, int] = {}
    lowlink: dict[T, int] = {}
    sccs: list[list[T]] = []

    def strong_connect(v: T) -> None:
        lowlink[v] = index[v] = len(index)
        node_stack.append(v)
        on_stack.add(v)
        for w in graph.get(v, ()):
            if w not in index:
                strong_connect(w)
                lowlink[v] = min(lowlink[v], lowlink[w])
            elif w in on_stack:
                lowlink[v] = min(lowlink[v], index[w])
        if lowlink[v] == index[v]:
            scc: list[T] = []
            while True:
                w = node_stack.pop()
                on_stack.remove(w)
                scc.append(w)
                if w == v:
                    break
            sccs.append(scc)

    for v in graph:
        if v not in index:
            strong_connect(v)
    return sccs
