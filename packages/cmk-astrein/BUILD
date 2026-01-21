load("@aspect_rules_py//py:defs.bzl", "py_binary", "py_library", "py_pytest_main", "py_test")
load("@cmk_requirements//:requirements.bzl", "requirement")

exports_files([
    "requirements.in",
])

py_library(
    name = "library",
    srcs = [
        "cmk/astrein/__init__.py",
        "cmk/astrein/checker_localization.py",
        "cmk/astrein/checker_module_layers.py",
        "cmk/astrein/checkers.py",
        "cmk/astrein/cli.py",
        "cmk/astrein/framework.py",
        "cmk/astrein/lsp.py",
        "cmk/astrein/module_layers_config.py",
        "cmk/astrein/sarif.py",
    ],
    data = [":py_typed"],
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

py_pytest_main(
    name = "__test__",
    deps = [
        requirement("pytest"),
    ],
)

py_test(
    name = "test",
    srcs = ["__test__"] + glob(["tests/test_*.py"]),
    main = "__test__.py",
    deps = [
        ":__test__",
        ":library",
        requirement("lsprotocol"),
        requirement("pygls"),
        requirement("pytest"),
    ],
)
