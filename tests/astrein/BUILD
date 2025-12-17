load("@rules_python//python:defs.bzl", "py_binary", "py_library")

py_library(
    name = "framework",
    srcs = ["framework.py"],
)

py_library(
    name = "sarif",
    srcs = ["sarif.py"],
    deps = [":framework"],
)

py_library(
    name = "module_layers_config",
    srcs = ["config/module_layers_config.py"],
)

py_library(
    name = "checker_localization",
    srcs = ["checker_localization.py"],
    visibility = ["//tests/astrein:__subpackages__"],
    deps = [":framework"],
)

py_library(
    name = "checker_module_layers",
    srcs = ["checker_module_layers.py"],
    visibility = ["//tests/astrein:__subpackages__"],
    deps = [
        ":framework",
        ":module_layers_config",
    ],
)

py_binary(
    name = "astrein",
    srcs = ["cli.py"],
    main = "cli.py",
    visibility = ["//visibility:public"],
    deps = [
        ":checker_localization",
        ":checker_module_layers",
        ":framework",
        ":module_layers_config",
        ":sarif",
    ],
)
