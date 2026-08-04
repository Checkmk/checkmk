#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Generate ``bin/`` console-script wrappers from a wheel's entry points.

A wheel records its ``console_scripts`` entry points in ``*.dist-info/entry_points.txt``.
Normally the *installer* (pip) reads that metadata and synthesises the executable wrappers
in ``bin/``. We do not install our wheels -- we unzip them into ``site-packages/`` -- so no
wrappers are created. This tool re-implements just that slice: it reads the standard
metadata and emits one small wrapper per ``console_scripts`` entry into an output directory.
"""

import argparse
import configparser
import stat
import sys
import zipfile
from collections.abc import Sequence
from pathlib import Path
from typing import override

_WRAPPER_TEMPLATE = """\
#!/usr/bin/env python3
# Generated console-script wrapper -- do not edit.
import sys

from {module} import {attr}

if __name__ == "__main__":
    sys.exit({call}())
"""


def _read_entry_points(wheel: Path) -> str:
    """Return the contents of the wheel's ``entry_points.txt`` (empty string if absent)."""
    with zipfile.ZipFile(wheel) as zf:
        match tuple(n for n in zf.namelist() if n.endswith(".dist-info/entry_points.txt")):
            case ():
                return ""
            case (name,):
                return zf.read(name).decode("utf-8")
            case multiple:
                raise RuntimeError(f"{wheel}: found multiple entry_points.txt: {multiple}")


class _EntryPointsParser(configparser.ConfigParser):
    """A ConfigParser matching the entry-points format."""

    def __init__(self) -> None:
        # No interpolation: a "%" in any entry-point group must not be special.
        super().__init__(delimiters=("=",), interpolation=None)

    @override
    def optionxform(self, optionstr: str) -> str:
        """Entry-point names are case-sensitive; keep them verbatim."""
        return optionstr


def parse_console_scripts(content: str) -> Sequence[tuple[str, str]]:
    """Parse the ``[console_scripts]`` section into ``{name: "module:attr"}``."""
    parser = _EntryPointsParser()
    parser.read_string(content)
    return parser.items("console_scripts") if parser.has_section("console_scripts") else ()


def instantiate_wrapper(target: str) -> str:
    """Render a wrapper for an entry-point target ``module(.sub):attr(.sub)``.

    ``extras`` (a trailing ``[...]``) are irrelevant to running the script and are ignored.
    """
    module, _, attr_path = target.split("[", 1)[0].strip().partition(":")
    module = module.strip()
    attr_path = attr_path.strip()
    if not module or not attr_path:
        raise ValueError(f"malformed entry-point target: {target!r}")
    # ``module:foo.bar`` imports ``foo`` from ``module`` and calls ``foo.bar()``.
    top_attr = attr_path.split(".", 1)[0]
    return _WRAPPER_TEMPLATE.format(module=module, attr=top_attr, call=attr_path)


def main(argv: Sequence[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wheel", required=True, type=Path, help="path to the .whl file")
    parser.add_argument(
        "--out", required=True, type=Path, help="output directory for the wrapper scripts"
    )
    args = parser.parse_args(argv)

    # Emit a wrapper for every console_scripts entry point the wheel declares. A
    # wheel with none (or no entry_points.txt at all) is a silent no-op: the output
    # directory is still created, just empty, so the Bazel action's declared output
    # always exists.
    scripts = parse_console_scripts(_read_entry_points(args.wheel))
    args.out.mkdir(parents=True, exist_ok=True)
    for name, target in scripts:
        wrapper = args.out / name
        wrapper.write_text(instantiate_wrapper(target))
        wrapper.chmod(wrapper.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)

    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
