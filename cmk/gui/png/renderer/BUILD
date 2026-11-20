load("@aspect_rules_py//py:defs.bzl", "py_library")
load("@cmk_requirements//:requirements.bzl", "requirement")

py_library(
    name = "renderer",
    srcs = [
        "__init__.py",
        "_model.py",
    ],
    imports = ["../../../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//tests:__subpackages__",
    ],
)

py_library(
    name = "process",
    srcs = [
        "__main__.py",
        "_image.py",
        "_time_axis.py",
    ],
    imports = ["../../../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        ":renderer",
        "//cmk/gui/png",
        requirement("matplotlib"),
        requirement("numpy"),
    ],
)
