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
    srcs = [
        "cmk/astrein/__init__.py",
        "cmk/astrein/checkers/__init__.py",
        "cmk/astrein/checkers/_imported_names.py",
        "cmk/astrein/checkers/_placeholders.py",
        "cmk/astrein/checkers/abcmeta_metaclass.py",
        "cmk/astrein/checkers/argparse_nargs.py",
        "cmk/astrein/checkers/conftest_import.py",
        "cmk/astrein/checkers/html_debug.py",
        "cmk/astrein/checkers/http_status_literal.py",
        "cmk/astrein/checkers/key_size_unit_test.py",
        "cmk/astrein/checkers/localization.py",
        "cmk/astrein/checkers/localization_named_placeholder.py",
        "cmk/astrein/checkers/logging_formatter.py",
        "cmk/astrein/checkers/logging_named_placeholder.py",
        "cmk/astrein/checkers/module_layers/__init__.py",
        "cmk/astrein/checkers/module_layers/checker.py",
        "cmk/astrein/checkers/module_layers/config.py",
        "cmk/astrein/checkers/pillow_import.py",
        "cmk/astrein/checkers/pydantic_type_adapter.py",
        "cmk/astrein/checkers/request_input.py",
        "cmk/astrein/checkers/tarfile_open_read.py",
        "cmk/astrein/cli.py",
        "cmk/astrein/engine.py",
        "cmk/astrein/framework.py",
        "cmk/astrein/lsp.py",
        "cmk/astrein/output/__init__.py",
        "cmk/astrein/output/gcc.py",
        "cmk/astrein/output/sarif.py",
        "cmk/astrein/registry.py",
        "cmk/astrein/suppressions.py",
    ],
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
    srcs = glob(["tests/test_*.py"]),
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
