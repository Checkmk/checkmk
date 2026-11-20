#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Where the configuration files are located"""

from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

_MAIN_MK_RELATIVE = "etc/check_mk/main.mk"
_CONF_D_RELATIVE = "etc/check_mk/conf.d"
_FINAL_MK_RELATIVE = "etc/check_mk/final.mk"
_LOCAL_MK_RELATIVE = "etc/check_mk/local.mk"


@dataclass(frozen=True, kw_only=True)
class BaseConfigurationMKFiles:
    """The .mk files of the base configuration

    In the order they are read:
     1) main.mk
     2) All files below `conf_d` (unless `include_conf_d` is false)
     3) final_mk
     4) local_mk
    """

    main_mk: Path
    conf_d: Path
    final_mk: Path
    local_mk: Path
    include_conf_d: bool

    @classmethod
    def from_omd_root(
        cls, omd_root: Path, *, include_conf_d: bool = True
    ) -> BaseConfigurationMKFiles:
        return cls(
            main_mk=omd_root / _MAIN_MK_RELATIVE,
            conf_d=omd_root / _CONF_D_RELATIVE,
            final_mk=omd_root / _FINAL_MK_RELATIVE,
            local_mk=omd_root / _LOCAL_MK_RELATIVE,
            include_conf_d=include_conf_d,
        )

    # This is deliberately not `__iter__`: the files are yielded in the order
    # in which they must be executed (later files override earlier ones).
    # The explicit name keeps this significance visible at the call sites.
    def iterate_for_loading(self) -> Iterator[tuple[Path, Path | None]]:
        """Yield each file and, for those below `conf_d`, its path relative to it"""
        yield self.main_mk, None
        if self.include_conf_d:
            yield from (
                (p, p.relative_to(self.conf_d))
                for p in sorted(self.conf_d.rglob("*.mk"), key=key_config_paths)
            )
        for path in (self.final_mk, self.local_mk):
            if path.exists():  # TODO: just yield. EAFP.
                yield path, None


def key_config_paths(path: Path) -> tuple[tuple[str, ...], int, tuple[str, ...]]:
    """Key function for Check_MK configuration file paths

    Helper functions that determines the sort order of the
    configuration files. The following two rules are implemented:

    1. *.mk files in the same directory will be read
       according to their lexical order.
    2. subdirectories in the same directory will be
       scanned according to their lexical order.
    3. subdirectories of a directory will always be read *after*
       the *.mk files in that directory.
    """
    pa = path.parts
    return pa[:-1], len(pa), pa
