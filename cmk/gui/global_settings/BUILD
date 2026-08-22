load("@aspect_rules_py//py:defs.bzl", "py_library")

py_library(
    name = "global_settings",
    srcs = glob(["**/*.py"]),
    imports = ["../../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//non-free/packages:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        "//cmk/gui:auth_core",
        "//cmk/gui:core_toolkit",
        "//cmk/gui:html_toolkit",
        "//cmk/gui:page_toolkit",
        "//cmk/gui/form_specs",
        "//cmk/gui/watolib",
        "//packages/cmk-plugin-apis:rulesets",
        "//packages/cmk-shared-typing:cmk_shared_typing_py",
    ],
)
