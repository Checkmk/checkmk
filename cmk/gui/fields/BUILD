load("@aspect_rules_py//py:defs.bzl", "py_library")
load("@cmk_requirements//:requirements.bzl", "requirement")

py_library(
    name = "base",
    srcs = [
        "base.py",
        "mixins.py",
        "utils.py",
    ],
    imports = ["../../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        "//cmk/fields",
        "//packages/cmk-ccc:version",
        "//packages/cmk-livestatus-client:py_livestatus",
        requirement("apispec"),
        requirement("marshmallow"),
    ],
)

# Temporary: fields files that still belong to the monolithic //cmk/gui target.
# Remove this filegroup once fields is fully extracted.
filegroup(
    name = "gui_srcs",
    srcs = glob(
        include = ["**/*.py"],
        exclude = [
            "base.py",
            "mixins.py",
            "utils.py",
        ],
    ),
    visibility = ["//cmk/gui:__pkg__"],
)
