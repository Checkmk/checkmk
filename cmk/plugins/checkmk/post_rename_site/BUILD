load("@aspect_rules_py//py:defs.bzl", "py_library")

py_library(
    name = "post_rename_site",
    srcs = glob(["*.py"]),
    imports = ["../../../.."],
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
        "//packages/cmk-ccc:i18n",
        "//packages/cmk-ccc:site",
        "//packages/cmk-ccc:store",
        "//packages/cmk-ccc:tty",
        "//packages/cmk-ccc:version",
        "//packages/cmk-messaging",
        "//packages/cmk-plugin-apis:post_rename_site",
        "//packages/cmk-ruleset-matcher",
    ],
)
