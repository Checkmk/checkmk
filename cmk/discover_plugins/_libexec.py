#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from importlib import import_module
from pathlib import Path

from ._wellknown import LIBEXEC_FOLDER


def discover_executable(name: str, *search_paths: Path) -> Path | None:
    return next((full_path for p in search_paths if (full_path := p / name).exists()), None)


def family_libexec_dir(module_name: str) -> Path:
    """Return the libexec dir corresponding to the passed module.

    Args:
      module_name: The name of a module that implements a plug-in of any
        of the well-known plug-in groups, i.e. two levels into the plugin
        families namespace.

    Example:
      In this example the family is "prism":

      >>> family_libexec_dir(  # doctest: +SKIP
      ...    "cmk.plugins.prism.server_side_calls.special_agent"
      ... ).parts[-4:]
      ('cmk', 'plugins', 'prism', 'libexec')

    """
    #    ^- arbitrary example, adjust if this file is ever (re)moved.

    if (file := import_module(module_name).__file__) is None:
        # should never happen: we know we loaded this from a file.
        raise TypeError(f"module does not have a __file__ attrbute: {module_name}")
    if (file_path := Path(file)).name == "__init__.py":
        return file_path.parent.parent.parent / LIBEXEC_FOLDER
    return file_path.parent.parent / LIBEXEC_FOLDER
