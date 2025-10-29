#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterator
from pathlib import Path

from cmk.bakery.v1 import OS, PluginConfig, SystemConfig

type FileGenerator = Iterator[Plugin | SystemBinary | PluginConfig | SystemConfig]
"""Return type for the 'files_function' generator function."""


class Plugin:
    """File artifact that represents a Checkmk agent plugin

    The specified plug-in file will be deployed to the Checkmk agent's plug-in directory as
    a callable plugin.

    Args:
        base_os: The target operating system.
        source: Path of the plug-in file, relative to the plug-in families `cmk.plugins.<FAMILY>.agent`
            or `cmk_addons.plugins.<FAMILY>.agent` directory on the Checkmk site.
            This usually consists only of the filename.
        target: Target path, relative to the plug-in directory within the agent's file tree
            on the target system. If omitted, the plug-in will be deployed under it's
            relative source path/filename.
        interval: Caching interval in seconds. The plug-in will only be executed by the
            agent after the caching interval is elapsed.
        asynchronous: Relevant for Windows Agent. Don't wait for termination of the plugin's
            process if True. An existent interval will always result in asynchronous execution.
        timeout: Relevant for Windows Agent. Maximum waiting time for a plug-in to terminate.
        retry_count: Relevant for Windows Agent. Maximum number of retried executions after a
            failed plug-in execution.
    """

    def __init__(
        self,
        *,
        base_os: OS,
        source: Path,
        target: Path | None = None,
        interval: float | None = None,
        asynchronous: bool | None = None,
        timeout: float | None = None,
        retry_count: float | None = None,
    ) -> None:
        # Don't trust the caller.
        self.base_os = OS(base_os)
        self.source = Path(source)
        self.target = None if target is None else Path(target)
        self.interval = None if interval is None else int(round(interval))
        self.asynchronous = None if asynchronous is None else bool(asynchronous)
        self.timeout = None if timeout is None else int(round(timeout))
        self.retry_count = None if retry_count is None else int(round(retry_count))

    def __repr__(self) -> str:
        args = (
            f"base_os={self.base_os!r}",
            f"source={self.source!r}",
            *(
                f"{k}={v!r}"
                for k, v in (
                    ("target", self.target),
                    ("interval", self.interval),
                    ("asynchronous", self.asynchronous),
                    ("timeout", self.timeout),
                    ("retry_count", self.retry_count),
                )
                if v is not None
            ),
        )
        return f"{self.__class__.__name__}({', '.join(args)})"

    def __eq__(self, other: object) -> bool:
        return self.__class__ == other.__class__ and self.__dict__ == other.__dict__


class SystemBinary:
    """File artifact that represents a script/program that should be deployed on the hosts.

    Under UNIX, the file will be deployed to the binary directory (by default, '/usr/bin',
    configurable in WATO).

    Under Windows, the file will be deployed to the 'bin'-folder at the agent's installation directory.

    Args:
        base_os: The target operating system.
        source: Path of the file, relative to the plugin families `cmk.plugins.<FAMILY>.agent`
            or `cmk_addons.plugins.<FAMILY>.agent` directory on the Checkmk site.
        target: Target path, relative to the binary directory on the target system. If omitted,
            the plug-in will be deployed under it's relative source path/filename.
    """

    def __init__(self, *, base_os: OS, source: Path, target: Path | None = None) -> None:
        self.base_os = OS(base_os)
        self.source = Path(source)
        self.target = None if target is None else Path(target)

    def __repr__(self) -> str:
        t_arg = "" if self.target is None else f", target={self.target!r}"
        return f"{self.__class__.__name__}(base_os={self.base_os!r}, source={self.source!r}{t_arg})"

    def __eq__(self, other: object) -> bool:
        return self.__class__ == other.__class__ and self.__dict__ == other.__dict__
