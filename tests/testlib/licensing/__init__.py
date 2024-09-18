#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterator
from contextlib import contextmanager, nullcontext
from pathlib import Path

from tests.testlib.site import Site

from cmk.ccc.version import Edition

_SOURCE_DIR_RELATIVE_TO_THIS_FILE = Path("license_files")
_LICENSING_DIR_RELATIVE_TO_SITE_ROOT = Path("var/check_mk/licensing")


@contextmanager
def license_site(
    site: Site,
    target_edition: Edition | None = None,
) -> Iterator[None]:
    target_edition = target_edition or site.version.edition
    with (
        site.copy_file(
            str(_SOURCE_DIR_RELATIVE_TO_THIS_FILE / target_edition.short / "verification_response"),
            str(_LICENSING_DIR_RELATIVE_TO_SITE_ROOT / "verification_response"),
        ),
        (
            site.copy_file(
                str(
                    _SOURCE_DIR_RELATIVE_TO_THIS_FILE
                    / target_edition.short
                    / "verification_request_id"
                ),
                str(_LICENSING_DIR_RELATIVE_TO_SITE_ROOT / "verification_request_id"),
            )
            if target_edition in (Edition.CCE, Edition.CME)
            else nullcontext()
        ),
    ):
        site.restart_core()
        yield
