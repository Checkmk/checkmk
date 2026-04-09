load("@aspect_rules_py//py:defs.bzl", "py_library")
load("@cmk_requirements//:requirements.bzl", "requirement")

exports_files([".f12"])

py_library(
    name = "utils",
    srcs = ["utils.py"],
    imports = ["../../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        requirement("flask"),
    ],
)

# Temporary: wsgi files that still belong to the monolithic //cmk/gui target.
# Remove this filegroup once wsgi is fully extracted.
filegroup(
    name = "gui_srcs",
    srcs = glob(
        include = ["**/*.py"],
        exclude = ["utils.py"],
    ) + ["applications/index.wsgi"],
    visibility = ["//cmk/gui:__pkg__"],
)
