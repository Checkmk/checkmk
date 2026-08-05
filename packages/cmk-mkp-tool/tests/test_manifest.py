#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import io
import pprint
import tarfile
from pathlib import Path

import pydantic
import pytest

from cmk.mkp_tool import PackageError, PackageName, PackagePart, PackageVersion
from cmk.mkp_tool._mkp import (
    extract_manifest,
    extract_manifest_optionally,
    extract_manifests,
    Manifest,
    read_manifest_optionally,
)

TEST_MANIFEST = Manifest(
    title="Unit test package",
    name=PackageName("test_package"),
    description="A nice package to test with. Also I want to thank my grandma.",
    version=PackageVersion("1.2.3-prerelease.23+42"),
    version_packaged="2.2.0p3",
    version_min_required="2.1.0p13",
    version_usable_until="2.2.0",
    author="myself",
    download_url="https://boulderbugle.com/c4zzwmjs",
    files={p: [Path("example-file.py")] for p in PackagePart},
)


class TestManifest:
    def test_read_15_manifest(self) -> None:
        """make sure we can read old packages without 'usable until'"""
        Manifest.parse_python_string(
            "{'author': 'Checkmk GmbH (mo)',\n"
            " 'description': '',\n"
            " 'download_url': '',\n"
            " 'files': {},\n"
            " 'name': 'test-package',\n"
            " 'title': 'Test Package',\n"
            " 'version': '1.0.0',\n"
            " 'version.min_required': '2.1.0',\n"
            " 'version.packaged': '2.1.0p2'}\n"
        )

    def test_read_20_manifest(self) -> None:
        """make sure we can read old packages with 'num_files'"""
        Manifest.parse_python_string(
            "{'author': 'Checkmk GmbH (mo)',\n"
            " 'description': '',\n"
            " 'download_url': '',\n"
            " 'files': {},\n"
            " 'num_files': 0,\n"
            " 'name': 'test-package',\n"
            " 'title': 'Test Package',\n"
            " 'version': '1.0.0',\n"
            " 'version.min_required': '2.1.0',\n"
            " 'version.packaged': '2.1.0p2'}\n"
        )

    def test_read_21_manifest(self) -> None:
        Manifest.parse_python_string(
            "{'author': 'Checkmk GmbH (mo)',\n"
            " 'description': '',\n"
            " 'download_url': '',\n"
            " 'files': {'checks': ['just-some-file']},\n"
            " 'name': 'test-package-only-21',\n"
            " 'title': 'Test Package for 2.1 only',\n"
            " 'version': '1.0',\n"
            " 'version.min_required': '2.1.0',\n"
            " 'version.packaged': '2022.08.08',\n"
            " 'version.usable_until': '2.2.0'}\n"
        )

    def test_roundtrip_json(self) -> None:
        assert Manifest.model_validate_json(TEST_MANIFEST.model_dump_json()) == TEST_MANIFEST

    def test_roundtrip_python(self) -> None:
        assert Manifest.parse_python_string(TEST_MANIFEST.file_content()) == TEST_MANIFEST


def test_read_manifest_optionally_ok(tmp_path: Path) -> None:
    ok_manifest_path = tmp_path / "ok"
    ok_manifest_path.write_text(TEST_MANIFEST.file_content())

    manifest = read_manifest_optionally(ok_manifest_path)
    assert manifest
    assert manifest == TEST_MANIFEST


def test_read_manifest_optionally_invalid(tmp_path: Path) -> None:
    invalid_manifest_path = tmp_path / "invalid"
    invalid_manifest_dict = {
        k: v for k, v in TEST_MANIFEST.model_dump(by_alias=True).items() if k != "name"
    }
    invalid_manifest_path.write_text(f"{pprint.pformat(invalid_manifest_dict)}\n")

    assert read_manifest_optionally(invalid_manifest_path) is None


def test_read_manifest_optionally_missing(tmp_path: Path) -> None:
    assert read_manifest_optionally(tmp_path / "missing") is None


def test_field_conversion() -> None:
    m = Manifest.parse_python_string(
        "{'author': 'Checkmk GmbH (mo)',\n"
        " 'description': '',\n"
        " 'download_url': '',\n"
        " 'files': {},\n"
        " 'name': 'test-package',\n"
        " 'title': 'Test Package',\n"
        " 'version': '1.0.0',\n"
        " 'version.min_required': '2.1.0',\n"
        " 'version.packaged': '2.1.0p2'}\n"
    )
    assert isinstance(m.version, PackageVersion)


def test_field_conversion_package_name() -> None:
    with pytest.raises(pydantic.ValidationError, match="must start with a letter or underscore"):
        Manifest.parse_python_string(
            "{'author': 'Checkmk GmbH (mo)',\n"
            " 'description': '',\n"
            " 'download_url': '',\n"
            " 'files': {},\n"
            " 'name': '111',\n"
            " 'title': 'Test Package',\n"
            " 'version': '1.0.0',\n"
            " 'version.min_required': '2.1.0',\n"
            " 'version.packaged': '2.1.0p2'}\n"
        )


def _make_tgz(members: dict[str, bytes], *, dirs: tuple[str, ...] = ()) -> bytes:
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as tar:
        for name in dirs:
            info = tarfile.TarInfo(name)
            info.type = tarfile.DIRTYPE
            tar.addfile(info)
        for name, content in members.items():
            info = tarfile.TarInfo(name)
            info.size = len(content)
            tar.addfile(info, io.BytesIO(content))
    return buffer.getvalue()


class TestExtractManifest:
    def test_ok(self) -> None:
        mkp = _make_tgz({"info": TEST_MANIFEST.file_content().encode()})

        assert extract_manifest(mkp) == TEST_MANIFEST

    def test_info_missing(self) -> None:
        mkp = _make_tgz({"something-else": b"whatever"})

        with pytest.raises(PackageError, match="'info' not contained in MKP"):
            _ = extract_manifest(mkp)

    def test_info_is_not_a_regular_file(self) -> None:
        mkp = _make_tgz({}, dirs=("info",))

        with pytest.raises(PackageError, match="'info' is not a regular file"):
            _ = extract_manifest(mkp)

    def test_not_a_tarball(self) -> None:
        with pytest.raises(tarfile.TarError):
            _ = extract_manifest(b"this is not an MKP")


class TestExtractManifestOptionally:
    def test_ok(self, tmp_path: Path) -> None:
        mkp_path = tmp_path / "ok.mkp"
        mkp_path.write_bytes(_make_tgz({"info": TEST_MANIFEST.file_content().encode()}))

        assert extract_manifest_optionally(mkp_path) == TEST_MANIFEST

    def test_broken_file_is_swallowed(self, tmp_path: Path) -> None:
        broken = tmp_path / "broken.mkp"
        broken.write_bytes(b"not an MKP at all")

        assert extract_manifest_optionally(broken) is None

    def test_missing_file_is_swallowed(self, tmp_path: Path) -> None:
        assert extract_manifest_optionally(tmp_path / "missing.mkp") is None


class TestExtractManifests:
    def test_empty(self) -> None:
        assert extract_manifests([]) == []

    def test_broken_files_are_filtered_out(self, tmp_path: Path) -> None:
        good = tmp_path / "good.mkp"
        good.write_bytes(_make_tgz({"info": TEST_MANIFEST.file_content().encode()}))
        broken = tmp_path / "broken.mkp"
        broken.write_bytes(b"not an MKP at all")

        assert extract_manifests([good, broken, tmp_path / "missing.mkp"]) == [TEST_MANIFEST]


def test_field_conversion_package_part() -> None:
    with pytest.raises(pydantic.ValidationError, match="Input should be"):
        Manifest.parse_python_string(
            "{'author': 'Checkmk GmbH (mo)',\n"
            " 'description': '',\n"
            " 'download_url': '',\n"
            " 'files': {'not-a-package-part': ['just-some-file']},\n"
            " 'name': 'test-package-only-21',\n"
            " 'title': 'Test Package for 2.1 only',\n"
            " 'version': '1.0',\n"
            " 'version.min_required': '2.1.0',\n"
            " 'version.packaged': '2022.08.08',\n"
            " 'version.usable_until': '2.2.0'}\n"
        )
