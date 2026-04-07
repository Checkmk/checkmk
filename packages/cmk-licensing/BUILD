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
    name = "cmk-licensing",
    srcs = glob(["cmk/licensing/**/*.py"]),
    data = ["cmk/licensing/py.typed"],
    imports = ["."],
    visibility = [
        "//cmk:__subpackages__",
        "//non-free/packages/cmk-licensing-nonfree:__pkg__",
    ],
    deps = [
        "//packages/cmk-ccc:site",
        "//packages/cmk-ccc:store",
        "//packages/cmk-ccc:version",
        "//packages/cmk-livestatus-client:py_livestatus",
        requirement("python-dateutil"),
    ],
)

py_wheel(
    name = "wheel",
    distribution = "cmk-licensing",
    strip_path_prefixes = ["packages/cmk-licensing"],
    # TODO: Duplicated from pyproject.toml
    version = "1.0.0",
    deps = [
        ":cmk-licensing",
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
        ":cmk-licensing",
        requirement("pytest"),
        requirement("time-machine"),
    ],
)

py_requirements_test(
    name = "requirements-test",
    libs = [
        ":cmk-licensing",
    ],
    requirements_in = "requirements.in",
)
