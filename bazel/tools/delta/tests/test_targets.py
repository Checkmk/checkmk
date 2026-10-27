# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from collections.abc import Mapping

from bazel_delta.targets import owning_targets, OwningRule, Query, query_errors


def _rule(
    name: str,
    srcs: list[str],
    hdrs: list[str] | None = None,
    kind: str = "py_library",
    tags: list[str] | None = None,
) -> str:
    attribute = [{"name": "srcs", "type": "LABEL_LIST", "stringListValue": srcs}]
    if hdrs is not None:
        attribute.append({"name": "hdrs", "type": "LABEL_LIST", "stringListValue": hdrs})
    if tags is not None:
        attribute.append({"name": "tags", "type": "STRING_LIST", "stringListValue": tags})
    return json.dumps(
        {"type": "RULE", "rule": {"name": name, "ruleClass": kind, "attribute": attribute}}
    )


def _fake_query(outputs: Mapping[tuple[str, str], str]) -> Query:
    """Returns the output given for an expression and output format, nothing otherwise."""

    def query(expression: str, output: str) -> str:
        return outputs.get((expression, output), "")

    return query


def test_targets_listing_a_file_in_their_srcs_own_it() -> None:
    query = _fake_query(
        {
            ('set("cmk/a.py" "cmk/b.py")', "label"): "//cmk:a.py\n//cmk:b.py\n",
            (
                'same_pkg_direct_rdeps(set("//cmk:a.py" "//cmk:b.py"))',
                "streamed_jsonproto",
            ): "\n".join(
                [
                    _rule("//cmk:lib", ["//cmk:a.py", "//cmk:other.py"]),
                    _rule("//cmk:data_only", []),
                    _rule("//cmk:test", ["//cmk:b.py"], kind="py_test", tags=["slow"]),
                ]
            ),
        }
    )
    owning = owning_targets(query, ["cmk/a.py", "cmk/b.py"])
    assert owning.targets == ["//cmk:lib", "//cmk:test"]
    assert owning.rules == {
        "cmk/a.py": [OwningRule("//cmk:lib", "py_library", frozenset())],
        "cmk/b.py": [OwningRule("//cmk:test", "py_test", frozenset({"slow"}))],
    }


def test_files_in_a_filegroup_are_owned_by_its_users_in_the_package() -> None:
    query = _fake_query(
        {
            ('set("tests/testlib/out.py")', "label"): "//tests/testlib:out.py\n",
            (
                'same_pkg_direct_rdeps(set("//tests/testlib:out.py"))',
                "streamed_jsonproto",
            ): _rule("//tests/testlib:srcs", ["//tests/testlib:out.py"], kind="filegroup"),
            (
                'same_pkg_direct_rdeps(set("//tests/testlib:srcs"))',
                "streamed_jsonproto",
            ): "\n".join(
                [
                    _rule("//tests/testlib:testlib", ["//tests/testlib:srcs"]),
                    _rule("//tests/testlib:data", [], kind="filegroup"),
                ]
            ),
        }
    )
    owning = owning_targets(query, ["tests/testlib/out.py"])
    assert owning.targets == ["//tests/testlib:srcs", "//tests/testlib:testlib"]
    assert owning.rules == {
        "tests/testlib/out.py": [
            OwningRule("//tests/testlib:srcs", "filegroup", frozenset()),
            OwningRule("//tests/testlib:testlib", "py_library", frozenset()),
        ]
    }


def test_files_of_the_root_package_are_repo_paths() -> None:
    query = _fake_query(
        {
            ('set("setup.py")', "label"): "//:setup.py\n",
            ('same_pkg_direct_rdeps(set("//:setup.py"))', "streamed_jsonproto"): _rule(
                "//:setup", ["//:setup.py"]
            ),
        }
    )
    assert set(owning_targets(query, ["setup.py"]).rules) == {"setup.py"}


def test_files_in_no_package_have_no_targets() -> None:
    owning = owning_targets(_fake_query({}), ["notes.txt"])
    assert owning.targets == []
    assert owning.rules == {}


def test_targets_listing_a_file_in_their_hdrs_own_it() -> None:
    query = _fake_query(
        {
            ('set("src/foo.h")', "label"): "//src:foo.h\n",
            ('same_pkg_direct_rdeps(set("//src:foo.h"))', "streamed_jsonproto"): _rule(
                "//src:foo", ["//src:foo.cc"], hdrs=["//src:foo.h"]
            ),
        }
    )
    owning = owning_targets(query, ["src/foo.h"])
    assert owning.targets == ["//src:foo"]
    assert set(owning.rules) == {"src/foo.h"}


def test_skipped_files_are_no_query_errors() -> None:
    stderr = (
        "ERROR: Skipping 'notes.txt': no such target '//:notes.txt': ...\n"
        "WARNING: --keep_going specified, ignoring errors. Results may be inaccurate\n"
    )
    assert query_errors(stderr) == ""


def test_build_files_that_fail_to_load_are_query_errors() -> None:
    stderr = (
        "ERROR: /repo/pkg/BUILD:2:1: syntax error at 'newline': expected ,\n"
        "ERROR: Skipping 'pkg/a.py': no such target '//pkg:a.py': ...\n"
    )
    assert (
        query_errors(stderr) == "ERROR: /repo/pkg/BUILD:2:1: syntax error at 'newline': expected ,"
    )


def test_skipped_files_of_packages_that_fail_to_load_are_query_errors() -> None:
    stderr = (
        "ERROR: Skipping 'pkg/a.py': error loading package 'pkg': Label '//nope:x.bzl' is invalid\n"
        "ERROR: Skipping 'notes.txt': no such target '//:notes.txt': ...\n"
    )
    assert query_errors(stderr) == (
        "ERROR: Skipping 'pkg/a.py': error loading package 'pkg': Label '//nope:x.bzl' is invalid"
    )


def test_files_with_non_ascii_names_have_their_targets() -> None:
    query = _fake_query(
        {
            ('set("doc/café.py")', "label"): "//doc:café.py\n",
            ('same_pkg_direct_rdeps(set("//doc:café.py"))', "streamed_jsonproto"): _rule(
                "//doc:doc", ["//doc:café.py"]
            ),
        }
    )
    owning = owning_targets(query, ["doc/café.py"])
    assert owning.targets == ["//doc:doc"]
    assert set(owning.rules) == {"doc/café.py"}
