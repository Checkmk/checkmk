load("@aspect_rules_py//py:defs.bzl", "py_library")
load("@cmk_requirements//:requirements.bzl", "requirement")
load("@rules_python//python:defs.bzl", "py_binary")
load("//bazel/rules:py_cmk_test.bzl", "py_cmk_test")
load("//bazel/rules:py_requirements_test.bzl", "py_requirements_test")

exports_files([
    "requirements.in",
])

py_library(
    name = "library",
    srcs = glob(["cmk/astrein/**/*.py"]),
    data = [
        ":py_typed",
        "//:module_layers.toml",
        "//tests/agent-plugin-unit:sources-list.txt",
    ],
    imports = ["."],
    deps = [
        requirement("pygls"),
    ],
)

filegroup(
    name = "py_typed",
    srcs = ["cmk/astrein/py.typed"],
)

py_binary(
    name = "astrein_bin",
    srcs = ["cmk/astrein/cli.py"],
    imports = ["."],
    main = "cmk/astrein/cli.py",
    visibility = ["//visibility:public"],
    deps = [
        ":library",
    ],
)

alias(
    name = "astrein",
    actual = ":astrein_bin",
    visibility = ["//visibility:public"],
)

py_binary(
    name = "astrein_lsp_bin",
    srcs = ["cmk/astrein/lsp.py"],
    imports = ["."],
    main = "cmk/astrein/lsp.py",
    visibility = ["//visibility:public"],
    deps = [
        ":library",
        requirement("lsprotocol"),
        requirement("pygls"),
    ],
)

alias(
    name = "astrein-lsp",
    actual = ":astrein_lsp_bin",
    visibility = ["//visibility:public"],
)

py_cmk_test(
    name = "test",
    srcs = glob(["tests/**/test_*.py"]),
    data = ["//:module_layers.toml"],
    deps = [
        ":library",
        requirement("lsprotocol"),
    ],
)

py_requirements_test(
    name = "requirements-test",
    libs = [
        ":astrein_bin",
        ":astrein_lsp_bin",
        ":library",
    ],
    requirements_in = "requirements.in",
)
