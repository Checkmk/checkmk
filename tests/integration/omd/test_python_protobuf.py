#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterator
from pathlib import Path

import pytest

from tests.testlib import import_module_hack
from tests.testlib.site import Site


def test_protobuf_api_implementation_is_cpp() -> None:
    from google.protobuf.internal import api_implementation

    assert api_implementation.Type() == "cpp"


@pytest.fixture(name="test_dir")
def fixture_test_dir(site: Site) -> Iterator[Path]:
    site.makedirs("protobuf")
    yield Path(site.path("protobuf"))
    # site.delete_dir("protobuf")


@pytest.fixture(name="proto_source_file")
def fixture_proto_source_file(test_dir: Path, site: Site) -> Path:
    proto_path = test_dir / "test.proto"
    with proto_path.open("w") as f:
        f.write(
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
}"""
        )
    return proto_path


@pytest.fixture(name="protobuf_py")
def fixture_protobuf_py(site: Site, test_dir: Path, proto_source_file: Path) -> Path:
    p = site.execute(
        ["protoc", "-I=%s" % test_dir, "--python_out=%s" % test_dir, str(proto_source_file)]
    )
    assert p.wait() == 0

    py_file = test_dir / "test_pb2.py"
    assert py_file.exists()
    return py_file


def test_python_protobuf(site: Site, protobuf_py: Path) -> None:
    test_pb2 = import_module_hack(str(protobuf_py))

    address_book = test_pb2.AddressBook()

    person = address_book.people.add()
    person.id = 1234
    person.name = "John Doe"
    person.email = "jdoe@example.com"

    serialized = address_book.SerializeToString()

    address_book2 = test_pb2.AddressBook()
    address_book2.ParseFromString(serialized)
    assert len(address_book.people) == 1
