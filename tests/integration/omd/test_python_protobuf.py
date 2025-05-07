#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterator
from pathlib import Path

import pytest

from tests.testlib.site import Site


def test_protobuf_api_implementation(site: Site) -> None:
    assert (
        site.python_helper("helper_test_protobuf_api_implementation.py").check_output().rstrip()
        == "upb"
    )


@pytest.fixture(name="test_dir")
def fixture_test_dir(site: Site) -> Iterator[Path]:
    site.makedirs("protobuf")
    try:
        yield site.path("protobuf")
    finally:
        site.delete_dir("protobuf")


@pytest.fixture(name="proto_source_file")
def fixture_proto_source_file(test_dir: Path, site: Site) -> Path:
    proto_path = test_dir / "test.proto"
    site.write_file(
        str(proto_path.relative_to(site.root)),
        """syntax = "proto2";

package tutorial;

message Person {
  optional string name = 1;
  optional int32 id = 2;
  optional string email = 3;

  enum PhoneType {
    MOBILE = 0;
    HOME = 1;
    WORK = 2;
  }

  message PhoneNumber {
    optional string number = 1;
    optional PhoneType type = 2 [default = HOME];
  }

  repeated PhoneNumber phones = 4;
}

message AddressBook {
  repeated Person people = 1;
}""",
    )
    return proto_path


@pytest.fixture(name="protobuf_py")
def fixture_protobuf_py(site: Site, test_dir: Path, proto_source_file: Path) -> Iterator[None]:
    target_dir = site.path("local/lib/python3/")
    _ = site.run(
        [
            "protoc",
            "-I=%s" % test_dir,
            "--python_out",
            target_dir.as_posix(),
            str(proto_source_file),
        ]
    )

    assert site.file_exists("local/lib/python3/test_pb2.py")
    yield
    site.delete_file("local/lib/python3/test_pb2.py")


@pytest.mark.usefixtures("protobuf_py")
def test_python_protobuf(site: Site) -> None:
    assert site.python_helper("helper_test_python_protobuf.py").check_output().rstrip() == "1"
