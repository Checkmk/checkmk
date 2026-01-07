load("@aspect_rules_py//py:defs.bzl", "py_binary", "py_library", "py_pytest_main", "py_test")
load("@cmk_requirements//:requirements.bzl", "requirement")

py_library(
    name = "library",
    srcs = [
        "checker_localization.py",
        "checker_module_layers.py",
        "cli.py",
        "config/module_layers_config.py",
        "framework.py",
        "sarif.py",
    ],
)

py_binary(
    name = "astrein",
    srcs = ["cli.py"],
    main = "cli.py",
    visibility = ["//visibility:public"],
    deps = [
        ":library",
    ],
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
