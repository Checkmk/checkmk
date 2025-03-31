#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pydantic import TypeAdapter

from cmk.gui.watolib.simple_config_file import config_file_registry


def test_type_adapter_instantiable() -> None:
    # NOTE: The config_file_registry is filled via importing cmk.gui.main_modules
    # in test/unit/cmk/conftest.py. First let's make sure that the registry *is*
    # actually filled: With an empty registry this test would turn into a no-op.
    # The 10 is just an ad hoc value, currently we register 12 (CRE) or 13 (all
    # other editions) config files.
    assert len(config_file_registry) > 10

    for wato_config_file in config_file_registry.values():
        # check if pydantic knows how to generate a schema for the given class
        TypeAdapter(wato_config_file.spec_class)  # nosemgrep: type-adapter-detected
