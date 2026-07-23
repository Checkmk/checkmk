#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from tests.testlib.site import Site


def test_erl_in_bin(site: Site) -> None:
    assert site.path("bin/erl").exists()


def test_erl_version(site: Site) -> None:
    cmd = [
        "erl",
        "-noshell",
        "-eval",
        "{ok,Version} = file:read_file(filename:join("
        "[code:root_dir(),'releases',erlang:system_info(otp_release),'OTP_VERSION']"
        ")),io:fwrite(Version),halt().",
    ]
    assert "26.2.5.13" in site.check_output(cmd)


def test_erlang_ssl_smoke(site: Site) -> None:
    cmd = [
        "erl",
        "-noshell",
        "-eval",
        "ok = crypto:start(), "
        "ok = io:format('~p~n~n~p~n~n', [crypto:supports(), ssl:versions()]), init:stop().",
    ]
    assert "ciphers" in site.check_output(cmd)
