load("@aspect_rules_py//py:defs.bzl", "py_library")
load("@cmk_requirements//:requirements.bzl", "requirement")

py_library(
    name = "renderer",
    srcs = glob(["**/*.py"]),
    imports = ["../../../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        "//cmk/gui/graphing",
        "//cmk/gui/png",
        "//packages/cmk-graphing-engine",
        "//packages/cmk-web/cmk/web/utils",
        requirement("matplotlib"),
        requirement("numpy"),
    ],
)
