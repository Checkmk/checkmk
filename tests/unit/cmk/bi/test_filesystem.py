#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.bi.filesystem import BI_SITE_CACHE_PREFIX, BIFileSystem


def test_cache_generate_filesystem(fs: BIFileSystem) -> None:
    assert fs.cache.compiled_aggregations.exists()
    assert fs.cache.site_structure_data.exists()


def test_clear_compilation_cache(fs: BIFileSystem) -> None:
    (fs.cache.compiled_aggregations / "foo").write_text("bar")
    fs.cache.compilation_lock.write_text("lock")
    fs.cache.last_compilation.write_text("last")

    fs.cache.clear_compilation_cache()

    assert not any(fs.cache.compiled_aggregations.iterdir())
    assert not fs.cache.compilation_lock.exists()
    assert not fs.cache.last_compilation.exists()


def test_clear_compilation_cache_is_idempotent(fs: BIFileSystem) -> None:
    fs.cache.clear_compilation_cache()
    fs.cache.clear_compilation_cache()

    assert not any(fs.cache.compiled_aggregations.iterdir())
    assert not fs.cache.compilation_lock.exists()
    assert not fs.cache.last_compilation.exists()


def test_cache_get_site_structure_data_path(fs: BIFileSystem) -> None:
    site_id = "heute"
    timestamp = "1744213607"

    value = fs.cache.get_site_structure_data_path(site_id, timestamp)
    expected = fs.cache.site_structure_data / f"{BI_SITE_CACHE_PREFIX}.{site_id}.{timestamp}"

    assert value == expected


def test_cache_is_site_path(fs: BIFileSystem) -> None:
    path = fs.cache.site_structure_data / f"{BI_SITE_CACHE_PREFIX}.heute.1744213607"
    assert fs.cache.is_site_cache(path) is True


def test_cache_is_not_site_path(fs: BIFileSystem) -> None:
    path = fs.cache.site_structure_data / "not-valid-site-path"
    assert fs.cache.is_site_cache(path) is False


def test_cache_compilation_lock_path(fs: BIFileSystem) -> None:
    value = fs.cache.compilation_lock
    expected = fs.cache._root / "compilation.LOCK"
    assert value == expected


def test_cache_last_compilation_path(fs: BIFileSystem) -> None:
    value = fs.cache.last_compilation
    expected = fs.cache._root / "last_compilation"
    assert value == expected


def test_var_generate_config_filesystem(fs: BIFileSystem) -> None:
    assert fs.var.frozen_aggregations.exists()


def test_etc_bi_config(fs: BIFileSystem) -> None:
    assert fs.etc.config == fs.etc._root / "multisite.d/wato/bi_config.bi"


def test_etc_multisite_config_exists(fs: BIFileSystem) -> None:
    assert fs.etc.multisite.exists()
