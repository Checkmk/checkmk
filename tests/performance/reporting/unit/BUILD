load("@aspect_rules_py//py:defs.bzl", "py_library")
load("//bazel/rules:py_cmk_test.bzl", "py_cmk_test")

# Owns __init__.py so the source-presence check finds it without putting it in
# the py_test's srcs (which would mis-anchor pytest's package discovery).
py_library(
    name = "pkg",
    testonly = True,
    srcs = ["__init__.py"],
)

py_cmk_test(
    name = "unit",
    size = "small",
    srcs = ["test_performance_baselines.py"],
    imports = ["../../../.."],
    use_project_pytest_config = True,
    deps = ["//tests/performance:reporting"],
)
