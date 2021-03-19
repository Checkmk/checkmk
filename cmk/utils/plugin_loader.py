#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import importlib
import pkgutil
import sys
from typing import Tuple, Optional, List, Generator


def load_plugins_with_exceptions(package_name: str) -> Generator[Tuple[str, Exception], None, None]:
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
    __import__(package_name)
    package = sys.modules[package_name]
    module_path: List[str] = getattr(package, '__path__', [])
    for _loader, plugin_name, _is_pkg in pkgutil.walk_packages(module_path):
        try:
            importlib.import_module("%s.%s" % (package_name, plugin_name))
        except Exception as exc:
            yield plugin_name, exc


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
    module_path: Optional[List[str]] = getattr(package, '__path__')
    if module_path:
        for _loader, plugin_name, _is_pkg in pkgutil.walk_packages(module_path):
            importlib.import_module("%s.%s" % (package_name, plugin_name))

    for _loader, plugin_name, _is_pkg in pkgutil.walk_packages([init_file_path]):
        importlib.import_module("%s.%s" % (package_name, plugin_name))
