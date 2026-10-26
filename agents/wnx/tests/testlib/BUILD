load("@aspect_rules_py//py:defs.bzl", "py_test")
load("@cmk_requirements//:requirements.bzl", "requirement")
load("@rules_python//python:defs.bzl", "py_library")

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
    srcs = [":srcs"],
    imports = [".."],
    visibility = ["//visibility:public"],
    deps = [
        requirement("pytest"),
    ],
)

py_test(
    name = "test_agent_output",
    size = "small",
    srcs = ["test_agent_output.py"],
    args = [
        "--import-mode=importlib",
        "--ignore-glob=*pytest_main.py",
    ],
    pytest_main = True,
    deps = [
        ":wnx-agent-python-testlib",
        requirement("pytest"),
    ],
)
