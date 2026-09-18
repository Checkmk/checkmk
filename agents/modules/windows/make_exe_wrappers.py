#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Generate the Windows console-script ``.exe`` wrappers for the CAB's venv.

On a Windows host, pip materialises a wheel's console entry points as ``.exe``
launchers under ``Scripts/``: a distlib launcher stub, a ``#!`` line naming the
interpreter, and a zip containing ``__main__.py``.  Our cross-platform Linux
``pip install --target`` writes POSIX shell scripts to ``bin/`` instead, so this
tool rebuilds the launchers the way distlib's ``ScriptMaker`` would on Windows
— with one deliberate improvement: the historic Windows build baked the *build
machine's* venv path into the shebang (``D:\\w\\workspace\\...``), which made
the wrappers fail to resolve their interpreter on customer hosts.  We bake the
production install path instead.

The ``t64.exe`` stub is taken from the pinned pip wheel's vendored distlib, so
no extra dependency is needed and the stub provenance is sha256-pinned.

Each ``--fixup-records`` site-packages dir gets its dist-info ``RECORD``
files rewritten so the ``../../bin/<script>`` lines our cross-platform pip
install recorded point at the ``../../Scripts/<script>.exe`` wrappers that
actually ship (matching what a native Windows pip install records).

Usage::

    make_exe_wrappers.py --pip-wheel <pip wheel or find-links dir> \\
        --scripts-dir <venv Scripts dir> --python-major-minor <X.Y> \\
        --shebang <windows python.exe path> \\
        [--fixup-records <site-packages dir> ...]
"""

from __future__ import annotations

import argparse
import base64
import configparser
import hashlib
import io
import re
import sys
import zipfile
from collections.abc import Iterable
from pathlib import Path

# Console entry points the CAB ships as .exe wrappers, and the exact
# __main__.py each wrapper executes.  The pip wrappers use the (older)
# template virtualenv's seeder generated; the rest use pip's own template.
_PIP_MAIN = (
    "# -*- coding: utf-8 -*-\n"
    "import re\n"
    "import sys\n"
    "if __name__ == '__main__':\n"
    "    from pip._internal.cli.main import main\n"
    "    sys.argv[0] = re.sub(r'(-script\\.pyw|\\.exe)?$', '', sys.argv[0])\n"
    "    sys.exit(main())\n"
)


def _plain_main(module: str, func: str) -> str:
    return (
        "import sys\n"
        f"from {module} import {func}\n"
        "if __name__ == '__main__':\n"
        "    sys.argv[0] = sys.argv[0].removesuffix('.exe')\n"
        f"    sys.exit({func}())\n"
    )


# pip's console scripts keep the (older) template virtualenv's seeder generated;
# everything else is generated from the dist's own declared entry point.
_PIP_SCRIPT_TARGET = "pip._internal.cli.main:main"


def _console_scripts(site_packages: list[Path]) -> dict[str, str]:
    """Map every installed console script to its "module:func" entry point.

    The names come from each dist-info's ``entry_points.txt``, so a wrapper can
    never disagree with the wheel it wraps.  pip additionally installs a
    versioned alias (``pip3.13``) that it does not declare there; it is
    recovered from the RECORD below and mapped to pip's own target.
    """
    scripts: dict[str, str] = {}
    for site in site_packages:
        for entry_points in sorted(site.glob("*.dist-info/entry_points.txt")):
            parser = configparser.ConfigParser()
            # Entry-point names are case sensitive; ConfigParser lowercases by default.
            parser.optionxform = str  # type: ignore[method-assign,assignment]
            parser.read(entry_points)
            if not parser.has_section("console_scripts"):
                continue
            for name, target in parser.items("console_scripts"):
                scripts[name] = target.strip()
    return scripts


def _installed_scripts(site_packages: list[Path]) -> set[str]:
    """Console-script names the cross-platform pip install actually recorded."""
    names: set[str] = set()
    for site in site_packages:
        for record in site.glob("*.dist-info/RECORD"):
            for line in record.read_text().splitlines():
                if not line.startswith("../../bin/"):
                    continue
                name = line[len("../../bin/") :].split(",", 1)[0]
                if not name.endswith(".py") and "__pycache__" not in name:
                    names.add(name)
    return names


def _main_py(name: str, target: str) -> str:
    if target == _PIP_SCRIPT_TARGET:
        return _PIP_MAIN
    module, _, func = target.partition(":")
    if not module or not func:
        sys.exit(f"error: console script {name!r} has an unparsable entry point {target!r}")
    return _plain_main(module, func)


def _wrappers(python_major_minor: str, site_packages: list[Path]) -> dict[str, str]:
    """{wrapper filename: __main__.py} for every script the install recorded."""
    declared = _console_scripts(site_packages)
    versioned_pip = f"pip{python_major_minor}"
    wrappers: dict[str, str] = {}
    for name in sorted(_installed_scripts(site_packages)):
        target = declared.get(name)
        if target is None:
            if name != versioned_pip:
                sys.exit(
                    f"error: console script {name!r} was installed but no dist-info "
                    "declares it; make_exe_wrappers.py cannot derive its entry point"
                )
            # pip's own versioned alias, not declared in entry_points.txt.
            target = _PIP_SCRIPT_TARGET
        wrappers[name + ".exe"] = _main_py(name, target)
    # virtualenv's extra alias; never RECORDed, so it is not derivable.
    wrappers[f"pip-{python_major_minor}.exe"] = _PIP_MAIN
    return wrappers


_STUB_IN_PIP_WHEEL = "pip/_vendor/distlib/t64.exe"

# Fixed zip entry timestamp so rebuilt wrappers are bit-identical.
_ZIP_DATE_TIME = (1980, 1, 1, 0, 0, 0)


def _record_script_to_wrapper(wrapper_names: Iterable[str]) -> dict[str, str]:
    # RECORD line rewrites: the POSIX entry-point script name pip recorded
    # under bin/ -> the .exe wrapper that replaces it.  pip-<X.Y>.exe is
    # virtualenv's extra alias and was never RECORDed, matching production.
    return {name.removesuffix(".exe"): name for name in wrapper_names}


def _pip_wheel(path: Path) -> Path:
    if path.is_dir():
        candidates = sorted(path.glob("pip-*.whl"))
        if not candidates:
            sys.exit(f"error: no pip-*.whl in {path}")
        return candidates[0]
    return path


def _wrapper_bytes(stub: bytes, shebang: str, main_py: str) -> bytes:
    payload = io.BytesIO()
    with zipfile.ZipFile(payload, "w", zipfile.ZIP_STORED) as zf:
        info = zipfile.ZipInfo("__main__.py", date_time=_ZIP_DATE_TIME)
        zf.writestr(info, main_py)
    return stub + b"#!" + shebang.encode() + b"\n" + payload.getvalue()


def _record_hash(data: bytes) -> str:
    digest = base64.urlsafe_b64encode(hashlib.sha256(data).digest()).rstrip(b"=")
    return f"sha256={digest.decode()}"


def _fixup_records(
    site_packages: Path, wrappers: dict[str, bytes], script_to_wrapper: dict[str, str]
) -> None:
    for record in site_packages.glob("*.dist-info/RECORD"):
        original = record.read_text()
        if "../../bin/" not in original:
            continue
        # pip writes RECORD via the csv module, i.e. with CRLF endings; keep
        # whatever the file already uses.
        eol = "\r\n" if "\r\n" in original else "\n"
        lines = []
        for line in original.splitlines():
            if line.startswith("../../bin/"):
                rest = line[len("../../bin/") :]
                name = rest.split(",", 1)[0]
                if name in script_to_wrapper:
                    wrapper = script_to_wrapper[name]
                    data = wrappers[wrapper]
                    line = f"../../Scripts/{wrapper},{_record_hash(data)},{len(data)}"
                elif name.endswith(".py") or "__pycache__" in name:
                    # Plain script payloads (and their __pycache__ entries)
                    # move from bin/ to Scripts/ verbatim.
                    line = "../../Scripts/" + rest
                else:
                    # A pip-generated console script that never ships (only
                    # bin/*.py is copied to Scripts/); its RECORD hash covers
                    # the build machine's interpreter path, breaking reproducibility.
                    sys.exit(f"error: {record}: console script {name!r} has no .exe wrapper")
            lines.append(line)
        record.write_text(eol.join(lines) + eol)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pip-wheel", required=True, type=Path)
    parser.add_argument("--scripts-dir", required=True, type=Path)
    parser.add_argument("--python-major-minor", required=True)
    parser.add_argument("--shebang", required=True)
    parser.add_argument("--fixup-records", type=Path, action="append", default=[])
    args = parser.parse_args()

    if not re.fullmatch(r"\d+\.\d+", args.python_major_minor):
        sys.exit(
            f"error: --python-major-minor must look like 3.13, got {args.python_major_minor!r}"
        )

    with zipfile.ZipFile(_pip_wheel(args.pip_wheel)) as wheel:
        stub = wheel.read(_STUB_IN_PIP_WHEEL)

    wrappers = {
        name: _wrapper_bytes(stub, args.shebang, main_py)
        for name, main_py in _wrappers(args.python_major_minor, args.fixup_records).items()
    }
    args.scripts_dir.mkdir(parents=True, exist_ok=True)
    for name, data in wrappers.items():
        (args.scripts_dir / name).write_bytes(data)

    script_to_wrapper = _record_script_to_wrapper(wrappers)
    for site_packages in args.fixup_records:
        _fixup_records(site_packages, wrappers, script_to_wrapper)
    return 0


if __name__ == "__main__":
    sys.exit(main())
