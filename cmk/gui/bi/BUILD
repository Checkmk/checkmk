load("@aspect_rules_py//py:defs.bzl", "py_library")

py_library(
    name = "bi_manager",
    srcs = ["bi_manager.py"],
    imports = ["../../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        "//cmk/bi",
        "//cmk/gui:hooks",
        "//cmk/gui:i18n",
        "//cmk/gui:sites",
        "//packages/cmk-ccc:exceptions",
        "//packages/cmk-ccc:site",
        "//packages/cmk-livestatus-client",
    ],
)

filegroup(
    name = "gui_srcs",
    srcs = glob(
        include = ["**/*.py"],
        exclude = ["bi_manager.py"],
    ),
    visibility = ["//cmk/gui:__pkg__"],
)
