#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""LSP (Language Server Protocol) server for astrein."""

from __future__ import annotations

import argparse
import logging
import signal
import sys
import tempfile
from pathlib import Path

from lsprotocol import types as lsp
from pygls.lsp.server import LanguageServer

from cmk.astrein.checkers import all_checkers
from cmk.astrein.framework import CheckerError, run_checkers

logger = logging.getLogger(__name__)


def main() -> int:
    parser = argparse.ArgumentParser(description="Astrein LSP server")
    parser.add_argument(
        "--repo-root",
        type=Path,
        help="Repository root path (overrides workspace root from client)",
    )
    parser.add_argument(
        "--log-file",
        type=Path,
        help="Log file path for debugging",
    )
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Log level (default: INFO)",
    )

    args = parser.parse_args()

    log_handlers: list[logging.Handler] = []
    if args.log_file:
        log_handlers.append(logging.FileHandler(args.log_file))
    else:
        log_handlers.append(logging.StreamHandler(sys.stderr))

    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=log_handlers,
    )

    repo_root_override = None
    if args.repo_root is not None:
        repo_root_override = args.repo_root.resolve()
        logger.info("Using repo root override from CLI: %s", repo_root_override)

    server = create_server(repo_root_override)

    def shutdown_handler(signum: int, _frame: object) -> None:
        logger.info("Received signal %s, shutting down", signum)
        raise SystemExit(0)

    signal.signal(signal.SIGINT, shutdown_handler)
    signal.signal(signal.SIGTERM, shutdown_handler)

    logger.info("Starting astrein LSP server")
    server.start_io()

    return 0


def create_server(repo_root_override: Path | None) -> AstreinLanguageServer:
    server = AstreinLanguageServer(repo_root_override)

    @server.feature(lsp.INITIALIZED)
    def initialized(_params: lsp.InitializedParams) -> None:
        if server.repo_root is None:
            workspace_root = _get_workspace_root(server)
            if workspace_root is not None:
                server.repo_root = workspace_root
                logger.info("Using workspace root from client: %s", server.repo_root)
            else:
                logger.warning("No workspace root available, module-layers checker may not work")

    @server.feature(lsp.TEXT_DOCUMENT_DID_OPEN)
    def did_open(params: lsp.DidOpenTextDocumentParams) -> None:
        logger.info("Document opened: %s", params.text_document.uri)
        _validate_document(server, params.text_document.uri)

    @server.feature(lsp.TEXT_DOCUMENT_DID_SAVE)
    def did_save(params: lsp.DidSaveTextDocumentParams) -> None:
        logger.info("Document saved: %s", params.text_document.uri)
        _validate_document(server, params.text_document.uri)

    @server.feature(lsp.TEXT_DOCUMENT_DID_CLOSE)
    def did_close(params: lsp.DidCloseTextDocumentParams) -> None:
        logger.info("Document closed: %s", params.text_document.uri)
        server.text_document_publish_diagnostics(
            lsp.PublishDiagnosticsParams(uri=params.text_document.uri, diagnostics=[])
        )

    @server.feature(lsp.TEXT_DOCUMENT_DID_CHANGE)
    def did_change(params: lsp.DidChangeTextDocumentParams) -> None:
        logger.debug("Document changed: %s", params.text_document.uri)
        # Get the full content from the last change (assuming full sync)
        if params.content_changes:
            source = params.content_changes[-1].text
            _validate_document(server, params.text_document.uri, source=source)

    return server


def _get_workspace_root(server: AstreinLanguageServer) -> Path | None:
    """Extract workspace root from LSP client initialization."""
    if server.workspace.folders:
        first_folder = next(iter(server.workspace.folders.values()))
        return Path(first_folder.uri.replace("file://", ""))

    if server.workspace.root_uri:
        return Path(server.workspace.root_uri.replace("file://", ""))

    return None


class AstreinLanguageServer(LanguageServer):
    def __init__(self, repo_root_override: Path | None) -> None:
        super().__init__(name="astrein", version="1.0.0")
        self.repo_root: Path | None = repo_root_override


def _validate_document(ls: AstreinLanguageServer, uri: str, *, source: str | None = None) -> None:
    diagnostics = get_diagnostics(uri, ls.repo_root, source=source)
    if diagnostics is None:
        return

    ls.text_document_publish_diagnostics(
        lsp.PublishDiagnosticsParams(uri=uri, diagnostics=diagnostics)
    )
    logger.info("Published %d diagnostic(s) for %s", len(diagnostics), uri)


def get_diagnostics(
    uri: str, repo_root: Path | None, *, source: str | None = None
) -> list[lsp.Diagnostic] | None:
    """Get diagnostics for a document. Returns None if validation should be skipped."""
    file_path = Path(uri.replace("file://", ""))

    if file_path.suffix != ".py":
        return None

    if repo_root is None:
        logger.warning("repo_root not set, skipping validation")
        return None

    checkers = list(all_checkers().values())
    errors = []
    try:
        if source is not None:
            with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=True) as tmp:
                tmp.write(source)
                tmp.flush()
                errors.extend(run_checkers(Path(tmp.name), repo_root, checkers))
        else:
            if not file_path.exists():
                logger.warning("File does not exist: %s", file_path)
                return None

            errors.extend(run_checkers(file_path, repo_root, checkers))

        return [_checker_error_to_diagnostic(e) for e in errors]

    except Exception as e:
        logger.exception("Error validating document %s: %s", uri, e)
        return []


def _checker_error_to_diagnostic(error: CheckerError) -> lsp.Diagnostic:
    return lsp.Diagnostic(
        range=lsp.Range(
            start=lsp.Position(line=max(0, error.line - 1), character=error.column),
            end=lsp.Position(line=max(0, error.line - 1), character=error.column + 1),
        ),
        severity=lsp.DiagnosticSeverity.Error,
        source="astrein",
        code=error.checker_id,
        message=error.message,
    )


if __name__ == "__main__":
    sys.exit(main())
