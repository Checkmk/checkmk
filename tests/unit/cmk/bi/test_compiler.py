#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest
from fakeredis import FakeRedis

from livestatus import LivestatusResponse, Query

from cmk.bi.compiler import BICompiler
from cmk.bi.filesystem import BIFileSystem
from cmk.bi.lib import SitesCallback
from cmk.ccc.exceptions import MKGeneralException, MKTimeout
from cmk.ccc.site import SiteId


def _query(
    query: Query,
    only_sites: list[SiteId] | None = None,
    fetch_full_data: bool = False,
) -> LivestatusResponse:
    return LivestatusResponse([])


class TestLoadCompiledAggregations:
    @pytest.fixture
    def compiler(self, fs: BIFileSystem) -> BICompiler:
        return BICompiler(
            fs.etc.config,
            SitesCallback(
                all_sites_with_id_and_online=lambda: [],
                query=_query,
                translate=lambda s: s,
            ),
            fs=fs,
            redis_client=FakeRedis(),
        )

    def test_loads_when_compilation_check_succeeds(
        self, compiler: BICompiler, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        load_calls: list[None] = []
        monkeypatch.setattr(compiler, "_check_compilation_status", lambda: None)
        monkeypatch.setattr(
            compiler, "_load_compiled_aggregations", lambda: load_calls.append(None)
        )

        compiler.load_compiled_aggregations()

        assert len(load_calls) == 1

    def test_loads_when_compilation_check_fails(
        self, compiler: BICompiler, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A failed compilation still leaves whatever the store holds usable."""

        def _fail() -> None:
            raise MKGeneralException("compilation failed")

        load_calls: list[None] = []
        monkeypatch.setattr(compiler, "_check_compilation_status", _fail)
        monkeypatch.setattr(
            compiler, "_load_compiled_aggregations", lambda: load_calls.append(None)
        )

        with pytest.raises(MKGeneralException):
            compiler.load_compiled_aggregations()

        assert len(load_calls) == 1

    def test_does_not_load_when_compilation_check_times_out(
        self, compiler: BICompiler, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Loading after a timeout would run unbounded and hide the timeout itself.

        The timeout has to reach the caller so that it can report it, which it cannot
        do if loading raises an exception of its own on the way out.
        """

        def _time_out() -> None:
            raise MKTimeout("request timed out")

        def _load() -> None:
            raise AssertionError("aggregations must not be loaded after a timeout")

        monkeypatch.setattr(compiler, "_check_compilation_status", _time_out)
        monkeypatch.setattr(compiler, "_load_compiled_aggregations", _load)

        with pytest.raises(MKTimeout):
            compiler.load_compiled_aggregations()
