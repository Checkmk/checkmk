load("@aspect_rules_py//py:defs.bzl", "py_library")

py_library(
    name = "backend",
    srcs = glob(["backend/**/*.py"]),
    imports = ["../.."],
    visibility = [
        "//bin:__subpackages__",
        "//cmk:__subpackages__",
        "//non-free/packages/cmk-dcd:__pkg__",
    ],
    deps = [
        "//packages/cmk-ccc:hostaddress",
        "//packages/cmk-ccc:inotify",
    ],
)

py_library(
    name = "hub",
    srcs = glob(["hub/**/*.py"]),
    imports = ["../.."],
    visibility = [
        "//bin:__subpackages__",
        "//cmk:__subpackages__",
        "//non-free/packages/cmk-dcd:__pkg__",
    ],
    deps = [
        ":backend",
        "//packages/cmk-ccc:daemon",
        "//packages/cmk-ccc:hostaddress",
        "//packages/cmk-messaging",
    ],
)
