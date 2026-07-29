load("@aspect_rules_py//py:defs.bzl", "py_library")
load("@bazel_skylib//rules:build_test.bzl", "build_test")
load("@rules_python//python:packaging.bzl", "py_wheel")
load("//bazel/rules:doctest.bzl", "py_doc_test")
load("//bazel/rules:package_wheel.bzl", "package_wheel")
load("//bazel/rules:py_requirements_test.bzl", "py_requirements_test")

exports_files([
    "dev-requirements.in",
    "pyproject.toml",
    "requirements.in",
])

py_library(
    name = "inventory",
    srcs = [
        "cmk/inventory/__init__.py",
        "cmk/inventory/config.py",
        "cmk/inventory/paths.py",
        "cmk/inventory/structured_data.py",
        "cmk/inventory/transformation/__init__.py",
        "cmk/inventory/transformation/__main__.py",
        "cmk/inventory/transformation/main.py",
    ],
    data = [":inventory_py_typed"],
    imports = ["."],
    visibility = ["//visibility:public"],
    deps = [
        "//packages/cmk-ccc:exceptions",
        "//packages/cmk-ccc:hostaddress",
        "//packages/cmk-ccc:regex",
        "//packages/cmk-ccc:resulttype",
        "//packages/cmk-ccc:store",
    ],
)

py_doc_test(
    name = "doctest",
    size = "small",
    srcs = [":inventory"],
)

filegroup(
    name = "inventory_py_typed",
    srcs = ["cmk/inventory/py.typed"],
)

py_wheel(
    name = "wheel",
    distribution = "cmk-inventory",
    entry_points = {"console_scripts": [
        "cmk-transform-inventory-trees = cmk.inventory.transformation.__main__:main",
    ]},
    strip_path_prefixes = ["packages/cmk-inventory"],
    # TODO: Duplicated from pyproject.toml
    version = "1.0.0",
    visibility = ["//visibility:public"],
    deps = [
        ":inventory",
        ":inventory_py_typed",
    ],
)

build_test(
    name = "build_test",
    targets = [
        "wheel",
    ],
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
    libs = [":inventory"],
    requirements_in = "requirements.in",
)
