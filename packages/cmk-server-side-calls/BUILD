load("@aspect_rules_py//py:defs.bzl", "py_library", "py_pytest_main", "py_test")
load("@cmk_requirements//:requirements.bzl", "requirement")
load("@rules_python//python:packaging.bzl", "py_wheel")
load("//bazel/rules:doctest.bzl", "py_doc_test")
load("//bazel/rules:package_wheel.bzl", "package_wheel")

exports_files([
    "pyproject.toml",
    "requirements.in",
])

py_library(
    name = "cmk-server-side-calls",
    srcs = [
        "cmk/server_side_calls/__init__.py",
        "cmk/server_side_calls/v1/__init__.py",
        "cmk/server_side_calls/v1/_active_checks.py",
        "cmk/server_side_calls/v1/_special_agents.py",
        "cmk/server_side_calls/v1/_utils.py",
    ],
    imports = ["."],
    visibility = ["//cmk:__pkg__"],
)

py_doc_test(
    name = "doctest",
    size = "small",
    srcs = ["cmk-server-side-calls"],
    tags = ["no-mypy"],
    # TODO: There should be *no* imports in doctests!
    deps = [requirement("pydantic")],
)

py_pytest_main(
    name = "__test__",
    deps = [
        requirement("pytest"),
    ],
)

py_test(
    name = "unit",
    size = "small",
    srcs = glob(["tests/**/*.py"]) + [":__test__.py"],
    main = "__test__.py",
    deps = [
        ":__test__",
        ":cmk-server-side-calls",
        requirement("pydantic"),
        requirement("pytest"),
    ],
)

py_wheel(
    name = "wheel",
    distribution = "cmk-server-side-calls",
    strip_path_prefixes = ["packages/cmk-server-side-calls"],
    # TODO: Duplicated from pyproject.toml
    version = "1.0.0",
    deps = [":cmk-server-side-calls"],
)

package_wheel(
    name = "pkg_tar",
    visibility = ["//visibility:public"],
    whl = "wheel",
)
