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
        --scripts-dir <venv Scripts dir> --shebang <windows python.exe path> \\
        [--fixup-records <site-packages dir> ...]
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import io
import sys
import zipfile
from pathlib import Path

# Console entry points the historic CAB shipped as .exe wrappers, and the
# exact __main__.py each wrapper executed.  The pip wrappers use the (older)
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


_WRAPPERS = {
    "pip.exe": _PIP_MAIN,
    "pip3.exe": _PIP_MAIN,
    "pip3.13.exe": _PIP_MAIN,
    "pip-3.13.exe": _PIP_MAIN,
    "chardetect.exe": _plain_main("chardet.cli.chardetect", "main"),
    "normalizer.exe": _plain_main("charset_normalizer.cli", "cli_detect"),
    "pywin32_postinstall.exe": _plain_main("win32.scripts.pywin32_postinstall", "main"),
    "pywin32_testall.exe": _plain_main("win32.scripts.pywin32_testall", "main"),
}

_STUB_IN_PIP_WHEEL = "pip/_vendor/distlib/t64.exe"

# Fixed zip entry timestamp so rebuilt wrappers are bit-identical.
_ZIP_DATE_TIME = (1980, 1, 1, 0, 0, 0)

# RECORD line rewrites: the POSIX entry-point script name pip recorded
# under bin/ -> the .exe wrapper that replaces it.  pip-3.13.exe is
# virtualenv's extra alias and was never RECORDed, matching production.
_RECORD_SCRIPT_TO_WRAPPER = {
    "pip": "pip.exe",
    "pip3": "pip3.exe",
    "pip3.13": "pip3.13.exe",
    "chardetect": "chardetect.exe",
    "normalizer": "normalizer.exe",
    "pywin32_postinstall": "pywin32_postinstall.exe",
    "pywin32_testall": "pywin32_testall.exe",
}


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


def _fixup_records(site_packages: Path, wrappers: dict[str, bytes]) -> None:
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
                if name in _RECORD_SCRIPT_TO_WRAPPER:
                    wrapper = _RECORD_SCRIPT_TO_WRAPPER[name]
                    data = wrappers[wrapper]
                    line = f"../../Scripts/{wrapper},{_record_hash(data)},{len(data)}"
                else:
                    # Plain script payloads (and their __pycache__ entries)
                    # move from bin/ to Scripts/ verbatim.
                    line = "../../Scripts/" + rest
            lines.append(line)
        record.write_text(eol.join(lines) + eol)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pip-wheel", required=True, type=Path)
    parser.add_argument("--scripts-dir", required=True, type=Path)
    parser.add_argument("--shebang", required=True)
    parser.add_argument("--fixup-records", type=Path, action="append", default=[])
    args = parser.parse_args()

    with zipfile.ZipFile(_pip_wheel(args.pip_wheel)) as wheel:
        stub = wheel.read(_STUB_IN_PIP_WHEEL)

    wrappers = {
        name: _wrapper_bytes(stub, args.shebang, main_py) for name, main_py in _WRAPPERS.items()
    }
    args.scripts_dir.mkdir(parents=True, exist_ok=True)
    for name, data in wrappers.items():
        (args.scripts_dir / name).write_bytes(data)

    for site_packages in args.fixup_records:
        _fixup_records(site_packages, wrappers)
    return 0


if __name__ == "__main__":
    sys.exit(main())
