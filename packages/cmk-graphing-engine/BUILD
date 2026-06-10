load("@aspect_rules_py//py:defs.bzl", "py_library", "py_pytest_main", "py_test")
load("@bazel_skylib//rules:build_test.bzl", "build_test")
load("@cmk_requirements//:requirements.bzl", "requirement")
load("@rules_python//python:packaging.bzl", "py_wheel")
load("//bazel/rules:package_wheel.bzl", "package_wheel")
load("//bazel/rules:py_requirements_test.bzl", "py_requirements_test")

exports_files([
    "dev-requirements.in",
    "pyproject.toml",
    "requirements.in",
])

py_library(
    name = "cmk-graphing-engine",
    srcs = [
        "cmk/graphing_engine/__init__.py",
        "cmk/graphing_engine/_evaluate.py",
        "cmk/graphing_engine/_explicit.py",
        "cmk/graphing_engine/_fetch.py",
        "cmk/graphing_engine/_from_api.py",
        "cmk/graphing_engine/_objects.py",
        "cmk/graphing_engine/_options.py",
        "cmk/graphing_engine/_template.py",
        "cmk/graphing_engine/_title.py",
        "cmk/graphing_engine/_translate.py",
    ],
    data = [":py_typed"],
    imports = ["."],
    visibility = ["//visibility:public"],
    deps = [
        "//packages/cmk-plugin-apis:graphing",
    ],
)

_ALL = [
    "cmk-graphing-engine",
]

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
        ":cmk-graphing-engine",
        requirement("pytest"),
    ],
)

py_wheel(
    name = "wheel",
    distribution = "cmk-graphing-engine",
    strip_path_prefixes = ["packages/cmk-graphing-engine"],
    # TODO: Duplicated from pyproject.toml
    version = "1.0.0",
    visibility = ["//visibility:public"],
    deps = _ALL + [
        ":py_typed",
    ],
)

build_test(
    name = "build_test",
    targets = ["wheel"],
)

filegroup(
    name = "py_typed",
    srcs = ["cmk/graphing_engine/py.typed"],
)

package_wheel(
    name = "pkg_tar",
    visibility = ["//visibility:public"],
    whl = "wheel",
)

sh_library(
    name = "helpers",
    srcs = [
        ".f12",
    ],
)

py_requirements_test(
    name = "requirements-test",
    libs = _ALL,
    requirements_in = "requirements.in",
)
