#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Edition specific preparation of the test host and the site runtime.

Some editions need more than `omd create` to get a working site, e.g. config
files on the host or fake services next to the site. The code for that lives
with the edition below non-free/tests/, so the generic system test code does
not depend on it. It is found through the namespace package
`tests.testlib.system.edition_setups`: the module named after the edition
(e.g. non-free/tests/testlib/system/edition_setups/cloud.py) provides `SETUP`.

Editions without such a module need no preparation.
"""

import importlib
from contextlib import AbstractContextManager, nullcontext
from pathlib import Path
from typing import Protocol

from tests.testlib.common.version import TypeCMKEdition
from tests.testlib.system.site import Site

_NAMESPACE = "tests.testlib.system.edition_setups"


class EditionSetup(Protocol):
    def prepare_host(self, config_root: Path) -> None:
        """Create what has to be in place on the host before a site is created.

        `config_root` is the file system root to write to, a mounted volume for
        sites running in a container.
        """

    def site_environment(self, site: Site) -> AbstractContextManager[object]:
        """Provide what the site needs while it is initialized and tested."""


class _NoEditionSetup:
    def prepare_host(self, config_root: Path) -> None:
        pass

    def site_environment(self, _site: Site) -> AbstractContextManager[object]:
        return nullcontext()


def edition_setup(edition: TypeCMKEdition) -> EditionSetup:
    module_name = f"{_NAMESPACE}.{edition.long}"
    try:
        module = importlib.import_module(module_name)
    except ModuleNotFoundError as e:
        # Only a missing setup module means "nothing to do", not a missing
        # import inside of it.
        if e.name not in (_NAMESPACE, module_name):
            raise
        if edition.is_cloud_edition():
            raise RuntimeError(
                f"The cloud edition needs {module_name}, which is part of non-free/tests/"
            ) from e
        return _NoEditionSetup()
    setup: EditionSetup = module.SETUP
    return setup
