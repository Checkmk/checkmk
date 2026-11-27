# Modified by Checkmk GmbH, see bazel/tools/rules_mypy/VENDORED.md
"Public API for py_type_library."

load("//bazel/tools/rules_mypy/mypy/private:py_type_library.bzl", _py_type_library = "py_type_library")

py_type_library = _py_type_library
