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
    use_project_pytest_config = True,
    deps = [
        requirement("psycopg"),
        "//tests/qa_metrics/db",
        "//tests/unit/qa_metrics",
    ],
)
