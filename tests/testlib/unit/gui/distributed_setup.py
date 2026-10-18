#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterator
from contextlib import contextmanager

import cmk.utils.paths
from cmk.config.paths import BaseConfigurationMKFiles


@contextmanager
def running_on_a_remote_site() -> Iterator[None]:
    """Make the code believe it runs on a distributed-setup remote site."""
    conf_d = BaseConfigurationMKFiles.from_omd_root(cmk.utils.paths.omd_root).conf_d
    conf_d.mkdir(parents=True, exist_ok=True)
    distr_wato_mk = conf_d / "distributed_wato.mk"
    previous = distr_wato_mk.read_bytes() if distr_wato_mk.exists() else None
    distr_wato_mk.write_text("is_distributed_setup_remote_site = True\n")
    try:
        yield
    finally:
        if previous is None:
            distr_wato_mk.unlink(missing_ok=True)
        else:
            distr_wato_mk.write_bytes(previous)
