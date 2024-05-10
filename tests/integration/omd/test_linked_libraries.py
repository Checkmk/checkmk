#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import re
from collections.abc import Iterator
from pathlib import Path
from typing import NamedTuple

import pytest

from tests.testlib.site import Site


class LinkedLibrary(NamedTuple):
    """
    A shared library that is linked to some dynamically linked binary in our system.
    """

    name: str
    path: Path | None


def _run_find_dynamically_linked(site: Site, path: Path) -> frozenset[Path]:
    """
    Use find to search all dynamically linked executables in the given path.

    The corresponding command in bash:
      find -L <path> \
           -type f -executable \
           -exec file {} + \
      | grep "dynamically linked" \
      | awk -F':' '{print $1}' \
      | xargs realpath \
    """

    # Implemented with as much find magic as I could muster because os.walk is _much_ slower.
    find_result = site.check_output(
        ["find", "-L", str(path), "-type", "f", "-executable", "-exec", "file", "{}", ";"]
    ).splitlines()

    return frozenset(
        Path(line.split(":")[0]).resolve() for line in find_result if "dynamically linked" in line
    )


ldd_regex = re.compile(r"(\S+) => (\S+) \(0x[0-9a-f]+\)")
not_found_regex = re.compile(r"(\S+) => not found")


def _run_ldd(site: Site, file: Path) -> list[str]:
    return site.check_output(["ldd", str(file)]).splitlines()


def _parse_ldd(lines: list[str]) -> Iterator[LinkedLibrary]:
    """

    >>> list(_parse_ldd([]))
    []
    >>> list(
    ...     _parse_ldd([
    ...         "linux-vdso.so.1 (0x00007ffcb2b42000)",
    ...         "libm.so.6 => /lib/x86_64-linux-gnu/libm.so.6 (0x00007f513f4af000)",
    ...         "libssl.so.1.1 => /omd/sites/stable/lib/libssl.so.1.1 (0x00007f513f14c000)",
    ...         "/lib64/ld-linux-x86-64.so.2 (0x00007f513f5b1000)",
    ...         "imaginary.so.9 => not found",
    ...     ])
    ... )
    [LinkedLibrary(name='libm.so.6', path=PosixPath('/lib/x86_64-linux-gnu/libm.so.6')), LinkedLibrary(name='libssl.so.1.1', path=PosixPath('/omd/sites/stable/lib/libssl.so.1.1')), LinkedLibrary(name='imaginary.so.9', path=None)]
    >>> list(
    ...     _parse_ldd([
    ...         "libwrap.so.0 => /lib/x86_64-linux-gnu/libwrap.so.0 (0x00007f1f036fd000)",
    ...     ])
    ... )
    [LinkedLibrary(name='libwrap.so.0', path=PosixPath('/lib/x86_64-linux-gnu/libwrap.so.0'))]
    """
    for line in lines:
        if (match := not_found_regex.match(line.strip())) is not None:
            yield LinkedLibrary(name=match.group(1), path=None)
            continue
        if (match := ldd_regex.match(line.strip())) is None:
            # According to man ldd only ld-linux and linux-vdso are different...
            # (The linux-vdso and ld-linux shared dependencies are special; see vdso(7) and ld.so(8).)
            assert "ld-linux" in line or "linux-vdso" in line or "linux-gate" in line, f"? {line!r}"
            continue
        yield LinkedLibrary(name=match.group(1), path=Path(match.group(2)))


def _linked_libraries_of_file(site: Site, file: Path) -> Iterator[LinkedLibrary]:
    """
    All libraries that a given file links to, using ldd.
    """
    yield from _parse_ldd(_run_ldd(site, file))


@pytest.mark.skip(reason="fails unexpected at the moment - CMK-15651")
def test_linked_libraries(site: Site) -> None:
    """
    A test to sanity check linked libraries in the installation.

    This test finds all dynamically linked binaries below the site directory and uses ldd to learn
    about the libs they link to.

    If a link cannot be resolved or the linked library is listed as forbidden below, the test will
    fail.
    """
    forbidden = [
        # make sure we don't accidentally link to old openssl anymore
        "libssl.so.1.1",
        "libcrypto.so.1.1",
    ]

    files = _run_find_dynamically_linked(site, Path(site.root))

    for file in files:
        if str(file).endswith("/share/check_mk/agents/plugins/cmk-update-agent-32"):
            # That is a 32bit binary, so let's skip checking it
            continue
        for lib in _linked_libraries_of_file(site, file):
            assert lib.name not in forbidden, f"{file} links to forbidden libraries"

            if lib.path is None:
                if str(file).endswith("/lib/seccli/naviseccli"):
                    # seccli has some libraries next to the binary
                    assert lib.name in list(p.name for p in Path(file).parent.iterdir())
                    continue
                if str(file).endswith(
                    "/share/doc/check_mk/treasures/modbus/agents/special/agent_modbus"
                ):
                    assert lib.name == "libmodbus.so.5"
                    continue

                assert False, f"Library {lib.name} was not found. Linked from {file}"
