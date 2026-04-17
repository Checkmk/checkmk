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
        "//cmk/gui:config",
        "//cmk/gui:logged_in",
        "//cmk/gui:site_config",
        "//cmk/gui:user_sites",
        "//cmk/gui/watolib",
        "//cmk/gui/watolib:config_infra",
        "//cmk/post_rename_site:internal",
        "//cmk/utils",
        "//packages/cmk-ccc:site",
    ],
)
