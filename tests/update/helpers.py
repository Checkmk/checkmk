#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from tests.testlib.site import Site
from tests.testlib.utils import parse_files


def check_errors_in_log_files(site: Site) -> None:
    """Assert that there are no unexpected errors in the site log-files"""
    # Default pattern should be "^.*error.*$"
    # * TODO: Remove "sigterm" lookahead from pattern after CMK-24766 is done
    # * TODO: Remove "Interface_2" lookahead from pattern after CMK-18603 is done
    # * TODO: Remove "wsgi" lookahead from pattern after CMK-27248 is done
    # * using OPENSSL version > 3.4.0 in test-containers leads to an error in web.log when starting
    #   a cmk site with version <= 2.3.0p40
    content_pattern = "^(?!.*(sigterm))(?!.*(Interface_2.rrd))(?!.*(wsgi))(?!.*(Error building RPM packet)).*error.*$"

    error_match_dict = parse_files(
        path_name=site.logs_dir,
        files_name_pattern="*log*",
        content_pattern=content_pattern,
        sudo=True,
    )

    assert not error_match_dict, f"Error string found in one or more log files: {error_match_dict}"
