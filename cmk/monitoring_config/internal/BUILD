load("@aspect_rules_py//py:defs.bzl", "py_library")

py_library(
    name = "internal",
    srcs = glob(["**/*.py"]),
    imports = ["../../.."],
    visibility = [
        "//cmk:__pkg__",
        "//cmk/base:__subpackages__",
        "//cmk/plugins:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        "//cmk/base/config",
        "//cmk/utils",
        "//packages/cmk-ccc:config-path",
        "//packages/cmk-ccc:hostaddress",
        "//packages/cmk-check-engine:checker-plugin",
        "//packages/cmk-check-engine/cmk/checkengine/plugins",
        "//packages/cmk-licensing",
        "//packages/cmk-plugin-apis:password_store",
    ],
)
