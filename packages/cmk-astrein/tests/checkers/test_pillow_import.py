#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import ast
from pathlib import Path

from cmk.astrein.checkers.pillow_import import PillowImportChecker
from cmk.astrein.framework import CheckerError


def _check_pillow(
    code: str, file_path: Path = Path("test/test.py"), repo_root: Path = Path("test")
) -> list[CheckerError]:
    checker = PillowImportChecker(file_path, repo_root, code)
    return checker.check(ast.parse(code))


def test_pillow_rejects_from_pil_import() -> None:
    errors = _check_pillow("from PIL import Image")
    assert len(errors) == 1
    assert "PIL" in errors[0].message


def test_pillow_rejects_import_pil() -> None:
    errors = _check_pillow("import PIL")
    assert len(errors) == 1
    assert "PIL" in errors[0].message


def test_pillow_rejects_import_pil_submodule() -> None:
    errors = _check_pillow("import PIL.Image")
    assert len(errors) == 1
    assert "PIL" in errors[0].message


def test_pillow_rejects_from_pil_submodule_import() -> None:
    errors = _check_pillow("from PIL.Image import open")
    assert len(errors) == 1
    assert "PIL" in errors[0].message


def test_pillow_allows_pillow_package() -> None:
    assert _check_pillow("from pillow import something") == []


def test_pillow_allows_unrelated_imports() -> None:
    assert _check_pillow("import os") == []


def test_pillow_allows_pil_in_images_wrapper() -> None:
    repo_root = Path("/repo")
    file_path = repo_root / "cmk" / "gui" / "utils" / "images.py"
    assert _check_pillow("from PIL import Image", file_path=file_path, repo_root=repo_root) == []
