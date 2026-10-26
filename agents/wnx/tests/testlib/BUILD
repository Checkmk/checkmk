load("@cmk_requirements//:requirements.bzl", "requirement")
load("@rules_python//python:defs.bzl", "py_library")
load("//bazel/rules:py_cmk_test.bzl", "py_cmk_test")

filegroup(
    name = "srcs",
    srcs = [
        "__init__.py",
        "agent_output.py",
        "utils.py",
    ],
    visibility = ["//agents/wnx/tests:__subpackages__"],
)

py_library(
    name = "wnx-agent-python-testlib",
    testonly = True,
    srcs = [":srcs"],
    imports = [".."],
    visibility = ["//visibility:public"],
    deps = [
        requirement("pytest"),
    ],
)

py_cmk_test(
    name = "test_agent_output",
    size = "small",
    srcs = ["test_agent_output.py"],
    deps = [":wnx-agent-python-testlib"],
)
