load("@aspect_rules_py//py:defs.bzl", "py_library")
load("@bazel_skylib//rules:build_test.bzl", "build_test")
load("@rules_python//python:packaging.bzl", "py_wheel")
load("//bazel/rules:doctest.bzl", "py_doc_test")
load("//bazel/rules:package_wheel.bzl", "package_wheel")
load("//bazel/rules:py_requirements_test.bzl", "py_requirements_test")

exports_files([
    "dev-requirements.in",
    "requirements.in",
])

py_library(
    name = "package",
    srcs = ["cmk/inventory/__init__.py"],
    data = [":inventory_py_typed"],
    imports = ["."],
    visibility = ["//visibility:public"],
)

py_library(
    name = "model",
    srcs = [
        "cmk/inventory/_choices.py",
        "cmk/inventory/_dict_keys.py",
        "cmk/inventory/_legacy.py",
        "cmk/inventory/delta.py",
        "cmk/inventory/filtering.py",
        "cmk/inventory/merging.py",
        "cmk/inventory/raw_paths.py",
        "cmk/inventory/serialization.py",
        "cmk/inventory/trees.py",
    ],
    imports = ["."],
    visibility = ["//visibility:public"],
    deps = [":package"],
)

py_library(
    name = "paths",
    srcs = ["cmk/inventory/paths.py"],
    imports = ["."],
    visibility = ["//visibility:public"],
    deps = [
        ":package",
        "//packages/cmk-ccc:hostaddress",
    ],
)

py_library(
    name = "store",
    srcs = [
        "cmk/inventory/history.py",
        "cmk/inventory/store.py",
    ],
    imports = ["."],
    visibility = ["//visibility:public"],
    deps = [
        ":model",
        ":package",
        ":paths",
        "//packages/cmk-ccc:exceptions",
        "//packages/cmk-ccc:hostaddress",
        "//packages/cmk-ccc:resulttype",
        "//packages/cmk-ccc:store",
    ],
)

py_library(
    name = "cleanup",
    srcs = ["cmk/inventory/cleanup.py"],
    imports = ["."],
    visibility = ["//visibility:public"],
    deps = [
        ":package",
        ":paths",
        "//packages/cmk-ccc:hostaddress",
    ],
)

py_library(
    name = "transformation",
    srcs = [
        "cmk/inventory/transformation/__init__.py",
        "cmk/inventory/transformation/__main__.py",
        "cmk/inventory/transformation/tree_files.py",
    ],
    imports = ["."],
    visibility = ["//visibility:public"],
    deps = [
        ":package",
        ":paths",
        ":store",
        "//packages/cmk-ccc:hostaddress",
        "//packages/cmk-ccc:store",
    ],
)

py_library(
    name = "inventory",
    imports = ["."],
    visibility = ["//visibility:public"],
    deps = [
        ":cleanup",
        ":model",
        ":package",
        ":paths",
        ":store",
        ":transformation",
    ],
)

py_doc_test(
    name = "doctest",
    size = "small",
    srcs = [
        ":cleanup",
        ":model",
        ":paths",
        ":store",
        ":transformation",
    ],
)

filegroup(
    name = "inventory_py_typed",
    srcs = ["cmk/inventory/py.typed"],
)

py_library(
    name = "plugins",
    srcs = ["cmk/plugins/inventory/diagnostics/checkmk_overview.py"],
    imports = ["."],
    visibility = [
        "//cmk:__subpackages__",
        "//packages/cmk-inventory:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        ":model",
        ":store",
        "//packages/cmk-ccc:hostaddress",
        "//packages/cmk-plugin-apis:diagnostics",
    ],
)

py_wheel(
    name = "wheel",
    distribution = "cmk-inventory",
    entry_points = {"console_scripts": [
        "cmk-transform-inventory-trees = cmk.inventory.transformation.__main__:main",
    ]},
    strip_path_prefixes = ["packages/cmk-inventory"],
    version = "1.0.0",
    visibility = ["//visibility:public"],
    deps = [
        ":cleanup",
        ":inventory_py_typed",
        ":model",
        ":package",
        ":paths",
        ":plugins",
        ":store",
        ":transformation",
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
    libs = [
        ":cleanup",
        ":model",
        ":paths",
        ":plugins",
        ":store",
        ":transformation",
    ],
    requirements_in = "requirements.in",
)
