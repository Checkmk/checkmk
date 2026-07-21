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
    name = "pages",
    srcs = [
        "cmk/web/context.py",
        "cmk/web/exceptions.py",
        "cmk/web/page_container.py",
        "cmk/web/pages.py",
    ],
    imports = ["."],
)

py_library(
    name = "cmk-web",
    srcs = ["cmk/web/__init__.py"],
    data = ["cmk/web/py.typed"],
    imports = ["."],
    visibility = ["//visibility:public"],
    deps = [
        ":pages",
        "//packages/cmk-web/cmk/web/htmllib",
        "//packages/cmk-web/cmk/web/utils",
    ],
)

py_doc_test(
    name = "doctest",
    size = "small",
    srcs = [
        ":pages",
        "//packages/cmk-web/cmk/web/htmllib",
        "//packages/cmk-web/cmk/web/utils",
    ],
)

py_requirements_test(
    name = "requirements-test",
    libs = [
        ":cmk-web",
        ":pages",
        "//packages/cmk-web/cmk/web/htmllib",
        "//packages/cmk-web/cmk/web/utils",
    ],
    requirements_in = "requirements.in",
)

py_wheel(
    name = "wheel",
    distribution = "cmk-web",
    strip_path_prefixes = ["packages/cmk-web"],
    # TODO: Duplicated from pyproject.toml
    version = "1.0.0",
    visibility = ["//visibility:public"],
    deps = [
        ":cmk-web",
        ":pages",
        "//packages/cmk-web/cmk/web/htmllib",
        "//packages/cmk-web/cmk/web/utils",
    ],
)

build_test(
    name = "build_test",
    targets = [
        ":wheel",
    ],
)

sh_library(
    name = "f12",
    srcs = [".f12"],
)

package_wheel(
    name = "pkg_tar",
    visibility = ["//visibility:public"],
    whl = "wheel",
)
