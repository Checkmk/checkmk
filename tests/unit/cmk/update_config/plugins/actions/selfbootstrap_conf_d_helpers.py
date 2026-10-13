#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Shared by the tests of the self-bootstrap actions of all editions"""

import shutil
from collections.abc import Iterator, Mapping
from pathlib import Path

from cmk.gui.watolib.utils import wato_root_dir


def make_wato_dir() -> Iterator[Path]:
    """Provide an empty conf.d/wato directory; wrap in a fixture

    The directory must not exist yet: it is removed afterwards, along with
    anything the test wrote into it.
    """
    wato_dir = wato_root_dir()
    assert not wato_dir.exists()
    wato_dir.mkdir(parents=True)
    yield wato_dir
    shutil.rmtree(wato_dir)


def load_unseeded(path: Path) -> Mapping[str, object]:
    """Load a config file the way the base config loader will: into an empty namespace"""
    namespace: dict[str, object] = {}
    exec(compile(path.read_text(), path, "exec"), namespace, namespace)  # nosec B102
    return {k: v for k, v in namespace.items() if k != "__builtins__"}
