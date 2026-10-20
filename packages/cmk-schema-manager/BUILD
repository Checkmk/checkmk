load("@aspect_rules_py//py:defs.bzl", "py_library")
load("@bazel_skylib//rules:build_test.bzl", "build_test")
load("@rules_python//python:packaging.bzl", "py_wheel")
load("//bazel/rules:package_wheel.bzl", "package_wheel")
load("//bazel/rules:py_requirements_test.bzl", "py_requirements_test")

exports_files([
    "dev-requirements.in",
    "requirements.in",
])

py_library(
    name = "cmk-schema-manager",
    srcs = glob(["cmk/schema_manager/**/*.py"]),
    data = [":py_typed"],
    imports = ["."],
    visibility = ["//visibility:public"],
    deps = [
        "//packages/cmk-plugin-apis:discover_plugins",
    ],
)

py_library(
    name = "testlib",
    testonly = True,
    srcs = glob(["cmk/testlib/schema_manager/**/*.py"]),
    imports = ["."],
    visibility = ["//visibility:public"],
    deps = [":cmk-schema-manager"],
)

_ALL = [
    "cmk-schema-manager",
]

py_wheel(
    name = "wheel",
    distribution = "cmk-schema-manager",
    strip_path_prefixes = ["packages/cmk-schema-manager"],
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
    srcs = ["cmk/schema_manager/py.typed"],
)

package_wheel(
    name = "pkg_tar",
    visibility = ["//visibility:public"],
    whl = "wheel",
)

py_requirements_test(
    name = "requirements-test",
    libs = _ALL,
    requirements_in = "requirements.in",
)
