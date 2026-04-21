load("@aspect_rules_py//py:defs.bzl", "py_library")

py_library(
    name = "welcome",
    srcs = glob(["**/*.py"]),
    imports = ["../../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//non-free/packages:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        "//cmk/gui:breadcrumb",
        "//cmk/gui:config",
        "//cmk/gui:header",
        "//cmk/gui:http",
        "//cmk/gui:i18n",
        "//cmk/gui:logged_in",
        "//cmk/gui:pages",
        "//cmk/gui:type_defs",
        "//cmk/gui/htmllib:html",
        "//cmk/gui/sidebar",
        "//cmk/gui/utils:roles",
        "//cmk/gui/utils:urls",
        "//cmk/gui/wato",
        "//cmk/utils",
        "//packages/cmk-ccc:plugin-registry",
        "//packages/cmk-ccc:version",
        "//packages/cmk-shared-typing:cmk_shared_typing_py",
    ],
)
