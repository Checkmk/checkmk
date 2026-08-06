load("@aspect_rules_py//py:defs.bzl", "py_library")
load("@bazel_skylib//rules:build_test.bzl", "build_test")
load("@rules_python//python:packaging.bzl", "py_wheel")
load("//bazel/rules:package_wheel.bzl", "package_wheel")
load("//bazel/rules:py_requirements_test.bzl", "py_requirements_test")

exports_files([
    "dev-requirements.in",
    "pyproject.toml",
    "requirements.in",
])

py_library(
    name = "backend",
    srcs = [
        "cmk/profiling/backend/__init__.py",
        "cmk/profiling/backend/_flamegraph.py",
        "cmk/profiling/backend/_profile.py",
        "cmk/profiling/backend/_store.py",
    ],
    data = [":backend_py_typed"],
    imports = ["."],
    visibility = ["//visibility:public"],
    deps = [
        "//packages/cmk-ccc:store",
        "//packages/cmk-shared-typing:cmk_shared_typing_py",
    ],
)

py_library(
    name = "gui",
    srcs = [
        "cmk/profiling/gui/__init__.py",
        "cmk/profiling/gui/_store.py",
        "cmk/profiling/gui/pages.py",
    ],
    data = [":gui_py_typed"],
    imports = ["."],
    visibility = ["//visibility:public"],
    deps = [
        ":backend",
        "//cmk/gui:auth_core",
        "//cmk/gui:config",
        "//cmk/gui:core_toolkit",
        "//cmk/gui:html_toolkit",
        "//cmk/gui:page_toolkit",
        "//cmk/gui/utils",
        "//cmk/gui/utils:middle",
        "//cmk/gui/watolib",
        "//cmk/utils:paths",
        "//packages/cmk-shared-typing:cmk_shared_typing_py",
    ],
)

filegroup(
    name = "backend_py_typed",
    srcs = ["cmk/profiling/backend/py.typed"],
)

filegroup(
    name = "gui_py_typed",
    srcs = ["cmk/profiling/gui/py.typed"],
)

py_library(
    name = "plugins",
    srcs = glob(["cmk/plugins/**/*.py"]),
    imports = ["."],
    visibility = [
        "//cmk:__subpackages__",
        "//packages/cmk-profiling:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        ":backend",
        "//packages/cmk-plugin-apis:diagnostics",
    ],
)

py_wheel(
    name = "wheel",
    distribution = "cmk-profiling",
    strip_path_prefixes = ["packages/cmk-profiling"],
    # TODO: Duplicated from pyproject.toml
    version = "1.0.0",
    visibility = ["//visibility:public"],
    deps = [
        ":backend",
        ":backend_py_typed",
        ":gui",
        ":gui_py_typed",
        ":plugins",
    ],
)

build_test(
    name = "build_test",
    targets = ["wheel"],
)

package_wheel(
    name = "pkg_tar",
    visibility = ["//visibility:public"],
    whl = "wheel",
)

py_requirements_test(
    name = "requirements-test",
    libs = [
        ":backend",
        ":gui",
        ":plugins",
    ],
    requirements_in = "requirements.in",
)
