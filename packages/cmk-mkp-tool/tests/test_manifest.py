#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pprint
from pathlib import Path

import pydantic
import pytest

from cmk.mkp_tool import PackageName, PackagePart, PackageVersion
from cmk.mkp_tool._mkp import Manifest, read_manifest_optionally

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
        assert TEST_MANIFEST == Manifest.model_validate_json(TEST_MANIFEST.model_dump_json())

    def test_roundtrip_python(self) -> None:
        assert TEST_MANIFEST == Manifest.parse_python_string(TEST_MANIFEST.file_content())


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
