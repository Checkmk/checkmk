load("@cmk_requirements//:requirements.bzl", "requirement")
load("@rules_python//python:defs.bzl", "py_library")

py_library(
    name = "wnx-agent-integration-python-tests",
    srcs = [
        "__init__.py",
        "conftest.py",
        "test_check_mk_cmd_line.py",
        "test_check_mk_run.py",
        "test_python_module.py",
        "utils.py",
    ],
    visibility = ["//visibility:public"],
    deps = [
        requirement("pytest"),
        requirement("telnetlib3"),
        requirement("pyyaml"),
    ],
)
