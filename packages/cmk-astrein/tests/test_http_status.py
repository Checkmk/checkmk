#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import ast
from http import HTTPStatus
from pathlib import Path, PurePosixPath

import pytest

from cmk.astrein.checker_http_status import (
    HTTPStatusLiteralChecker,
    LEGACY_PYTHON_SOURCES,
    load_legacy_python_files,
)
from cmk.astrein.framework import CheckerError

_REPO_ROOT = Path("/repo")
_CHECKED_FILE = _REPO_ROOT / "cmk/checked/module.py"


def _check(
    code: str,
    file_path: Path = _CHECKED_FILE,
    legacy_python_files: frozenset[PurePosixPath] = frozenset(),
) -> list[CheckerError]:
    checker = HTTPStatusLiteralChecker(
        file_path, _REPO_ROOT, code, legacy_python_files=legacy_python_files
    )
    return checker.check(ast.parse(code))


def _suggestions(code: str) -> list[str]:
    return [error.message.split("`")[1] for error in _check(code)]


@pytest.mark.parametrize(
    "code",
    [
        pytest.param("resp.status_code == 404", id="attribute_eq"),
        pytest.param("404 != resp.status_code", id="literal_on_left"),
        pytest.param("status == 404", id="name"),
        pytest.param('body["status"] == 404', id="subscript_key"),
        pytest.param("resp.status_code not in [404]", id="not_in_list"),
        pytest.param("404 in expected_status_codes", id="literal_in_status_collection"),
        pytest.param("f(status=404)", id="keyword"),
        pytest.param("f(additional_status_codes={404})", id="keyword_set"),
        pytest.param("resp.status_code = 404", id="attribute_assignment"),
        pytest.param("status_code: int = 404", id="annotated_assignment"),
        pytest.param("def f(status: int = 404): ...", id="positional_default"),
        pytest.param("async def f(*, status_code=404): ...", id="keyword_only_default"),
        pytest.param("self.send_response(404)", id="status_method"),
        pytest.param("expected_status_codes.add(404)", id="collection_add"),
        pytest.param("import httpx as h\nh.Response(404)", id="status_callable"),
        pytest.param("match resp.status_code:\n    case 404:\n        pass", id="match_value"),
        pytest.param("match status:\n    case 404 as s:\n        pass", id="match_as"),
    ],
)
def test_rejects_status_literal(code: str) -> None:
    assert _suggestions(code) == ["HTTPStatus.NOT_FOUND"]


@pytest.mark.parametrize(
    "code",
    [
        pytest.param("resp.status_code in (200, 204)", id="collection"),
        pytest.param("match status:\n    case 200 | 204:\n        pass", id="match_or"),
    ],
)
def test_rejects_each_alternative(code: str) -> None:
    assert _suggestions(code) == ["HTTPStatus.OK", "HTTPStatus.NO_CONTENT"]


def test_rejects_reason_phrase_lookup() -> None:
    assert _suggestions("from http.client import responses\nresponses[404]") == [
        "HTTPStatus.NOT_FOUND.phrase"
    ]


def test_anchors_error_to_the_literal_so_inline_suppression_works() -> None:
    code = "f(\n    url,\n    status=404,  # astrein: disable=http-status-literal\n)"
    assert _check(code) == []


@pytest.mark.parametrize(
    "code",
    [
        pytest.param("from http import HTTPStatus\nresp.status_code == HTTPStatus.OK", id="member"),
        pytest.param("200 <= resp.status_code < 300", id="range_check"),
        pytest.param("resp.status_code == 299", id="not_a_member"),
        pytest.param("resp.status_code == 404.0", id="float"),
        pytest.param("f(timeout=300)", id="unrelated_keyword"),
        pytest.param("width = 200", id="unrelated_assignment"),
        pytest.param("response.json() == 200", id="unrelated_comparison"),
        pytest.param('payload = {"status": 404}', id="dict_payload"),
        pytest.param("_FakeResponse(404)", id="unknown_callable"),
        pytest.param("sizes.append(404)", id="unrelated_collection"),
        pytest.param("from cmk.gui import http\nhttp.client.responses[404]", id="shadowed_http"),
        pytest.param("match resp.json():\n    case 404:\n        pass", id="unrelated_match"),
    ],
)
def test_allows(code: str) -> None:
    assert _check(code) == []


def test_suggests_only_members_python_3_7_provides() -> None:
    missing_on_python_3_7 = {103, 418, 425, 451}
    python_3_7_names = {
        413: "REQUEST_ENTITY_TOO_LARGE",
        414: "REQUEST_URI_TOO_LONG",
        416: "REQUESTED_RANGE_NOT_SATISFIABLE",
        422: "UNPROCESSABLE_ENTITY",
    }
    assert {status: _suggestions(f"status = {status.value}") for status in HTTPStatus} == {
        status: []
        if status in missing_on_python_3_7
        else [f"HTTPStatus.{python_3_7_names.get(status, status.name)}"]
        for status in HTTPStatus
    }


def test_skips_files_listed_as_python_3_4_sources(tmp_path: Path) -> None:
    sources = tmp_path / LEGACY_PYTHON_SOURCES
    sources.parent.mkdir(parents=True)
    sources.write_text("agents/plugins/mk_docker.py\n")

    errors = _check(
        "status = 404",
        file_path=_REPO_ROOT / "agents/plugins/mk_docker.py",
        legacy_python_files=load_legacy_python_files(tmp_path),
    )

    assert errors == []
