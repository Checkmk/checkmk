load("@aspect_rules_py//py:defs.bzl", "py_binary", "py_library", "py_pytest_main", "py_test")
load("@cmk_requirements//:requirements.bzl", "requirement")

py_library(
    name = "library",
    srcs = [
        "astrein/__init__.py",
        "astrein/checker_localization.py",
        "astrein/checker_module_layers.py",
        "astrein/cli.py",
        "astrein/framework.py",
        "astrein/module_layers_config.py",
        "astrein/sarif.py",
    ],
    imports = ["."],
)

py_binary(
    name = "astrein_bin",
    srcs = ["astrein/cli.py"],
    imports = ["."],
    main = "astrein/cli.py",
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
        requirement("pytest"),
    ],
)
