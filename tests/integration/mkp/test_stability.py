#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from pathlib import Path
from shutil import copyfile
from tempfile import mkdtemp

import pytest

from tests.integration.mkp import lib

from tests.testlib.site import Site
from tests.testlib.web_session import CMKWebSession


@pytest.mark.skip_if_edition("saas")
def test_site_availability_after_mkp_removal(site: Site, web: CMKWebSession) -> None:
    """
    Removing or disabling MKPs should not cause the entire UI to crash


    """
    mkp_name = "foo"
    mkp_filename = f"{mkp_name}-0.0.1.mkp"
    mkp_path = Path(__file__).parent / mkp_filename
    tmp_dir = Path(mkdtemp(prefix="pytest_cmk_"))
    tmp_mkp_path = tmp_dir / mkp_filename

    # Copying is important because of dev machines the site user is potentially not allowed to
    # access the dev's home directory.
    copyfile(mkp_path, tmp_mkp_path)
    tmp_dir.chmod(0o775)
    tmp_mkp_path.chmod(0o664)

    lib.add_extension(site, tmp_mkp_path)
    lib.enable_extension(site, mkp_name)
    lib.disable_extension(site, mkp_name)
    lib.remove_extension(site, mkp_name)
    tmp_mkp_path.unlink(missing_ok=True)

    web.get("")
    # No explicit assertion needed. The crash report in the response will be detected by the site
    # object, which will make the test fail.
