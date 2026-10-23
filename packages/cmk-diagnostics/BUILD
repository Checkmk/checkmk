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
    name = "engine",
    srcs = glob(["cmk/diagnostics/engine/**/*.py"]),
    data = [":engine_py_typed"],
    imports = ["."],
    visibility = ["//visibility:public"],
    deps = [
        "//packages/cmk-plugin-apis:diagnostics",
        "//packages/cmk-plugin-apis:discover_plugins",
    ],
)

# The results of the diagnostics dump automations, shared by the automations
# and their callers in the GUI. Keep deps lean.
py_library(
    name = "automation_types",
    srcs = glob(["cmk/diagnostics/automation_types/**/*.py"]),
    data = [":automation_types_py_typed"],
    imports = ["."],
    visibility = ["//visibility:public"],
    deps = ["//packages/cmk-plugin-apis:automations"],
)

py_doc_test(
    name = "doctest",
    size = "small",
    srcs = [
        ":automation_types",
        ":engine",
    ],
)

filegroup(
    name = "automation_types_py_typed",
    srcs = ["cmk/diagnostics/automation_types/py.typed"],
)

filegroup(
    name = "engine_py_typed",
    srcs = ["cmk/diagnostics/engine/py.typed"],
)

py_wheel(
    name = "wheel",
    distribution = "cmk-diagnostics",
    strip_path_prefixes = ["packages/cmk-diagnostics"],
    version = "1.0.0",
    visibility = ["//visibility:public"],
    deps = [
        ":automation_types",
        ":automation_types_py_typed",
        ":engine",
        ":engine_py_typed",
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

py_requirements_test(
    name = "requirements-test",
    libs = [
        ":automation_types",
        ":engine",
    ],
    requirements_in = "requirements.in",
)
