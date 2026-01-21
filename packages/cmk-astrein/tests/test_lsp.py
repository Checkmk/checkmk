#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os
from pathlib import Path

import pytest
from lsprotocol import types as lsp

from cmk.astrein.framework import CheckerError
from cmk.astrein.lsp import (
    _checker_error_to_diagnostic,
    AstreinLanguageServer,
    create_server,
    get_diagnostics,
)


def _simulate_client_initialize(
    server: AstreinLanguageServer,
    workspace_folders: list[lsp.WorkspaceFolder] | None = None,
    root_uri: str | None = None,
) -> None:
    """Simulate LSP client initialization by directly invoking the protocol."""
    params = lsp.InitializeParams(
        capabilities=lsp.ClientCapabilities(),
        process_id=os.getpid(),
        root_uri=root_uri,
        workspace_folders=workspace_folders,
    )
    # Consume the generator returned by lsp_initialize to execute it
    list(server.protocol.lsp_initialize(params))
    # Dispatch the initialized notification to trigger our registered handler
    server.protocol._handle_notification(lsp.INITIALIZED, lsp.InitializedParams())  # noqa: SLF001


def test_checker_error_to_diagnostic_basic() -> None:
    error = CheckerError(
        message="Test error message",
        line=10,
        column=5,
        file_path=Path("test.py"),
        checker_id="test-checker",
    )

    diagnostic = _checker_error_to_diagnostic(error)

    assert diagnostic.range.start.line == 9  # LSP is 0-indexed
    assert diagnostic.range.start.character == 5
    assert diagnostic.range.end.line == 9
    assert diagnostic.range.end.character == 6
    assert diagnostic.severity == lsp.DiagnosticSeverity.Error
    assert diagnostic.source == "astrein"
    assert diagnostic.code == "test-checker"
    assert diagnostic.message == "Test error message"


def test_checker_error_to_diagnostic_line_zero() -> None:
    error = CheckerError(
        message="Line zero error",
        line=0,
        column=0,
        file_path=Path("test.py"),
        checker_id="test-checker",
    )

    diagnostic = _checker_error_to_diagnostic(error)

    # Line should be clamped to 0 (not -1)
    assert diagnostic.range.start.line == 0
    assert diagnostic.range.start.character == 0


def test_checker_error_to_diagnostic_line_one() -> None:
    error = CheckerError(
        message="Line one error",
        line=1,
        column=0,
        file_path=Path("test.py"),
        checker_id="test-checker",
    )

    diagnostic = _checker_error_to_diagnostic(error)

    assert diagnostic.range.start.line == 0  # LSP line 0 = human line 1


def test_create_server_returns_language_server() -> None:
    server = create_server(repo_root_override=None)

    assert isinstance(server, AstreinLanguageServer)
    assert server.repo_root is None


def test_create_server_with_repo_root() -> None:
    repo_root = Path("/some/repo")
    server = create_server(repo_root_override=repo_root)

    assert server.repo_root == repo_root


def test_astrein_language_server_initialization() -> None:
    server = AstreinLanguageServer(repo_root_override=None)

    assert server.name == "astrein"
    assert server.version == "1.0.0"
    assert server.repo_root is None


def test_astrein_language_server_with_repo_root() -> None:
    server = AstreinLanguageServer(repo_root_override := Path("/test/repo"))
    assert server.repo_root == repo_root_override


def test_get_diagnostics_skips_non_python_files(tmp_path: Path) -> None:
    txt_file = tmp_path / "test.txt"
    txt_file.write_text("not python")
    uri = f"file://{txt_file}"

    result = get_diagnostics(uri, repo_root=tmp_path)
    assert result is None


def test_get_diagnostics_skips_when_no_repo_root() -> None:
    result = get_diagnostics("file:///some/path/test.py", repo_root=None)
    assert result is None


def test_get_diagnostics_returns_none_for_nonexistent_file(tmp_path: Path) -> None:
    result = get_diagnostics(f"file://{tmp_path}/nonexistent.py", repo_root=tmp_path)
    assert result is None


def test_get_diagnostics_with_clean_file(tmp_path: Path) -> None:
    test_file = tmp_path / "test.py"
    test_file.write_text("import sys\n")

    result = get_diagnostics(f"file://{test_file}", repo_root=tmp_path)

    assert result is not None
    assert len(result) == 0


def test_get_diagnostics_with_source_content(tmp_path: Path) -> None:
    result = get_diagnostics(
        f"file://{tmp_path}/test.py", repo_root=tmp_path, source="import sys\n"
    )

    assert result is not None
    assert len(result) == 0


@pytest.mark.parametrize(
    "line,expected_lsp_line",
    [
        (1, 0),  # Line 1 -> LSP line 0
        (10, 9),  # Line 10 -> LSP line 9
        (100, 99),  # Line 100 -> LSP line 99
        (0, 0),  # Line 0 -> clamped to LSP line 0
    ],
)
def test_checker_error_to_diagnostic_line_mapping(line: int, expected_lsp_line: int) -> None:
    error = CheckerError(
        message="Test",
        line=line,
        column=0,
        file_path=Path("test.py"),
        checker_id="test",
    )

    diagnostic = _checker_error_to_diagnostic(error)

    assert diagnostic.range.start.line == expected_lsp_line


def test_server_uses_workspace_folders_from_client() -> None:
    server = create_server(repo_root_override=None)
    _simulate_client_initialize(
        server,
        workspace_folders=[lsp.WorkspaceFolder(uri="file:///home/user/project", name="project")],
    )

    assert server.repo_root == Path("/home/user/project")


def test_server_uses_root_uri_from_client() -> None:
    server = create_server(repo_root_override=None)
    _simulate_client_initialize(
        server,
        root_uri="file:///home/user/repo",
        workspace_folders=[],
    )

    assert server.repo_root == Path("/home/user/repo")


def test_server_prefers_workspace_folders_over_root_uri() -> None:
    server = create_server(repo_root_override=None)
    _simulate_client_initialize(
        server,
        root_uri="file:///home/user/root-uri-path",
        workspace_folders=[
            lsp.WorkspaceFolder(uri="file:///home/user/folders-path", name="project")
        ],
    )

    assert server.repo_root == Path("/home/user/folders-path")


def test_server_repo_root_none_when_client_sends_nothing() -> None:
    server = create_server(repo_root_override=None)
    _simulate_client_initialize(
        server,
        root_uri=None,
        workspace_folders=[],
    )

    assert server.repo_root is None


def test_server_cli_override_takes_precedence() -> None:
    cli_path = Path("/cli/override/path")
    server = create_server(repo_root_override=cli_path)
    _simulate_client_initialize(
        server,
        workspace_folders=[lsp.WorkspaceFolder(uri="file:///client/workspace", name="workspace")],
    )

    assert server.repo_root == cli_path
