load("@aspect_rules_py//py:defs.bzl", "py_library")
load("@bazel_skylib//rules:build_test.bzl", "build_test")
load("@cmk_requirements//:requirements.bzl", "requirement")
load("@rules_pkg//pkg:mappings.bzl", "pkg_attributes", "pkg_files")
load("@rules_pkg//pkg:tar.bzl", "pkg_tar")
load("@rules_python//python:packaging.bzl", "py_wheel")
load("//bazel/rules:doctest.bzl", "py_doc_test")
load("//bazel/rules:package_wheel.bzl", "package_wheel")
load("//bazel/rules:py_cmk_test.bzl", "py_cmk_test")
load("//bazel/rules:py_requirements_test.bzl", "py_requirements_test")

exports_files([
    "dev-requirements.in",
    "pyproject.toml",
    "requirements.in",
])

py_library(
    name = "cmk-licensing",
    srcs = glob(
        include = ["cmk/licensing/**/*.py"],
        # Note: Do not make this a package.
        # We want to be able to import cmk.licensing.basics without pulling in the rest.
        exclude = ["cmk/licensing/__init__.py"],
    ),
    data = ["cmk/licensing/py.typed"],
    imports = ["."],
    visibility = [
        "//cmk:__subpackages__",
        "//non-free/packages/cmk-licensing-nonfree:__pkg__",
        "//non-free/packages/cmk-metric-backend:__pkg__",
        "//non-free/packages/cmk-plugins-nonfree:__subpackages__",
        "//non-free/packages/cmk-robotmk:__pkg__",
        "//non-free/tests:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        "//packages/cmk-ccc:site",
        "//packages/cmk-ccc:store",
        "//packages/cmk-ccc:version",
        "//packages/cmk-ccc:version-info",
        "//packages/cmk-licensing/cmk/licensing/basics",
        "//packages/cmk-livestatus-client",
        "//packages/cmk-plugin-apis:discover_plugins",
        "//packages/cmk-plugin-apis:licensing",
        requirement("python-dateutil"),
    ],
)

py_doc_test(
    name = "doctest",
    size = "small",
    srcs = [
        ":cmk-licensing",
        "//packages/cmk-licensing/cmk/licensing/basics",
    ],
)

# Not shipped. Only exists so that static analysis tools (ruff, …)
# can discover these .py files via Bazel.
py_library(
    name = "cmk-update-license-usage-main",
    srcs = ["cmk-update-license-usage.py"],
    imports = ["."],
    deps = [
        ":cmk-licensing",
        "//cmk/utils:paths",
        "//packages/cmk-ccc:site",
        "//packages/cmk-licensing/cmk/licensing/basics",
    ],
)

pkg_files(
    name = "bin",
    srcs = [
        "cmk-update-license-usage.py",
    ],
    attributes = pkg_attributes(
        mode = "0755",
    ),
    prefix = "bin",
    renames = {"cmk-update-license-usage.py": "cmk-update-license-usage"},
)

pkg_tar(
    name = "cmk-update-license-usage_pkg_tar",
    srcs = [":bin"],
    stamp = 1,
    visibility = ["//omd:__pkg__"],
)

py_wheel(
    name = "wheel",
    distribution = "cmk-licensing",
    strip_path_prefixes = ["packages/cmk-licensing"],
    # TODO: Duplicated from pyproject.toml
    version = "1.0.0",
    visibility = ["//visibility:public"],
    deps = [
        ":cmk-licensing",
        "//packages/cmk-licensing/cmk/licensing/basics",
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

py_cmk_test(
    name = "unit",
    size = "small",
    srcs = glob(["tests/**/*.py"]),
    deps = [
        ":cmk-licensing",
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
