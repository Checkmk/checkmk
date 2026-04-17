load("@aspect_rules_py//py:defs.bzl", "py_library")

py_library(
    name = "internal",
    srcs = ["internal.py"],
    imports = ["../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//non-free/packages:__subpackages__",
        "//packages:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        "//packages/cmk-ccc:site",
    ],
)

py_library(
    name = "post_rename_site",
    srcs = [
        "logger.py",
        "main.py",
    ],
    imports = ["../.."],
    visibility = [
        "//bin:__subpackages__",
        "//cmk:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        ":internal",
        "//cmk/gui:main_modules",
        "//cmk/gui:script_helpers",
        "//cmk/gui:session",
        "//cmk/gui/watolib",
        "//cmk/utils",
        "//packages/cmk-ccc:debug",
        "//packages/cmk-ccc:i18n",
        "//packages/cmk-ccc:plugin-registry",
        "//packages/cmk-ccc:site",
        "//packages/cmk-ccc:tty",
        "//packages/cmk-ccc:version",
    ],
)
