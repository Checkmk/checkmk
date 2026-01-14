#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

import os
import re
import shlex
from collections.abc import Collection, Iterator
from pathlib import Path
from typing import NamedTuple

from tests.testlib.site import Site

ldd_regex = re.compile(r"(\S+) => (\S+) \(0x[0-9a-f]+\)")
not_found_regex = re.compile(r"(\S+) => not found")


class LinkedLibrary(NamedTuple):
    """
    A shared library that is linked to some dynamically linked binary in our system.
    """

    name: str
    path: Path | None

    @classmethod
    def from_ldd_output(cls, line: str) -> LinkedLibrary | None:
        if (match := not_found_regex.match(line.strip())) is not None:
            return cls(name=match.group(1), path=None)

        if (match := ldd_regex.match(line.strip())) is not None:
            return cls(name=match.group(1), path=Path(match.group(2)))

        # According to 'man ldd':
        #   The linux-vdso and ld-linux shared dependencies are special; see vdso(7) and ld.so(8).
        # linux-gate appears to be special as well and "statically linked" occurs when a
        # "dynamic executable" doesn't link to any shared libraries.
        if any(
            allowed in line
            for allowed in ("ld-linux", "linux-vdso", "linux-gate", "statically linked")
        ):
            return None

        raise ValueError(f"failed to parse ldd output: {line!r}")


def _run_find_dynamically_linked(site: Site, path: Path) -> frozenset[Path]:
    """
    Use find to search all dynamically linked executables in the given path.
    """

    find_result = site.check_output(
        shlex.split(f"find -L {path} -type f -executable -exec file {{}} +")
    ).splitlines()

    return frozenset(
        Path(line.split(":")[0]).resolve() for line in find_result if "dynamically linked" in line
    )


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
    return (
        linked_lib
        for line in lines
        if (linked_lib := LinkedLibrary.from_ldd_output(line)) is not None
    )


def _linked_libraries_of_file(site: Site, file: Path) -> Iterator[LinkedLibrary]:
    """
    All libraries that a given file links to, using ldd.
    """
    yield from _parse_ldd(_run_ldd(site, file))


def _is_in_exclude_list(file: Path, exclusions: Collection[str]) -> bool:
    return any(str(file).endswith(path) for path in exclusions)


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

    files = _run_find_dynamically_linked(site, site.root)

    exclude_entirely = [
        # These are platform specific binaries.
        "lib/python3/cmk/plugins/oracle/agents/mk-oracle.solaris",
        "lib/python3/cmk/plugins/oracle/agents/mk-oracle.aix",
        "lib/python3/cmk/plugins/oracle/agents/mk-oracle.exe",
    ]

    exclude_from_forbidden_links_check = [
        # Some monitoring plugins link to existing libraries on the host, which in turn link to
        # the host's potentially older OpenSSL.
        "lib/nagios/plugins/check_ldap",
        "lib/nagios/plugins/check_mysql",
        "lib/nagios/plugins/check_mysql_query",
        "lib/nagios/plugins/check_pgsql",
        # To be investigated
        "bin/heirloom-mailx",
        "lib/python3.13/site-packages/netsnmp/client_intf.cpython-313-x86_64-linux-gnu.so",
        "var/tmp/xinetd",
        # Actually fixed, but not here
        "lib/nagios/plugins/check_nrpe",
        # system kerberos links on certain distros to openssl 1, see CMK-15651
        "lib/python3.13/site-packages/activedirectory/protocol/krb5.cpython-313-x86_64-linux-gnu.so",
        # ToDo: Pymsql links on certain distros to openssl 1, see CMK-21906
        "lib/python3.13/site-packages/pymssql/_mssql.cpython-313-x86_64-linux-gnu.so",
        "lib/python3.13/site-packages/pymssql/_pymssql.cpython-313-x86_64-linux-gnu.so",
        # ToDo: _ldap links on certain distros to openssl 1, see CMK-21908
        "lib/python3.13/site-packages/_ldap.cpython-313-x86_64-linux-gnu.so",
        # ToDo: SSLeay links on certain distros to openssl 1, see CMK-21910
        "lib/perl5/lib/perl5/x86_64-linux-thread-multi/auto/Crypt/SSLeay/SSLeay.so",
        # ToDo: Psycog 2 links on certain distros to openssl 1, see CMK-21909
        "lib/python3.13/site-packages/psycopg2/_psycopg.cpython-313-x86_64-linux-gnu.so",
    ]

    if os.environ["DISTRO"] == "almalinux-8":
        # ToDo: dbm links on almalinux-8 to /lib64/libcrypto.so.1.1, see CMK-22718
        exclude_from_forbidden_links_check.append(
            "lib/python3.13/lib-dynload/_dbm.cpython-313-x86_64-linux-gnu.so"
        )

    for file in files:
        if _is_in_exclude_list(file, exclude_entirely):
            continue

        for lib in _linked_libraries_of_file(site, file):
            if not _is_in_exclude_list(file, exclude_from_forbidden_links_check):
                assert lib.name not in forbidden, f"{file} links to forbidden libraries"

            if lib.path is None:
                # guess we don't care about treasures
                if str(file).endswith(
                    "share/doc/check_mk/treasures/modbus/agents/special/agent_modbus"
                ):
                    assert lib.name == "libmodbus.so.5"
                    continue

                if "lib/perl5/lib/perl5/auto/NetSNMP/" in str(file):
                    # Multiple missing links here. To be investigated.
                    continue

                assert False, f"Library {lib.name} was not found. Linked from {file}"


def test_perl_rrds_links_against_omd_rrd_so(site: Site) -> None:
    distro = os.environ["DISTRO"]
    if "sles" in distro or "alma" in distro:
        perl_rrd_so = (
            Path(site.root) / "lib/perl5/lib/perl5/x86_64-linux-thread-multi/auto/RRDs/RRDs.so"
        )
    else:
        perl_rrd_so = (
            Path(site.root) / "lib/perl5/lib/perl5/x86_64-linux-gnu-thread-multi/auto/RRDs/RRDs.so"
        )

    linked_rrd_libs = [
        linked_library
        for linked_library in _parse_ldd(_run_ldd(site, perl_rrd_so))
        if "librrd" in linked_library.name
    ]
    assert len(linked_rrd_libs) == 1, (
        f"RRDs.so should link to exactly one librrd but ldd returned: {linked_rrd_libs}"
    )
    assert linked_rrd_libs[0].path == Path(site.root) / "lib/librrd.so.8", (
        "RRDs.so should link against a librrd which is shipped with omd."
    )
