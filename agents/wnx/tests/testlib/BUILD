load("@cmk_requirements//:requirements.bzl", "requirement")
load("@rules_python//python:defs.bzl", "py_library")

py_library(
    name = "wnx-agent-python-testlib",
    srcs = [
        "__init__.py",
        "utils.py",
    ],
    visibility = ["//visibility:public"],
    deps = [
        requirement("pytest"),
    ],
)
