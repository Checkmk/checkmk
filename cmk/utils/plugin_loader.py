#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import importlib
import os
import pkgutil
import sys
from itertools import chain
from pathlib import Path
from types import ModuleType
from typing import Callable, Iterator, List, Optional, Tuple


def load_plugins_with_exceptions(package_name: str) -> Iterator[Tuple[str, BaseException]]:
    """Load all specified packages

    This function accepts a package name in Python's dotted syntax (e.g.
    requests.exceptions).

    Args:
        package_name:
            A valid module path in Python's dotted syntax.

    Returns:
        A generator of 2-tuples of plugin-name and exception, when a plugin failed to
        import. An empty generator if everything succeeded.

    Raises:
        Nothing explicit. Possibly ImportErrors.

    Example:
        >>> for mod_name, exc in load_plugins_with_exceptions("urllib"):
        ...     print("Importing %s failed: %s" % (mod_name, exc))

    """
    walk_errors: List[Tuple[str, BaseException]] = []

    def onerror_func(name: str) -> None:
        if exc := sys.exc_info()[1]:
            walk_errors.append((name, exc))

    __import__(package_name)
    for full_name in _find_modules(sys.modules[package_name], onerror=onerror_func):
        try:
            importlib.import_module(full_name)
        except Exception as exc:
            yield full_name.removeprefix(f"{package_name}."), exc

    yield from walk_errors


def _find_modules(pkg: ModuleType, onerror: Callable[[str], None]) -> List[str]:
    """Replacement for pkgutil.walk_packages

    We used `pkgutil.walk_packages` before, but that was not able to correctly detect and walk into
    PEP420 implicit namespace packages.

    See also:
        https://stackoverflow.com/questions/41203765/init-py-required-for-pkgutil-walk-packages-in-python3
    """
    return sorted(
        set(
            chain.from_iterable(
                _discover_path_importables(Path(p), pkg.__name__, onerror)
                for p in getattr(pkg, "__path__", [])
            ),
        ),
    )


def _discover_path_importables(
    pkg_pth: Path, pkg_name: str, onerror: Callable[[str], None]
) -> Iterator[str]:
    """Yield all importables under a given path and package."""
    for dir_path, _d, file_names in os.walk(pkg_pth):
        pkg_dir_path = Path(dir_path)

        if pkg_dir_path.parts[-1] == "__pycache__":
            continue

        if all(Path(_).suffix != ".py" for _ in file_names):
            continue

        rel_pt = pkg_dir_path.relative_to(pkg_pth)
        pkg_pref = ".".join((pkg_name,) + rel_pt.parts)
        yield from (
            pkg_path
            for _loader, pkg_path, _is_pkg in pkgutil.walk_packages(
                (str(pkg_dir_path),),
                prefix=f"{pkg_pref}.",
                onerror=onerror,
            )
        )


def load_plugins(
    init_file_path: str,
    package_name: str,
) -> None:
    """Import all submodules of a module, recursively

    This works reliably even with relative imports happening along the chain.

    Args:
        init_file_path: Package name
        package_name: The name of the package.

    Returns:
        Nothing.

    """
    # This is duplicated because it somehow obscures the exceptions being raised by
    # errors while compiling modules. This implemention explicitly doesn't catch any exceptions
    # occurring while compiling.
    __import__(package_name)
    package = sys.modules[package_name]
    module_path: Optional[List[str]] = getattr(package, "__path__")
    if module_path:
        for _loader, plugin_name, _is_pkg in pkgutil.walk_packages(module_path):
            importlib.import_module("%s.%s" % (package_name, plugin_name))

    for _loader, plugin_name, _is_pkg in pkgutil.walk_packages([init_file_path]):
        importlib.import_module("%s.%s" % (package_name, plugin_name))
