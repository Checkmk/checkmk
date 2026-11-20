load("@aspect_rules_py//py:defs.bzl", "py_library")
load("@cmk_requirements//:requirements.bzl", "requirement")

py_library(
    name = "png_renderer",
    srcs = [
        "__init__.py",
        "_model.py",
        "_wire.py",
    ],
    imports = ["../.."],
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
    imports = ["../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        ":png_renderer",
        requirement("matplotlib"),
        requirement("numpy"),
    ],
)
