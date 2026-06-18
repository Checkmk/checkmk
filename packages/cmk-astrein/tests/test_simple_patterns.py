#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import ast
from pathlib import Path

from cmk.astrein.checker_simple_patterns import (
    ABCMetaMetaclassChecker,
    HTMLDebugChecker,
    PillowImportChecker,
    PydanticTypeAdapterChecker,
    TarfileOpenReadChecker,
)
from cmk.astrein.framework import CheckerError


def _check_abcmeta(code: str) -> list[CheckerError]:
    checker = ABCMetaMetaclassChecker(Path("test/test.py"), Path("test"), code)
    return checker.check(ast.parse(code))


def test_abcmeta_rejects_metaclass_abcmeta() -> None:
    errors = _check_abcmeta("class Foo(metaclass=ABCMeta): pass")
    assert len(errors) == 1
    assert "ABC" in errors[0].message


def test_abcmeta_rejects_metaclass_abc_dot_abcmeta() -> None:
    errors = _check_abcmeta("class Foo(metaclass=abc.ABCMeta): pass")
    assert len(errors) == 1
    assert "ABC" in errors[0].message


def test_abcmeta_allows_inheriting_abc() -> None:
    assert _check_abcmeta("class Foo(ABC): pass") == []


def test_abcmeta_allows_inheriting_other_base() -> None:
    assert _check_abcmeta("class Foo(Bar): pass") == []


def test_abcmeta_allows_other_metaclass() -> None:
    assert _check_abcmeta("class Foo(metaclass=SomethingElse): pass") == []


def _check_html_debug(code: str) -> list[CheckerError]:
    checker = HTMLDebugChecker(Path("test/test.py"), Path("test"), code)
    return checker.check(ast.parse(code))


def test_html_debug_rejects_call_with_args() -> None:
    errors = _check_html_debug("html.debug(x)")
    assert len(errors) == 1
    assert "html.debug" in errors[0].message


def test_html_debug_rejects_call_without_args() -> None:
    errors = _check_html_debug("html.debug()")
    assert len(errors) == 1
    assert "html.debug" in errors[0].message


def test_html_debug_allows_other_html_methods() -> None:
    assert _check_html_debug("html.render()") == []


def test_html_debug_allows_debug_on_other_objects() -> None:
    assert _check_html_debug("foo.debug()") == []


def test_html_debug_allows_bare_debug_call() -> None:
    assert _check_html_debug("debug()") == []


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


# --- PydanticTypeAdapterChecker tests ---


def _check_type_adapter(code: str) -> list[CheckerError]:
    checker = PydanticTypeAdapterChecker(Path("test/test.py"), Path("test"), code)
    return checker.check(ast.parse(code))


def test_type_adapter_rejects_in_function() -> None:
    code = "def f():\n    TypeAdapter(X)"
    errors = _check_type_adapter(code)
    assert len(errors) == 1
    assert "TypeAdapter" in errors[0].message


def test_type_adapter_rejects_subscript_in_function() -> None:
    code = "def f():\n    TypeAdapter[T](X)"
    errors = _check_type_adapter(code)
    assert len(errors) == 1
    assert "TypeAdapter" in errors[0].message


def test_type_adapter_allows_module_level() -> None:
    assert _check_type_adapter("TypeAdapter(X)") == []


def test_type_adapter_allows_other_call_in_function() -> None:
    assert _check_type_adapter("def f():\n    SomeOther(X)") == []


def test_type_adapter_rejects_in_async_function() -> None:
    code = "async def f():\n    TypeAdapter(X)"
    errors = _check_type_adapter(code)
    assert len(errors) == 1


def test_type_adapter_rejects_in_nested_function() -> None:
    code = "def f():\n    def g():\n        TypeAdapter(X)"
    errors = _check_type_adapter(code)
    assert len(errors) == 1


def test_type_adapter_rejects_in_method() -> None:
    code = "class C:\n    def m(self):\n        TypeAdapter(X)"
    errors = _check_type_adapter(code)
    assert len(errors) == 1


# --- TarfileOpenReadChecker tests ---


def _check_tarfile(
    code: str,
    file_path: Path = Path("/repo/cmk/some_module.py"),
    repo_root: Path = Path("/repo"),
) -> list[CheckerError]:
    checker = TarfileOpenReadChecker(file_path, repo_root, code)
    return checker.check(ast.parse(code))


def test_tarfile_rejects_open_no_mode() -> None:
    errors = _check_tarfile('tarfile.open("f")')
    assert len(errors) == 1
    assert "tarfile.open()" in errors[0].message


def test_tarfile_rejects_open_read_mode_keyword() -> None:
    errors = _check_tarfile('tarfile.open("f", mode="r:gz")')
    assert len(errors) == 1


def test_tarfile_rejects_open_read_mode_positional() -> None:
    errors = _check_tarfile('tarfile.open("f", "r:bz2")')
    assert len(errors) == 1


def test_tarfile_rejects_tarfile_class() -> None:
    errors = _check_tarfile('TarFile.open("f")')
    assert len(errors) == 1


def test_tarfile_rejects_tf_suffix() -> None:
    errors = _check_tarfile('mytf.open("f")')
    assert len(errors) == 1


def test_tarfile_allows_write_mode() -> None:
    assert _check_tarfile('tarfile.open("f", mode="w")') == []


def test_tarfile_allows_write_mode_positional() -> None:
    assert _check_tarfile('tarfile.open("f", "w:gz")') == []


def test_tarfile_allows_other_object() -> None:
    assert _check_tarfile('foo.open("f")') == []


def test_tarfile_allows_excluded_tests_path() -> None:
    assert (
        _check_tarfile(
            'tarfile.open("f")',
            file_path=Path("/repo/tests/unit/test_foo.py"),
        )
        == []
    )


def test_tarfile_allows_excluded_package_tests_path() -> None:
    assert (
        _check_tarfile(
            'tarfile.open("f")',
            file_path=Path("/repo/packages/cmk-foo/tests/test_bar.py"),
        )
        == []
    )


def test_tarfile_allows_excluded_mkp_tool_path() -> None:
    assert (
        _check_tarfile(
            'tarfile.open("f")',
            file_path=Path("/repo/mkp_tool/something.py"),
        )
        == []
    )


def test_tarfile_allows_excluded_nested_mkp_tool_path() -> None:
    assert (
        _check_tarfile(
            'tarfile.open("f")',
            file_path=Path("/repo/packages/cmk-mkp-tool/cmk/mkp_tool/_mkp.py"),
        )
        == []
    )


def test_tarfile_allows_excluded_nested_testlib_path() -> None:
    assert (
        _check_tarfile(
            'tarfile.open("f")',
            file_path=Path("/repo/packages/cmk-agent-receiver/cmk/testlib/config.py"),
        )
        == []
    )
