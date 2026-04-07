#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
# NOTE:
# This check runs as a Bazel aspect, so it only covers files declared in
# Bazel target srcs. Files not in any Bazel target (e.g. doc/treasures/, ad-hoc
# scripts) are not checked.
#
# This is acceptable because all production-deployed files go through Bazel
# (see //omd:BUILD deps_packages). Additionally, the "Bazel sanity check"
# (scripts/in_bazel.sh) ensures that all .py files are in py_* Bazel targets.
#
# So the only gap is extensionless Python files outside the build graph.
#
# If repo-wide coverage is ever needed, a complementary filesystem-level check
# would be required.
import ast
import json
import re
import sys
import warnings
from pathlib import Path


def is_text_file(file_path: Path, blocksize: int = 512) -> bool:
    try:
        with file_path.open("rb") as f:
            block = f.read(blocksize)
        block.decode("utf-8")
        return True
    except UnicodeDecodeError:
        return False


def is_executable_wrapper(content: str) -> bool:
    """
    Detect if a Python file is a simple executable wrapper.

    These are typically short files (< 25 lines) that:
    1. Start with shebang #!/usr/bin/env python3
    2. Have a copyright header
    3. Import a main function from another module
    4. Call that main function in if __name__ == "__main__" block
    """
    lines = content.splitlines()

    # Must be reasonably short
    if len(lines) > 25:
        return False

    # Must start with python3 shebang
    if not lines or not lines[0].startswith("#!/usr/bin/env python3"):
        return False

    # Must have copyright header (look for "Copyright" in first few lines)
    has_copyright = any("Copyright" in line for line in lines[:6])
    if not has_copyright:
        return False

    # Must have import statement with "cmk" in it
    has_main_import = any("import" in line and "cmk" in line for line in lines)
    if not has_main_import:
        return False

    # Must have if __name__ == "__main__": block
    has_main_block = any('if __name__ == "__main__"' in line for line in lines)
    if not has_main_block:
        return False

    # Must call main() function in the main block
    has_main_call = any("main(" in line for line in lines)
    if not has_main_call:
        return False

    return True


def is_python_source(content: str) -> bool:
    if re.match(r"^\s*#!.*python3", content):
        # starting with a shebang for Python 3
        # (that's a good starting point - these are definitely Python files)
        return True

    if not content.strip():
        # empty file -> no Python source
        return False

    try:
        # Try to parse the content as Python source code.
        # If it raises a SyntaxError, it's not valid Python code.
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            ast.parse(content)

        # "valid in python" still might lead to a lot of false positives
        # (like a text file with "hello" in it)
        if re.search("import |def |class |print", content):
            # if it contains import, def, or class, it's likely Python code
            return True

        return False
    except SyntaxError:
        pass

    return False


# toggle for ignoring executable wrapper files (short Python files that just import and call main)
IGNORE_EXECUTABLE_WRAPPERS = False

# paths that are known to have python code without .py extension and should be ignored
KNOWN_VIOLATIONS = [
    r"non-free/packages/cmk-mknotifyd/mknotifyd$",
    r"non-free/packages/otel-collector/bin/cmk-cleanup-otel-collector-files$",
    r"cmk/plugins/checkmk/libexec/check_notify_count$",
    r"non-free/packages/cmk-core-helpers/fetcher$",
    r"bin/.*",
    r"packages/.*/notifications/.*",
    r"non-free/packages/.*/notifications/.*",
]

PYTHON_SUFFIXES = [
    # python extension
    ".py",
    ".pyi",
    ".wsgi",
    ".typed",
]

IGNORE_SUFFIXES = [
    # non-python stuff
    ".bazel",
    ".bzl",
    ".cab",
    ".cap",
    ".cfg",
    ".cfg-sample",
    ".conf",
    ".dat",
    ".dict",
    ".html",
    ".imp",
    ".in",
    ".json",
    ".lock",
    ".map",
    ".marker",
    ".md",
    ".mk",
    ".output",
    ".php",
    ".ps1",
    ".state",
    ".toml",
    ".txt",
    ".yaml",
    ".yml",
]


def has_python_extension_violation(file_path: Path) -> bool:
    # -------------------------------------------------------------
    # Phase 1: sort out as many files by path/extension
    # -------------------------------------------------------------
    # Skip files that already have a .py extension or other non-python extensions
    if file_path.suffix in PYTHON_SUFFIXES or file_path.suffix in IGNORE_SUFFIXES:
        return False

    if any(re.match(pattern, str(file_path)) for pattern in KNOWN_VIOLATIONS):
        return False

    # -------------------------------------------------------------
    # Phase 2: simple file content evaluation
    # -------------------------------------------------------------
    # Only consider text files.
    if not is_text_file(file_path):
        return False

    try:
        content = file_path.read_text(encoding="utf-8")
    except Exception:
        return False

    # -------------------------------------------------------------
    # Phase 3: evaluate complete content (parse python)
    # -------------------------------------------------------------
    # as this is more resource intensive, this should be at the end
    if is_python_source(content):
        # Check if it's an executable wrapper and should be ignored
        if IGNORE_EXECUTABLE_WRAPPERS and is_executable_wrapper(content):
            return False
        # Violation found: it's a python source file without a .py extension
        return True

    return False


def write_sarif_output(machine_path: str, violations: list[str]) -> None:
    results = [
        {
            "ruleId": "python-extension",
            "level": "error",
            "message": {"text": "A python source file doesn't have a .py extension"},
            "locations": [
                {
                    "physicalLocation": {
                        "artifactLocation": {
                            "uri": src_path,
                        }
                    }
                }
            ],
        }
        for src_path in violations
    ]
    sarif = {
        "$schema": "https://raw.githubusercontent.com/oasis-tcs/sarif-spec/master/Schemata/sarif-schema-2.1.0.json",
        "version": "2.1.0",
        "runs": [
            {
                "tool": {
                    "driver": {
                        "name": "PythonExtensionCheck",
                        "rules": [
                            {
                                "id": "python-extension",
                                "shortDescription": {
                                    "text": "See https://wiki.lan.checkmk.net/x/jStSCQ"
                                },
                            }
                        ],
                    }
                },
                "results": results,
            }
        ],
    }
    with open(machine_path, "w") as f:
        json.dump(sarif, f, indent=2)


def write_human_output(human_path: str, violations: list[str]) -> None:
    if violations:
        human_content = "PYTHON EXTENSION VIOLATIONS:\n" + "\n".join(violations) + "\n"
    else:
        human_content = "No python extension violations found."
    with open(human_path, "w") as f:
        f.write(human_content)


def main() -> int:
    if len(sys.argv) < 6:
        print(
            f"Usage: {sys.argv[0]} <human_out_path> <machine_out_path> <human_exit_code_path> "
            f"<machine_exit_code_path> <source_file>...",
            file=sys.stderr,
        )
        return 2

    human_out_path, machine_out_path, human_exit_code_path, machine_exit_code_path, *src_paths = (
        sys.argv[1:]
    )

    violations = []
    for src_path in src_paths:
        if has_python_extension_violation(Path(src_path)):
            violations.append(src_path)

    write_sarif_output(machine_out_path, violations)
    write_human_output(human_out_path, violations)

    exit_code = 1 if violations else 0

    if human_exit_code_path:
        with open(human_exit_code_path, "w") as f:
            f.write(str(exit_code))
    if machine_exit_code_path:
        with open(machine_exit_code_path, "w") as f:
            f.write(str(exit_code))

    fail_on_violation = not (human_exit_code_path or machine_exit_code_path)
    if fail_on_violation and violations:
        with open(human_out_path) as f:
            print(f.read(), file=sys.stderr)

    return 0 if not fail_on_violation else exit_code


if __name__ == "__main__":
    sys.exit(main())
