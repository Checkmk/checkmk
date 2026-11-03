#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import ast
from collections.abc import Sequence
from pathlib import Path

from cmk.astrein.checkers.logging_named_placeholder import (
    _EXCLUDED_PREFIXES,
    _INCLUDED_PATHS,
    LoggingNamedPlaceholderChecker,
)
from cmk.astrein.framework import CheckerError


def _check_logging(
    code: str,
    file_path: Path = Path("/repo/packages/cmk-astrein/cmk/astrein/foo.py"),
    repo_root: Path = Path("/repo"),
    excluded_prefixes: Sequence[str] = (),
    included_paths: Sequence[str] = (),
) -> list[CheckerError]:
    checker = LoggingNamedPlaceholderChecker(
        file_path,
        repo_root,
        code,
        excluded_prefixes=excluded_prefixes,
        included_paths=included_paths,
    )
    return checker.check(ast.parse(code))


def test_logging_rejects_positional_placeholder() -> None:
    errors = _check_logging('logger.info("%s unknown", foo)')
    assert len(errors) == 1
    assert "named `%(name)s` placeholders" in errors[0].message


def test_logging_rejects_multiple_positional_placeholders() -> None:
    errors = _check_logging('logger.warning("%s and %s", a, b)')
    assert len(errors) == 1


def test_logging_rejects_positional_with_flags_width_precision() -> None:
    errors = _check_logging('logger.error("value=%-5.2f", x)')
    assert len(errors) == 1


def test_logging_rejects_non_string_conversion() -> None:
    errors = _check_logging('logger.debug("%d items", n)')
    assert len(errors) == 1


def test_logging_rejects_positional_in_log_method() -> None:
    errors = _check_logging('logger.log(logging.INFO, "%s", x)')
    assert len(errors) == 1


def test_logging_rejects_mixed_named_and_positional() -> None:
    errors = _check_logging('logger.info("%(a)s %s", {"a": a}, b)')
    assert len(errors) == 1


def test_logging_allows_named_placeholder() -> None:
    assert _check_logging('logger.info("%(thing)s unknown", {"thing": foo})') == []


def test_logging_allows_multiple_named_placeholders() -> None:
    assert _check_logging('logger.warning("%(a)s and %(b)s", {"a": a, "b": b})') == []


def test_logging_allows_named_placeholder_with_flags_width_precision() -> None:
    assert _check_logging('logger.error("value=%(value)-5.2f", {"value": x})') == []


def test_logging_allows_named_placeholder_with_literal_percent() -> None:
    assert _check_logging('logger.info("%(pct)s%% done", {"pct": p})') == []


def test_logging_allows_message_without_format_args() -> None:
    assert _check_logging('logger.info("just a plain message")') == []


def test_logging_allows_percent_text_without_format_args() -> None:
    # No format args -> "%s" is literal text, not a placeholder.
    assert _check_logging('logger.info("ratio is 50% saturated")') == []


def test_logging_allows_log_method_without_format_args() -> None:
    assert _check_logging('logger.log(logging.INFO, "plain message")') == []


def test_logging_ignores_non_constant_message() -> None:
    # A variable message cannot be inspected statically.
    assert _check_logging("logger.info(msg, x)") == []


def test_logging_ignores_warn_method() -> None:
    # `logger.warn` is not a checked method: ruff's logging rules already reject it in
    # favour of `logger.warning`.
    assert _check_logging('warnings.warn("%s deprecated", DeprecationWarning)') == []


def test_logging_ignores_non_logging_method() -> None:
    assert _check_logging('obj.send("%s", x)') == []


def test_logging_respects_suppression_comment() -> None:
    code = 'logger.info("%s", foo)  # astrein: disable=logging-named-placeholder'
    assert _check_logging(code) == []


_POSITIONAL_LOG_CALL = 'logger.info("%s", foo)'
_DUMMY_EXCLUDED_PREFIXES = ("excluded_top", "packages/excluded_pkg")
_DUMMY_INCLUDED_PATHS = ("packages/excluded_pkg/migrated.py",)


def _check_exclusion(file_path: Path) -> list[CheckerError]:
    return _check_logging(
        _POSITIONAL_LOG_CALL,
        file_path=file_path,
        excluded_prefixes=_DUMMY_EXCLUDED_PREFIXES,
        included_paths=_DUMMY_INCLUDED_PATHS,
    )


def test_logging_skips_file_under_excluded_top_level_dir() -> None:
    assert _check_exclusion(Path("/repo/excluded_top/mod.py")) == []


def test_logging_skips_file_under_excluded_package() -> None:
    assert _check_exclusion(Path("/repo/packages/excluded_pkg/other.py")) == []


def test_logging_enforced_for_path_outside_every_excluded_prefix() -> None:
    assert len(_check_exclusion(Path("/repo/packages/other_pkg/mod.py"))) == 1


def test_logging_enforced_for_force_included_path_below_excluded_prefix() -> None:
    assert len(_check_exclusion(Path("/repo/packages/excluded_pkg/migrated.py"))) == 1


def test_logging_skips_sibling_of_force_included_file() -> None:
    assert _check_exclusion(Path("/repo/packages/excluded_pkg/not_migrated.py")) == []


def test_logging_defaults_to_production_exclusion_config() -> None:
    # Defaults must reference the production tuples so real behavior is unchanged.
    checker = LoggingNamedPlaceholderChecker(
        file_path=Path("/repo/foo.py"),
        repo_root=Path("/repo"),
        source_code=_POSITIONAL_LOG_CALL,
    )
    assert checker._excluded_prefixes is _EXCLUDED_PREFIXES  # noqa: SLF001
    assert checker._included_paths is _INCLUDED_PATHS  # noqa: SLF001
