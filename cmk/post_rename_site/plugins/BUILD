load("@aspect_rules_py//py:defs.bzl", "py_library")

py_library(
    name = "plugins",
    srcs = glob(["**/*.py"]),
    imports = ["../../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        "//cmk/gui:app",
        "//cmk/gui:auth_core",
        "//cmk/gui:config",
        "//cmk/gui/watolib",
        "//cmk/gui/watolib:config_infra",
        "//cmk/utils",
        "//packages/cmk-ccc:site",
        "//packages/cmk-ccc:version",
        "//packages/cmk-plugin-apis:post_rename_site",
    ],
)
