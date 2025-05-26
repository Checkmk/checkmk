load("@aspect_rules_py//py:defs.bzl", "py_library", "py_pytest_main", "py_test")
load("@cmk_requirements//:requirements.bzl", "requirement")
load("@rules_python//python:packaging.bzl", "py_wheel")
load("//bazel/rules:doctest.bzl", "py_doc_test")
load("//bazel/rules:package_wheel.bzl", "package_wheel")

exports_files([
    "pyproject.toml",
    "requirements.in",
])

py_library(
    name = "cmk-werks",
    srcs = [
        "cmk/werks/__init__.py",
        "cmk/werks/cli.py",
        "cmk/werks/collect.py",
        "cmk/werks/config.py",
        "cmk/werks/constants.py",
        "cmk/werks/convert.py",
        "cmk/werks/error.py",
        "cmk/werks/format.py",
        "cmk/werks/load.py",
        "cmk/werks/markup.py",
        "cmk/werks/models.py",
        "cmk/werks/parse.py",
        "cmk/werks/utils/__init__.py",
        "cmk/werks/utils/__main__.py",
        "cmk/werks/utils/collect.py",
        "cmk/werks/validate.py",
    ],
    imports = ["."],
    visibility = [
        "//cmk:__pkg__",
        "//omd:__pkg__",
    ],
    deps = [
        "//packages/cmk-ccc:version",
        requirement("gitpython"),
        requirement("lxml"),
        requirement("markdown"),
        requirement("pydantic"),
    ],
)

py_doc_test(
    name = "doctest",
    size = "small",
    srcs = ["cmk-werks"],
    tags = ["no-mypy"],
)

py_pytest_main(
    name = "__test__",
    tags = ["no-mypy"],
)

py_test(
    name = "unit",
    size = "small",
    srcs = glob(["tests/**/*.py"]) + [":__test__.py"],
    main = ":__test__.py",
    deps = [
        ":__test__",
        ":cmk-werks",
        requirement("pytest"),
        requirement("gitpython"),
    ],
)

py_wheel(
    name = "wheel",
    distribution = "cmk-werks",
    strip_path_prefixes = ["packages/cmk-werks"],
    # TODO: Duplicated from pyproject.toml
    version = "1.0.0",
    deps = [":cmk-werks"],
)

# This wheel is only used for providing the entry point "werk" from the .venv under .venv/bin
# We explicitly need to *not* add dependencies here because venv/IDE would take the static wheels
# and not the editable sources from the repo which are included via sitecustomize.py
py_wheel(
    name = "wheel_entrypoint_only",
    console_scripts = {"werk": "cmk.werks.cli:main"},
    distribution = "cmk-werks-entrypoint",
    version = "1.0.0",
    visibility = ["//visibility:public"],
    deps = [],
)

package_wheel(
    name = "pkg_tar",
    visibility = ["//visibility:public"],
    whl = "wheel",
)
