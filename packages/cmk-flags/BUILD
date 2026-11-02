load("@aspect_rules_py//py:defs.bzl", "py_library")
load("@bazel_skylib//rules:build_test.bzl", "build_test")
load("@cmk_requirements//:requirements.bzl", "requirement")
load("@rules_python//python:packaging.bzl", "py_wheel")
load("//bazel/rules:package_wheel.bzl", "package_wheel")
load("//bazel/rules:py_requirements_test.bzl", "py_requirements_test")

exports_files([
    "dev-requirements.in",
    "requirements.in",
])

py_library(
    name = "cmk-flags",
    srcs = [
        "cmk/flags/__init__.py",
        "cmk/flags/_config.py",
    ],
    data = [":py_typed"],
    imports = ["."],
    visibility = ["//visibility:public"],
    deps = [
        requirement("pydantic"),
    ],
)

py_library(
    name = "gui",
    srcs = glob(["cmk/flags/gui/**/*.py"]),
    imports = ["."],
    visibility = [
        "//cmk:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        ":cmk-flags",
        requirement("pydantic"),
        "//cmk/gui:core_toolkit",
        "//cmk/gui/watolib",
        "//cmk/gui/watolib:config_infra",
        "//cmk/gui_plugins/internal",
        "//cmk/utils:paths",
        "//packages/cmk-ccc:store",
        "//packages/cmk-plugin-apis:rulesets",
        "//packages/cmk-web/cmk/web/utils",
    ],
)

_ALL = [
    "cmk-flags",
]

py_wheel(
    name = "wheel",
    distribution = "cmk-flags",
    strip_path_prefixes = ["packages/cmk-flags"],
    version = "1.0.0",
    visibility = ["//visibility:public"],
    deps = _ALL + [
        ":gui",
        ":py_typed",
    ],
)

build_test(
    name = "build_test",
    targets = ["wheel"],
)

filegroup(
    name = "py_typed",
    srcs = ["cmk/flags/py.typed"],
)

package_wheel(
    name = "pkg_tar",
    visibility = ["//visibility:public"],
    whl = "wheel",
)

py_requirements_test(
    name = "requirements-test",
    libs = _ALL + [":gui"],
    requirements_in = "requirements.in",
)
