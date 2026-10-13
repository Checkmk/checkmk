#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Re-save the conf.d files that extend variables they never define

Earlier Checkmk versions wrote several files below ``conf.d/wato`` in
bare ``variable.update({...})`` or ``variable += [...]`` style, which can
only be executed in a namespace that has the variable pre-seeded.
Checkmk 3.1 stops seeding that namespace. Every writer now defines the
variable first (see ``cmk.ccc.store.bootstrap_statement``), so loading
and saving a file through its own writer brings it into that shape.

The files are known: contacts, tags, host, service and contact group
aliases, notification rules and parameters, passwords, time periods,
predefined conditions and OAuth2 connections in every edition, alert
handler rules and InfluxDB connections in the Pro edition, relays in the
Ultimate and Cloud editions. The group aliases are assigned since 2.4,
but a file written by 2.3 or earlier extends them. hosts.mk and rules.mk
are re-saved by the ``create_precompiled_files`` and ``rulesets``
actions anyway; the remaining generated files only assign variables.

A file is re-saved only if it fails to load into an empty namespace.

Each edition registers a :class:`SelfbootstrapConfDFiles` action with
its files.
"""

from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
from logging import Logger
from pathlib import Path
from typing import override

from cmk.gui.config import active_config
from cmk.gui.watolib.simple_config_file import WatoConfigFile
from cmk.gui.watolib.utils import wato_root_dir
from cmk.update_config.internal import ExpiryVersion, UpdateAction


@dataclass(frozen=True, kw_only=True)
class ExtendOnlyFile:
    """A generated file below conf.d/wato and the way to re-save it through its own writer

    The writer is created when `resave` runs: it resolves the site paths at
    that time, not when the file list is defined.
    """

    name: str
    """The file name below conf.d/wato"""
    resave: Callable[[bool], None]
    """Load and save the file; the argument is the pprint_value setting"""


def resave_config_file[G](
    name: str,
    make_config_file: Callable[[], WatoConfigFile[G]],
) -> ExtendOnlyFile:
    """Re-save `name` through the config file object `make_config_file` returns"""

    def resave(pprint_value: bool) -> None:
        config_file = make_config_file()
        config_file.save(config_file.load_for_modification(), pprint_value)

    return ExtendOnlyFile(name=name, resave=resave)


def _loads_unseeded(path: Path) -> bool:
    """Whether `path` can be executed into a namespace that starts out empty"""
    namespace: dict[str, object] = {}
    try:
        exec(compile(path.read_text(), path, "exec"), namespace, namespace)  # nosec B102 # BNS:aee528
    except Exception:
        return False
    return True


def resave_extend_only_files(
    files: Iterable[ExtendOnlyFile], *, pprint_value: bool, logger: Logger
) -> None:
    """Re-save every file that exists and cannot be loaded without predefined variables

    A file that cannot be read or re-saved is left alone and reported in
    the update log.
    """
    wato_dir = wato_root_dir()
    for file in files:
        path = wato_dir / file.name
        if not path.exists():
            continue
        try:
            if _loads_unseeded(path):
                continue
            file.resave(pprint_value)
        except Exception as e:
            logger.warning(
                "%(path)s: left unchanged, it cannot be re-saved: %(error)s",
                {"path": path, "error": e},
            )
            continue
        logger.info("Rewrote %(path)s to define its variable", {"path": path})


class SelfbootstrapConfDFiles(UpdateAction):
    """Make the given conf.d files loadable without pre-seeded variables"""

    def __init__(
        self,
        *,
        name: str,
        title: str,
        sort_index: int,
        files: Sequence[ExtendOnlyFile],
        expiry_version: ExpiryVersion,
        continue_on_failure: bool = True,
    ) -> None:
        super().__init__(
            name=name,
            title=title,
            sort_index=sort_index,
            expiry_version=expiry_version,
            continue_on_failure=continue_on_failure,
        )
        self._files = files

    @override
    def __call__(self, logger: Logger) -> None:
        resave_extend_only_files(
            self._files, pprint_value=active_config.wato_pprint_config, logger=logger
        )
