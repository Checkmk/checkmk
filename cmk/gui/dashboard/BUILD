load("@aspect_rules_py//py:defs.bzl", "py_library")

py_library(
    name = "page_token_error",
    srcs = ["page_token_error.py"],
    imports = ["../../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        "//cmk/gui:config",
        "//cmk/gui:http",
        "//cmk/gui:i18n",
        "//cmk/gui:logged_in",
        "//cmk/gui:theme",
        "//cmk/gui/htmllib:html",
    ],
)

py_library(
    name = "type_defs",
    srcs = ["type_defs.py"],
    imports = ["../../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        "//cmk/gui:type_defs",
        "//cmk/gui/valuespec",
    ],
)

# Temporary: dashboard files that still belong to the monolithic //cmk/gui target.
# Remove this filegroup once dashboard is fully extracted.
filegroup(
    name = "gui_srcs",
    srcs = glob(
        include = ["**/*.py"],
        exclude = [
            "page_token_error.py",
            "type_defs.py",
        ],
    ),
    visibility = ["//cmk/gui:__pkg__"],
)
