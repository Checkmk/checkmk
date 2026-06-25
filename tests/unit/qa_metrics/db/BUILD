load("@aspect_rules_py//py:defs.bzl", "py_library")
load("@cmk_requirements//:requirements.bzl", "requirement")
load("//bazel/rules:py_cmk_test.bzl", "py_cmk_test")

# Owns __init__.py so the source-presence check finds it without putting it in
# the py_test's srcs (which would mis-anchor pytest's package discovery).
py_library(
    name = "pkg",
    testonly = True,
    srcs = ["__init__.py"],
)

py_cmk_test(
    name = "db",
    size = "small",
    srcs = [
        "test_helpers.py",
        "test_table.py",
    ],
    imports = ["../../../.."],
    pytest_main = True,
    use_project_pytest_config = True,
    deps = [
        # marshmallow is referenced by the workspace pyproject.toml's
        # filterwarnings list; pytest needs it importable to parse config.
        requirement("marshmallow"),
        requirement("psycopg"),
        requirement("pytest"),
        "//tests/qa_metrics/db",
        "//tests/unit/qa_metrics",
    ],
)
