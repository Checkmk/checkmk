load("@aspect_rules_py//py:defs.bzl", "py_library")

py_library(
    name = "match_items",
    srcs = ["match_items.py"],
    imports = ["../../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        "//cmk/gui/utils:loading_transition",
        "//cmk/gui/utils:roles",
        "//packages/cmk-ccc:plugin-registry",
    ],
)

# Temporary: search files that still belong to the monolithic //cmk/gui target.
# Remove this filegroup once search is fully extracted.
filegroup(
    name = "gui_srcs",
    srcs = glob(
        include = ["**/*.py"],
        exclude = ["match_items.py"],
    ),
    visibility = ["//cmk/gui:__pkg__"],
)
