load("@aspect_rules_py//py:defs.bzl", "py_library")

py_library(
    name = "backend",
    srcs = glob(["backend/**/*.py"]),
    imports = ["../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//non-free/packages/cmk-dcd:__pkg__",
        "//packages/cmk-check-engine:__subpackages__",
    ],
    deps = [
        "//packages/cmk-ccc:hostaddress",
        "//packages/cmk-ccc:inotify",
    ],
)

py_library(
    name = "hub",
    srcs = glob(
        ["hub/**/*.py"],
        exclude = ["hub/cli.py"],
    ),
    imports = ["../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//non-free/packages/cmk-dcd:__pkg__",
        "//tests/unit:__subpackages__",
    ],
    deps = [
        ":backend",
        "//packages/cmk-ccc:daemon",
        "//packages/cmk-ccc:hostaddress",
        "//packages/cmk-messaging",
    ],
)

py_library(
    name = "cli",
    srcs = ["cli.py"],
    imports = ["../.."],
    visibility = ["//:__subpackages__"],
    deps = [
        ":backend",
        "//cmk/utils:paths",
        "//packages/cmk-livestatus-client",
    ],
)

py_library(
    name = "hub_cli",
    srcs = ["hub/cli.py"],
    imports = ["../.."],
    visibility = ["//:__subpackages__"],
    deps = [
        ":hub",
        "//cmk/utils:paths",
        "//cmk/utils:security_event",
        "//packages/cmk-ccc:hostaddress",
        "//packages/cmk-ccc:version-info",
        "//packages/cmk-crash:crash",
    ],
)
