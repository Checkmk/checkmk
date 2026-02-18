load("@cmk_requirements//:requirements.bzl", "requirement")
load("@rules_python//python:defs.bzl", "py_library")

py_library(
    name = "wnx-agent-ap-python-tests",
    srcs = [
        "conftest.py",
        "test_mk_logwatch_win.py",
    ],
    #imports = ["../testlib"],
    visibility = ["//visibility:public"],
    deps = [
        requirement("pytest"),
        "//agents/wnx/tests/testlib:wnx-agent-python-testlib",
    ],
)
