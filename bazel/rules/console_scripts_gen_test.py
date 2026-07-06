#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Tests for the console-script wrapper generator."""

import os
import tempfile
import unittest
import zipfile
from pathlib import Path

from console_scripts_gen import instantiate_wrapper, main, parse_console_scripts


class TestParseConsoleScripts(unittest.TestCase):
    def test_plain_entry(self) -> None:
        content = "[console_scripts]\ncmk-broker-test = cmk.messaging.broker_test:main\n"
        self.assertEqual(
            list(parse_console_scripts(content)),
            [("cmk-broker-test", "cmk.messaging.broker_test:main")],
        )

    def test_names_kept_case_sensitive(self) -> None:
        content = "[console_scripts]\nMixedCase = module:attr\n"
        self.assertEqual(list(parse_console_scripts(content)), [("MixedCase", "module:attr")])

    def test_missing_section(self) -> None:
        self.assertEqual(list(parse_console_scripts("")), [])
        self.assertEqual(list(parse_console_scripts("[gui_scripts]\nfoo = bar:baz\n")), [])

    def test_other_groups_ignored(self) -> None:
        content = (
            "[console_scripts]\nfoo = module:attr\n[some.plugin.group]\nplug = other.module:thing\n"
        )
        self.assertEqual(list(parse_console_scripts(content)), [("foo", "module:attr")])

    def test_percent_in_other_group_is_not_interpolated(self) -> None:
        content = (
            "[console_scripts]\nfoo = module:attr\n[templates]\ngreeting = hello %s of %(place)s\n"
        )
        self.assertEqual(list(parse_console_scripts(content)), [("foo", "module:attr")])


class TestInstantiateWrapper(unittest.TestCase):
    def test_plain_target(self) -> None:
        body = instantiate_wrapper("cmk.messaging.broker_test:main")
        self.assertIn("from cmk.messaging.broker_test import main", body)
        self.assertIn("sys.exit(main())", body)

    def test_dotted_attr_imports_top_level_and_calls_full_path(self) -> None:
        body = instantiate_wrapper("module.sub:obj.method")
        self.assertIn("from module.sub import obj", body)
        self.assertIn("sys.exit(obj.method())", body)

    def test_extras_are_stripped(self) -> None:
        body = instantiate_wrapper("module:main [extra1,extra2]")
        self.assertIn("from module import main", body)
        self.assertIn("sys.exit(main())", body)

    def test_malformed_target_raises(self) -> None:
        for target in ("no_colon", "module:", ":attr"):
            with self.assertRaises(ValueError):
                instantiate_wrapper(target)


def _make_wheel(directory: Path, entry_points: str | None) -> Path:
    wheel = directory / "dummy-1.0-py3-none-any.whl"
    with zipfile.ZipFile(wheel, "w") as zf:
        zf.writestr("dummy/__init__.py", "")
        if entry_points is not None:
            zf.writestr("dummy-1.0.dist-info/entry_points.txt", entry_points)
    return wheel


class TestMain(unittest.TestCase):
    def test_emits_executable_wrappers(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            wheel = _make_wheel(Path(tmp), "[console_scripts]\ndummy-tool = dummy.cli:main\n")
            out = Path(tmp) / "bin"
            self.assertEqual(main(["--wheel", str(wheel), "--out", str(out)]), 0)
            wrapper = out / "dummy-tool"
            self.assertTrue(os.access(wrapper, os.X_OK))
            self.assertIn("from dummy.cli import main", wrapper.read_text())

    def test_wheel_without_entry_points_is_noop(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            wheel = _make_wheel(Path(tmp), None)
            out = Path(tmp) / "bin"
            self.assertEqual(main(["--wheel", str(wheel), "--out", str(out)]), 0)
            # The declared output directory is created, just empty.
            self.assertTrue(out.is_dir())
            self.assertEqual(list(out.iterdir()), [])

    def test_wheel_without_console_scripts_group_is_noop(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            wheel = _make_wheel(Path(tmp), "[gui_scripts]\ngui = dummy.gui:main\n")
            out = Path(tmp) / "bin"
            self.assertEqual(main(["--wheel", str(wheel), "--out", str(out)]), 0)
            self.assertTrue(out.is_dir())
            self.assertEqual(list(out.iterdir()), [])


if __name__ == "__main__":
    unittest.main()
