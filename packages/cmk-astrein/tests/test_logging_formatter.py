#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import ast
from collections.abc import Sequence
from pathlib import Path

import pytest

from cmk.astrein.checker_logging_formatter import (
    _EXCLUDED_GLOBS,
    _INCLUDED_GLOBS,
    LoggingFormatterChecker,
)
from cmk.astrein.framework import CheckerError

_CHECKED_FILE = Path("/repo/checked/module.py")


def _check(
    code: str,
    file_path: Path = _CHECKED_FILE,
    repo_root: Path = Path("/repo"),
    *,
    excluded_globs: Sequence[str] = _EXCLUDED_GLOBS,
    included_globs: Sequence[str] = _INCLUDED_GLOBS,
) -> list[CheckerError]:
    checker = LoggingFormatterChecker(
        file_path,
        repo_root,
        code,
        excluded_globs=excluded_globs,
        included_globs=included_globs,
    )
    return checker.check(ast.parse(code))


@pytest.mark.parametrize(
    "code",
    [
        pytest.param(
            'import logging\nh.setFormatter(logging.Formatter("%(message)s"))', id="qualified"
        ),
        pytest.param(
            'import logging as L\nL.Formatter("%(asctime)s %(message)s")', id="module_alias"
        ),
        pytest.param('from logging import Formatter\nFormatter("%(message)s")', id="from_import"),
        pytest.param("from logging import Formatter as F\nF()", id="from_import_alias"),
        pytest.param("import logging.config\nlogging.Formatter()", id="import_logging_submodule"),
    ],
)
def test_rejects_formatter_construction(code: str) -> None:
    errors = _check(code)
    assert len(errors) == 1
    assert "CMKFormatter" in errors[0].message


def test_anchors_error_to_construction_call_so_inline_suppression_works() -> None:
    code = (
        "import logging\n"
        "h.setFormatter(\n"
        '    logging.Formatter("%(message)s")  # astrein: disable=logging-formatter\n'
        ")"
    )
    assert _check(code) == []


@pytest.mark.parametrize(
    "code",
    [
        pytest.param("from string import Formatter\nFormatter().parse(s)", id="string_formatter"),
        pytest.param("import logging\nother.Formatter()", id="unrelated_module"),
        pytest.param(
            "import logging\ndef f(fmt: logging.Formatter | None) -> bool:\n"
            "    return isinstance(fmt, logging.Formatter)\n",
            id="annotation_and_isinstance",
        ),
        pytest.param(
            "from cmk.ccc.log import CMKFormatter\nh.setFormatter(CMKFormatter(with_process=True))",
            id="cmk_formatter",
        ),
    ],
)
def test_allows_valid_formatter_usage(code: str) -> None:
    assert _check(code) == []


@pytest.mark.parametrize(
    "code",
    [
        pytest.param("import logging\nclass Mine(logging.Formatter):\n    pass", id="qualified"),
        pytest.param(
            "from logging import Formatter\nclass Mine(Formatter):\n    pass", id="from_import"
        ),
    ],
)
def test_rejects_subclassing_logging_formatter(code: str) -> None:
    errors = _check(code)
    assert len(errors) == 1
    assert "Subclass cmk.ccc.log.CMKFormatter" in errors[0].message


def test_allows_subclassing_cmk_formatter() -> None:
    assert _check("from cmk.ccc.log import CMKFormatter\nclass Mine(CMKFormatter):\n    pass") == []


_CMKFORMATTER_DEFINITION = "import logging\nclass CMKFormatter(logging.Formatter):\n    pass"


def test_allows_cmk_formatter_own_definition() -> None:
    assert (
        _check(_CMKFORMATTER_DEFINITION, file_path=Path("/repo/packages/cmk-ccc/cmk/ccc/log.py"))
        == []
    )


def test_rejects_cmk_formatter_named_class_in_other_file() -> None:
    errors = _check(_CMKFORMATTER_DEFINITION, file_path=Path("/repo/packages/cmk-ccc/cmk/ccc/x.py"))
    assert len(errors) == 1
    assert "Subclass cmk.ccc.log.CMKFormatter" in errors[0].message


def test_rejects_other_subclass_in_cmk_formatter_definition_file() -> None:
    errors = _check(
        "import logging\nclass Other(logging.Formatter):\n    pass",
        file_path=Path("/repo/packages/cmk-ccc/cmk/ccc/log.py"),
    )
    assert len(errors) == 1
    assert "Subclass cmk.ccc.log.CMKFormatter" in errors[0].message


@pytest.mark.parametrize(
    "code",
    [
        pytest.param(
            'import logging\nlogging.basicConfig(level=logging.INFO, format="%(message)s")',
            id="format_kw",
        ),
        pytest.param('import logging\nlogging.basicConfig(datefmt="%H:%M")', id="datefmt_kw"),
        pytest.param(
            'from logging import basicConfig\nbasicConfig(format="%(message)s")', id="from_import"
        ),
        pytest.param("import logging as L\nL.basicConfig(format=fmt)", id="module_alias"),
    ],
)
def test_rejects_basic_config_with_format(code: str) -> None:
    errors = _check(code)
    assert len(errors) == 1
    assert "handlers=[handler]" in errors[0].message


def test_allows_basic_config_without_format() -> None:
    assert _check("import logging\nlogging.basicConfig(level=logging.INFO, handlers=[h])") == []


_UVICORN_LOG_CONFIG = (
    "import uvicorn.logging\n"
    "from cmk.ccc.log import CMKFormatter\n"
    "cfg = {\n"
    '    "version": 1,\n'
    '    "formatters": {\n'
    '        "default": {"()": uvicorn.logging.DefaultFormatter, "fmt": "%(message)s"},\n'
    '        "access": {"format": "%(asctime)s %(message)s"},\n'
    '        "ours": {"()": CMKFormatter, "with_process": True},\n'
    "    },\n"
    "}"
)


def test_anchors_errors_to_the_offending_dict_config_formatters() -> None:
    errors = _check(_UVICORN_LOG_CONFIG)
    assert [e.line for e in errors] == [6, 7]


def _dict_config(imports: str, formatter: str) -> str:
    return f'{imports}\nd = {{"version": 1, "formatters": {{"f": {formatter}}}}}'


@pytest.mark.parametrize(
    "imports, formatter",
    [
        pytest.param("", '{"format": "%(message)s"}', id="no_factory"),
        pytest.param(
            "from cmk.ccc.log import CMKFormatter",
            '{"()": CMKFormatter, "fmt": "%(message)s"}',
            id="format_key",
        ),
        pytest.param("", '{"()": "cmk.ccc.log.CMKFormatter"}', id="dotted_path_string"),
        pytest.param(
            "import uvicorn.logging", '{"()": uvicorn.logging.DefaultFormatter}', id="other_class"
        ),
        pytest.param("class CMKFormatter: ...", '{"()": CMKFormatter}', id="local_lookalike"),
        pytest.param(
            "from mylib.log import CMKFormatter", '{"()": CMKFormatter}', id="other_module"
        ),
    ],
)
def test_rejects_dict_config_formatter_not_built_by_cmk_formatter(
    imports: str, formatter: str
) -> None:
    errors = _check(_dict_config(imports, formatter))
    assert len(errors) == 1
    assert '"()": CMKFormatter' in errors[0].message


@pytest.mark.parametrize(
    "code",
    [
        pytest.param(
            _dict_config("from cmk.ccc.log import CMKFormatter as F", '{"()": F}'),
            id="aliased_class",
        ),
        pytest.param(
            _dict_config("from cmk.ccc import log", '{"()": log.CMKFormatter}'),
            id="module_from_package",
        ),
        pytest.param(
            _dict_config("import cmk.ccc.log", '{"()": cmk.ccc.log.CMKFormatter}'),
            id="dotted_module",
        ),
        pytest.param(
            _dict_config("import cmk.ccc.log as L", '{"()": L.CMKFormatter}'), id="aliased_module"
        ),
        pytest.param(
            _dict_config(
                "from cmk.ccc.log import CMKFormatter", '{"()": CMKFormatter, "legacy": True}'
            ),
            id="factory_with_options",
        ),
        pytest.param('d = {"version": 1, "handlers": {}}', id="no_formatters"),
        pytest.param('d = {"formatters": {"a": {"format": "x"}}}', id="no_version"),
    ],
)
def test_allows_non_offending_dict(code: str) -> None:
    assert _check(code) == []


_FORMATTER_CALL = "import logging\nlogging.Formatter()"
_DUMMY_EXCLUDED_GLOBS = ("excluded_top/**", "packages/excluded_pkg/**")
_DUMMY_INCLUDED_GLOBS = ("packages/excluded_pkg/migrated.py",)


@pytest.mark.parametrize(
    "file_path, expected_errors",
    [
        pytest.param(Path("/repo/excluded_top/mod.py"), 0, id="excluded_top_level"),
        pytest.param(Path("/repo/packages/excluded_pkg/other.py"), 0, id="excluded_package"),
        pytest.param(Path("/repo/packages/other_pkg/mod.py"), 1, id="outside_every_glob"),
        pytest.param(Path("/repo/packages/excluded_pkg/migrated.py"), 1, id="force_included"),
        pytest.param(
            Path("/repo/packages/excluded_pkg/not_migrated.py"), 0, id="sibling_of_force_included"
        ),
    ],
)
def test_glob_scoping_with_included_override(file_path: Path, expected_errors: int) -> None:
    errors = _check(
        _FORMATTER_CALL,
        file_path=file_path,
        excluded_globs=_DUMMY_EXCLUDED_GLOBS,
        included_globs=_DUMMY_INCLUDED_GLOBS,
    )
    assert len(errors) == expected_errors
