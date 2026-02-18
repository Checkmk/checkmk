load("@cmk_requirements//:requirements.bzl", "requirement")
load("@rules_python//python:defs.bzl", "py_library")

py_library(
    name = "windows-module-integration-python-tests",
    srcs = [
        "__init__.py",
        "conftest.py",
        "test_scripts_execution.py",
    ],
    visibility = ["//visibility:public"],
    deps = [
        requirement("pytest"),
    ],
)
