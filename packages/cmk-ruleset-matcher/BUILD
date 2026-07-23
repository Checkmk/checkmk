load("@aspect_rules_py//py:defs.bzl", "py_library")
load("@bazel_skylib//rules:build_test.bzl", "build_test")
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
    name = "cmk-ruleset-matcher",
    srcs = [
        "cmk/ruleset_matcher/__init__.py",
        "cmk/ruleset_matcher/_type_defs.py",
        "cmk/ruleset_matcher/conditions.py",
        "cmk/ruleset_matcher/definition.py",
        "cmk/ruleset_matcher/labels.py",
        "cmk/ruleset_matcher/matcher.py",
        "cmk/ruleset_matcher/ruleset_name.py",
        "cmk/ruleset_matcher/tags.py",
        "cmk/ruleset_matcher/tuple_rulesets.py",
    ],
    data = [
        "cmk/ruleset_matcher/py.typed",
    ],
    imports = ["."],
    visibility = ["//visibility:public"],
    deps = [
        "//packages/cmk-ccc:debug",
        "//packages/cmk-ccc:exceptions",
        "//packages/cmk-ccc:hostaddress",
        "//packages/cmk-ccc:i18n",
        "//packages/cmk-ccc:regex",
        "//packages/cmk-ccc:site",
        "//packages/cmk-ccc:store",
        "//packages/cmk-trace",
    ],
)

py_doc_test(
    name = "doctest",
    size = "small",
    srcs = ["cmk-ruleset-matcher"],
)

py_wheel(
    name = "wheel",
    distribution = "cmk-ruleset-matcher",
    strip_path_prefixes = ["packages/cmk-ruleset-matcher"],
    # TODO: Duplicated from pyproject.toml
    version = "1.0.0",
    visibility = ["//visibility:public"],
    deps = [
        ":cmk-ruleset-matcher",
        ":py_typed",
    ],
)

build_test(
    name = "build_test",
    targets = ["wheel"],
)

filegroup(
    name = "py_typed",
    srcs = ["cmk/ruleset_matcher/py.typed"],
)

package_wheel(
    name = "pkg_tar",
    visibility = ["//visibility:public"],
    whl = "wheel",
)

py_cmk_test(
    name = "unit-tests",
    size = "small",
    srcs = glob(["tests/**/*.py"]),
    deps = [
        ":cmk-ruleset-matcher",
        "//packages/cmk-ccc:hostaddress",
    ],
)

py_requirements_test(
    name = "requirements-test",
    libs = [
        ":cmk-ruleset-matcher",
    ],
    requirements_in = "requirements.in",
)
