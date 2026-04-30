#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import sys
from contextlib import suppress
from pathlib import Path

import psutil


def _pid_from_file(pid_file: Path) -> int | None:
    with suppress(ValueError, OSError, psutil.NoSuchProcess):
        pid = int(pid_file.read_text().strip())
        if psutil.pid_exists(pid) and psutil.Process(pid).status() != psutil.STATUS_ZOMBIE:
            return pid
    return None


def _pid_from_proctable(omd_site: str, apache_name: str) -> int | None:
    # Use the process name instead of the command line:
    # There may be processes forked from the apache workers that need to be
    # ignored by this script where we can not change the full command line
    # but the process name. This means we can only distinguish between them
    # using the process name.
    # One process is in watolib.py: ActivateChangesSite.run()
    candidates: list[psutil.Process] = []
    for proc in psutil.process_iter(["username", "name", "create_time", "status"]):
        with suppress(psutil.NoSuchProcess):
            if (
                proc.info["username"] == omd_site
                and proc.info["name"] == apache_name
                and proc.info["status"] != psutil.STATUS_ZOMBIE
            ):
                candidates.append(proc)
    if not candidates:
        return None
    return min(candidates, key=lambda p: p.info["create_time"]).pid


def _pidof_apache(pid_file: Path, omd_site: str, apache_name: str) -> int | None:
    # If there is actually an apache2 process whose pid is in PIDFILE,
    # return it.
    if pid_file.exists():
        return _pid_from_file(pid_file)
    # It might happen that there is no pidfile but a process is running.
    # As fallback check the process table for the oldest apache process
    # running as this user.
    return _pid_from_proctable(omd_site, apache_name)


def main() -> None:
    if len(sys.argv) != 4:
        sys.exit(1)
    pid_file, omd_site, apache_bin_path = sys.argv[1:4]

    pid = _pidof_apache(Path(pid_file), omd_site, Path(apache_bin_path).name)

    if pid is not None:
        sys.stdout.write(f"{pid}\n")
        sys.exit(0)
    sys.exit(1)


if __name__ == "__main__":
    main()
