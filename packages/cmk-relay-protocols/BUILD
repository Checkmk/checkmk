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
    name = "cmk-relay-protocols",
    srcs = [
        "cmk/relay_protocols/__init__.py",
        "cmk/relay_protocols/monitoring_data.py",
    ],
    imports = ["."],
    visibility = ["//:__subpackages__"],
    deps = [
        requirement("pydantic"),
    ],
)

py_doc_test(
    name = "doctest",
    size = "small",
    srcs = ["cmk-relay-protocols"],
    tags = ["no-mypy"],
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
        ":cmk-relay-protocols",
        requirement("pytest"),
    ],
)

py_wheel(
    name = "wheel",
    distribution = "cmk-relay-protocols",
    strip_path_prefixes = ["packages/cmk-relay-protocols"],
    version = "1.0.0",
    deps = [":cmk-relay-protocols"],
)

package_wheel(
    name = "pkg_tar",
    visibility = ["//visibility:public"],
    whl = "wheel",
)
